#!/usr/bin/env python3
"""App Store Connect MCP server with one typed tool per published API operation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import http.client
from email.message import Message
import html
import json
import os
from pathlib import Path
import re
import secrets
import sys
import ssl
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jsonschema import Draft202012Validator

from asc_auth import make_jwt
from local_setup import start_background_setup
from runtime import StorageError, connection_status, forget_connection, load_connection


API_BASE = "https://api.appstoreconnect.apple.com"
API_ORIGIN = urllib.parse.urlsplit(API_BASE).netloc
API_VERSION = "0.1.0"
TOOL_PAGE_SIZE = 200
MAX_JSON_RESPONSE = 64 * 1024 * 1024
MAX_BINARY_RESPONSE = 512 * 1024 * 1024
APPROVAL_SECONDS = 300
OPERATIONS_PATH = Path(__file__).parents[1] / "operations.json"
UPLOAD_RESERVATIONS: dict[str, dict] = {}
ANALYTICS_DOWNLOADS: dict[str, dict] = {}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def load_catalog() -> tuple[dict, dict[str, dict]]:
    try:
        catalog = json.loads(OPERATIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RuntimeError("The bundled Apple OpenAPI action catalog is missing or invalid. Reinstall the plugin.") from None
    operations = catalog.get("operations")
    if not isinstance(operations, list) or catalog.get("operationCount") != len(operations):
        raise RuntimeError("The bundled Apple OpenAPI action catalog is incomplete. Reinstall the plugin.")
    return catalog, {operation["name"]: operation for operation in operations}


CATALOG, OPERATIONS = load_catalog()


def _parameter_value(value, parameter: dict, location: str) -> str:
    style = parameter.get("style") or ("simple" if location in {"path", "header"} else "form")
    explode = parameter.get("explode")
    if explode is None:
        explode = style == "form"
    if isinstance(value, list):
        separator = {"spaceDelimited": " ", "pipeDelimited": "|", "label": "." if explode else ","}.get(style, ",")
        rendered = separator.join(_scalar(item) for item in value)
        if location == "path" and style == "label":
            return "." + rendered
        if location == "path" and style == "matrix":
            name = urllib.parse.quote(parameter["name"], safe="-._~")
            return "".join(f";{name}={urllib.parse.quote(_scalar(item), safe='-._~')}" for item in value) if explode else f";{name}={urllib.parse.quote(rendered, safe='-._~')}"
        return rendered
    if isinstance(value, dict):
        if style == "deepObject":
            return "&".join(
                f"{urllib.parse.quote(parameter['name'], safe='-._~')}[{urllib.parse.quote(str(key), safe='-._~')}]={urllib.parse.quote(_scalar(item), safe='-._~')}"
                for key, item in value.items()
            )
        if explode and style in {"form", "simple"}:
            return ",".join(f"{key}={_scalar(item)}" for key, item in value.items())
        return ",".join(part for key, item in value.items() for part in (str(key), _scalar(item)))
    rendered = _scalar(value)
    if location == "path":
        if style == "label":
            return "." + urllib.parse.quote(rendered, safe="-._~")
        if style == "matrix":
            name = urllib.parse.quote(parameter["name"], safe="-._~")
            return f";{name}={urllib.parse.quote(rendered, safe='-._~')}"
        return urllib.parse.quote(rendered, safe="-._~")
    return rendered


def _scalar(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def build_url(operation: dict, arguments: dict) -> tuple[str, dict[str, str]]:
    path_values = arguments.get("path", {})
    endpoint = operation["path"]
    parameters = operation["parameters"]
    by_path_name = {p["name"]: p for p in parameters.get("path", [])}

    def substitute(match):
        name = match.group(1)
        if name not in path_values:
            raise ValueError(f"Missing path parameter: {name}")
        parameter = by_path_name.get(name, {"name": name})
        return _parameter_value(path_values[name], parameter, "path")

    endpoint = re.sub(r"\{([^{}]+)\}", substitute, endpoint)
    if "{" in endpoint or "}" in endpoint:
        raise ValueError("The endpoint path could not be resolved from its required path parameters.")

    query_values = arguments.get("query", {})
    query_defs = {p["name"]: p for p in parameters.get("query", [])}
    query_pairs = []
    for name, value in query_values.items():
        parameter = query_defs.get(name)
        if parameter is None:
            raise ValueError(f"Undocumented query parameter: {name}")
        if value is None:
            continue
        style = parameter.get("style") or "form"
        explode = parameter.get("explode")
        if explode is None:
            explode = style == "form"
        if style == "deepObject" and isinstance(value, dict):
            for key, item in value.items():
                query_pairs.append((f"{name}[{key}]", _scalar(item)))
        elif isinstance(value, list):
            if explode:
                query_pairs.extend((name, _scalar(item)) for item in value)
            else:
                delimiter = {"spaceDelimited": " ", "pipeDelimited": "|"}.get(style, ",")
                query_pairs.append((name, delimiter.join(_scalar(item) for item in value)))
        elif isinstance(value, dict):
            if explode:
                query_pairs.extend((str(key), _scalar(item)) for key, item in value.items())
            else:
                query_pairs.append((name, ",".join(part for key, item in value.items() for part in (str(key), _scalar(item)))))
        else:
            query_pairs.append((name, _scalar(value)))
    query_string = urllib.parse.urlencode(query_pairs, doseq=False)
    url = API_BASE + endpoint
    if query_string:
        url += "?" + query_string

    header_values = arguments.get("headers", {})
    allowed_headers = {p["name"].casefold(): p for p in parameters.get("header", [])}
    headers = {}
    for name, value in header_values.items():
        lowered = name.casefold()
        if lowered not in allowed_headers:
            raise ValueError(f"Undocumented header parameter: {name}")
        if lowered in {"authorization", "host", "content-length", "connection"}:
            raise ValueError(f"The {name} header is managed by the plugin and cannot be overridden.")
        headers[name] = _parameter_value(value, allowed_headers[lowered], "header")
    if urllib.parse.urlsplit(url).netloc != API_ORIGIN:
        raise ValueError("The App Store Connect API host is fixed by the plugin.")
    return url, headers


def _redact(value):
    if isinstance(value, dict):
        return {
            key: "[redacted]" if re.search(r"password|secret|token|private.?key|jwt", str(key), re.I) else _redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def request_approval(operation: dict, url: str, arguments: dict) -> bool:
    details = {
        "Action": operation["title"],
        "API operation": operation["operationId"],
        "Request": f"{operation['method']} {urllib.parse.urlsplit(url).path}",
        "Query": arguments.get("query", {}),
        "Body": _redact(arguments.get("body")) if "body" in arguments else None,
        "Reason": operation["riskCategory"],
    }
    display = json.dumps(details, ensure_ascii=False, indent=2)
    if len(display.encode("utf-8")) > 24_000:
        raise ValueError("This high-impact request is too large to review in the local approval page. No request was sent.")
    session = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(20)
    choice = {"value": None}
    decided = threading.Event()
    action_html = html.escape(operation["title"])
    details_html = html.escape(display)
    page = (Path(__file__).parents[1] / "assets" / "approval.html").read_text(encoding="utf-8")
    page = page.replace("__NONCE__", nonce).replace("__ACTION__", action_html).replace("__DETAILS__", details_html)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def do_GET(self):
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}" or self.path != "/":
                self.send_error(404)
                return
            body = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            token = self.headers.get("X-Approval-Token", "")
            if (self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                    or self.headers.get("Origin") != origin or self.path != "/api/decision"
                    or not hmac.compare_digest(token.encode(), session.encode())):
                self.send_error(403)
                return
            try:
                if int(self.headers.get("Content-Length", "0")) > 1024:
                    raise ValueError
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                if not isinstance(payload, dict) or payload.get("choice") not in {"approve", "cancel"}:
                    raise ValueError
                choice["value"] = payload["choice"] == "approve"
                decided.set()
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_error(400)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 0.5
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="app-store-connect-approval", daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/#session={session}"
    if not webbrowser.open(url):
        server.shutdown()
        server.server_close()
        raise ValueError("Could not open the local confirmation page. No high-impact request was sent.")
    try:
        decided.wait(APPROVAL_SECONDS)
        return choice["value"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def save_download(response, output_file: str | None, default_filename: str | None = None) -> dict:
    content_type = response.headers.get_content_type()
    disposition = Message()
    disposition["content-disposition"] = response.headers.get("Content-Disposition", "")
    filename = disposition.get_filename() or default_filename or f"app-store-connect-{int(time.time())}.download"
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename.replace("\\", "/")).name).strip("._") or "report.download"
    if output_file:
        target = Path(output_file).expanduser()
        if not target.is_absolute():
            raise ValueError("outputFile must be an absolute path.")
        if target.exists() and target.is_dir():
            target = target / filename
    else:
        target = Path.home() / "Downloads" / "App Store Connect" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise ValueError("The download destination already exists. Choose a new outputFile to avoid overwriting it.")
    temp_path = None
    size = 0
    try:
        with tempfile.NamedTemporaryFile(prefix=".asc-download-", dir=target.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BINARY_RESPONSE:
                    raise ValueError("The download exceeds the 512 MiB size limit. No complete file was saved.")
                handle.write(chunk)
        os.link(temp_path, target)
        temp_path.unlink()
    except FileExistsError:
        raise ValueError("The download destination already exists. Choose a new outputFile to avoid overwriting it.") from None
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
    return {"status": response.status, "contentType": content_type, "bytes": size, "file": str(target)}


def _capture_asset_reservations(result: dict) -> None:
    def visit(value):
        if isinstance(value, dict):
            operations = value.get("attributes", {}).get("uploadOperations") if isinstance(value.get("attributes"), dict) else None
            if isinstance(operations, list) and operations and isinstance(value.get("id"), str) and isinstance(value.get("type"), str):
                expiries = []
                for operation in operations:
                    if isinstance(operation, dict) and isinstance(operation.get("url"), str):
                        expires = urllib.parse.parse_qs(urllib.parse.urlsplit(operation["url"]).query).get("Expires", [])
                        if expires and expires[0].isdigit():
                            expiries.append(int(expires[0]))
                UPLOAD_RESERVATIONS[value["id"]] = {
                    "assetType": value["type"],
                    "assetId": value["id"],
                    "fileName": value.get("attributes", {}).get("fileName"),
                    "fileSize": value.get("attributes", {}).get("fileSize"),
                    "operations": operations,
                    "completedParts": set(),
                    "expiresAt": min(expiries) if expiries else time.time() + 7 * 24 * 60 * 60,
                }
            attributes = value.get("attributes")
            if (value.get("type") == "analyticsReportSegments" and isinstance(value.get("id"), str)
                    and isinstance(attributes, dict) and isinstance(attributes.get("url"), str)):
                ANALYTICS_DOWNLOADS[value["id"]] = {
                    "url": attributes["url"],
                    "sizeInBytes": attributes.get("sizeInBytes"),
                    "checksum": attributes.get("checksum"),
                    "expiresAt": time.monotonic() + 270,
                }
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(result.get("data"))


def _purge_ephemeral_urls() -> None:
    now = time.monotonic()
    for segment_id, item in list(ANALYTICS_DOWNLOADS.items()):
        if now >= item.get("expiresAt", 0):
            ANALYTICS_DOWNLOADS.pop(segment_id, None)
    wall_now = time.time()
    for asset_id, item in list(UPLOAD_RESERVATIONS.items()):
        if wall_now >= item.get("expiresAt", wall_now + 1):
            UPLOAD_RESERVATIONS.pop(asset_id, None)
    while len(ANALYTICS_DOWNLOADS) > 1000:
        ANALYTICS_DOWNLOADS.pop(next(iter(ANALYTICS_DOWNLOADS)))
    while len(UPLOAD_RESERVATIONS) > 100:
        UPLOAD_RESERVATIONS.pop(next(iter(UPLOAD_RESERVATIONS)))


def _hide_upload_urls(value):
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if key == "uploadOperations" and isinstance(child, list):
                result[key] = [
                    {
                        item_key: ("[held in local memory]" if item_key in {"url", "requestHeaders"} else _hide_upload_urls(item_value))
                        for item_key, item_value in operation.items()
                    }
                    for operation in child if isinstance(operation, dict)
                ]
            elif key == "assetToken":
                result[key] = "[held in local memory]"
            else:
                result[key] = _hide_upload_urls(child)
        return result
    if isinstance(value, list):
        return [_hide_upload_urls(child) for child in value]
    return value


def _hide_analytics_urls(value):
    if isinstance(value, dict):
        result = {key: _hide_analytics_urls(child) for key, child in value.items()}
        attributes = result.get("attributes")
        if result.get("type") == "analyticsReportSegments" and isinstance(attributes, dict) and "url" in attributes:
            attributes["url"] = "[stored locally for asc_download_analytics_segment; valid for about five minutes]"
        return result
    if isinstance(value, list):
        return [_hide_analytics_urls(child) for child in value]
    return value


def _upload_part(file_path: Path, upload: dict, index: int) -> None:
    method = upload.get("method")
    url = upload.get("url")
    offset = upload.get("offset")
    length = upload.get("length")
    if method not in {"PUT", "POST"} or not isinstance(url, str) or not isinstance(offset, int) or not isinstance(length, int):
        raise ValueError(f"Apple upload part {index + 1} has an invalid operation. No further parts were sent.")
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".blobstore.apple.com")
            or parsed.port not in {None, 443} or parsed.username or parsed.password):
        raise ValueError(f"Apple upload part {index + 1} has an unexpected destination host. No further parts were sent.")
    headers = {}
    for item in upload.get("requestHeaders", []):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("value"), str):
            raise ValueError(f"Apple upload part {index + 1} has invalid request headers. No further parts were sent.")
        name, value = item["name"], item["value"]
        if (not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name)
                or name.casefold() in {"authorization", "host", "content-length", "connection", "transfer-encoding"}
                or "\r" in value or "\n" in value):
            raise ValueError(f"Apple upload part {index + 1} returned an unsafe request header. No further parts were sent.")
        headers[name] = value

    connection = http.client.HTTPSConnection(
        parsed.hostname,
        parsed.port or 443,
        timeout=120,
        context=ssl.create_default_context(),
    )
    request_path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    try:
        connection.putrequest(method, request_path)
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.putheader("Content-Length", str(length))
        connection.endheaders()
        remaining = length
        with file_path.open("rb") as source:
            source.seek(offset)
            while remaining:
                chunk = source.read(min(64 * 1024, remaining))
                if not chunk:
                    raise ValueError(f"Local file ended during upload part {index + 1}. No further parts were sent.")
                connection.send(chunk)
                remaining -= len(chunk)
        response = connection.getresponse()
        response.read(16_384)
        if not 200 <= response.status < 300:
            raise ValueError(f"Apple's asset storage returned HTTP {response.status} for part {index + 1}. No further parts were sent.")
    except (OSError, TimeoutError, http.client.HTTPException):
        raise ValueError(f"Could not upload part {index + 1}. No further parts were sent; retry this same reservation before it expires.") from None
    finally:
        connection.close()


def transfer_reserved_asset(asset_id: str, file_path_value: str) -> dict:
    reservation = UPLOAD_RESERVATIONS.get(asset_id)
    if reservation is None:
        raise ValueError("No live upload reservation with that asset ID is in this MCP session. Create a new reservation and try again.")
    file_path = Path(file_path_value).expanduser()
    if not file_path.is_absolute() or not file_path.is_file():
        raise ValueError("filePath must be an absolute path to an existing local file.")
    size = file_path.stat().st_size
    expected_size = reservation.get("fileSize")
    if not isinstance(expected_size, int) or size != expected_size:
        raise ValueError(f"Local file size ({size} bytes) does not match Apple's reservation ({expected_size} bytes). No upload was started.")
    original_stat = file_path.stat()
    initial_digest = hashlib.md5(usedforsecurity=False)
    with file_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            initial_digest.update(chunk)
    initial_checksum = initial_digest.hexdigest()
    upload_operations = reservation["operations"]
    ranges = []
    for index, upload in enumerate(upload_operations):
        if not isinstance(upload, dict) or not isinstance(upload.get("offset"), int) or not isinstance(upload.get("length"), int):
            raise ValueError(f"Apple upload part {index + 1} has invalid offset or length. No upload was started.")
        ranges.append((upload["offset"], upload["offset"] + upload["length"], index))
    cursor = 0
    for start, end, index in sorted(ranges):
        if start != cursor or end <= start or end > size:
            raise ValueError(f"Apple upload part {index + 1} does not form a safe contiguous file range. No upload was started.")
        cursor = end
    if cursor != size:
        raise ValueError("Apple's upload operations do not cover the whole file. No upload was started.")

    for index, upload in enumerate(upload_operations):
        if index in reservation["completedParts"]:
            continue
        _upload_part(file_path, upload, index)
        reservation["completedParts"].add(index)

    final_digest = hashlib.md5(usedforsecurity=False)
    with file_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            final_digest.update(chunk)
    final_stat = file_path.stat()
    checksum = final_digest.hexdigest()
    if (final_stat.st_size != original_stat.st_size or final_stat.st_mtime_ns != original_stat.st_mtime_ns
            or not hmac.compare_digest(checksum, initial_checksum)):
        UPLOAD_RESERVATIONS.pop(asset_id, None)
        raise ValueError("The local file changed during upload. No commit checksum was returned; create a new reservation and upload the original file again.")
    commit_path = f"/v1/{reservation['assetType']}/{{id}}"
    commit_action = next((
        operation["name"] for operation in CATALOG["operations"]
        if operation["method"] == "PATCH" and operation["path"] == commit_path
    ), None)
    result = {
        "uploaded": True,
        "assetType": reservation["assetType"],
        "assetId": asset_id,
        "fileName": reservation.get("fileName"),
        "bytesUploaded": size,
        "partsUploaded": len(upload_operations),
        "sourceFileChecksum": checksum,
        "commitAction": commit_action,
        "nextStep": "Call the commitAction with Apple's uploaded=true and this sourceFileChecksum, then fetch the asset until its delivery state is COMPLETE.",
    }
    del UPLOAD_RESERVATIONS[asset_id]
    return result


def download_analytics_segment(segment_id: str, output_file: str | None) -> dict:
    download = ANALYTICS_DOWNLOADS.get(segment_id)
    if download is None or time.monotonic() >= download["expiresAt"]:
        ANALYTICS_DOWNLOADS.pop(segment_id, None)
        raise ValueError("No current analytics download URL is held for that segment. Fetch the segment details again and download within five minutes.")
    parsed = urllib.parse.urlsplit(download["url"])
    host_ok = bool(re.fullmatch(r"asp-[A-Za-z0-9-]+\.s3(?:[.-][A-Za-z0-9-]+)?\.amazonaws\.com", parsed.hostname or ""))
    if parsed.scheme != "https" or not host_ok or parsed.port not in {None, 443} or parsed.username or parsed.password:
        raise ValueError("Apple returned an unexpected analytics download host. No file was downloaded.")
    request = urllib.request.Request(download["url"], headers={"Accept": "*/*", "User-Agent": "jala-app-store-connect-mcp/0.1.0"}, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=90) as response:
            default_filename = f"analytics-{re.sub(r'[^A-Za-z0-9._-]', '_', segment_id)}.csv.gz"
            result = save_download(response, output_file, default_filename)
    except urllib.error.HTTPError as error:
        if error.code in {301, 302, 303, 307, 308, 403, 404, 410}:
            ANALYTICS_DOWNLOADS.pop(segment_id, None)
            raise ValueError("Apple's temporary analytics download URL expired or was rejected. Fetch the segment details again and retry.") from None
        raise ValueError(f"Apple's report storage returned HTTP {error.code}. No file was accepted.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError("Could not download the analytics segment. The temporary URL remains available briefly; check the destination and retry.") from None

    path = Path(result["file"])
    if isinstance(download.get("sizeInBytes"), int) and result["bytes"] != download["sizeInBytes"]:
        path.unlink(missing_ok=True)
        raise ValueError("The downloaded segment size did not match Apple's sizeInBytes. The incomplete file was removed.")
    expected_checksum = download.get("checksum")
    if isinstance(expected_checksum, str):
        digest = hashlib.md5(usedforsecurity=False)
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if not hmac.compare_digest(digest.hexdigest().casefold(), expected_checksum.casefold()):
            path.unlink(missing_ok=True)
            raise ValueError("The downloaded segment checksum did not match Apple's checksum. The file was removed.")
    ANALYTICS_DOWNLOADS.pop(segment_id, None)
    return {**result, "segmentId": segment_id, "verifiedSize": download.get("sizeInBytes"), "checksumVerified": isinstance(expected_checksum, str)}


def parse_json_response(response) -> dict:
    raw = response.read(MAX_JSON_RESPONSE + 1)
    if len(raw) > MAX_JSON_RESPONSE:
        raise ValueError("Apple returned a JSON response larger than 64 MiB; refine the query and try again.")
    if not raw:
        return {"status": response.status, "data": None}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise ValueError("Apple returned an invalid JSON response. Verify API state before repeating a write.") from None
    return {"status": response.status, "data": payload}


def api_error(error: urllib.error.HTTPError) -> dict:
    raw = error.read(16_384)
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeError, ValueError):
        payload = None
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list):
            clean = []
            for item in errors[:20]:
                if isinstance(item, dict):
                    clean.append({key: item[key] for key in ("status", "code", "title", "detail") if isinstance(item.get(key), (str, int))})
            payload = {"errors": clean}
        else:
            payload = {"message": "Apple returned an API error response."}
    return {"status": error.code, "error": payload or {"message": "Apple returned a non-JSON error response."}}


def call_operation(operation: dict, arguments: dict) -> dict:
    errors = sorted(Draft202012Validator(operation["inputSchema"]).iter_errors(arguments), key=lambda item: list(map(str, item.absolute_path)))
    if errors:
        location = ".".join(str(part) for part in errors[0].absolute_path) or "input"
        raise ValueError(f"Input does not match Apple's typed action schema at {location}. Check required values and documented types.")

    url, parameter_headers = build_url(operation, arguments)
    connection = load_connection()
    if operation["riskCategory"]:
        if not request_approval(operation, url, arguments):
            return {"cancelled": True, "message": "The high-impact App Store Connect request was cancelled or not approved. No request was sent."}

    request_headers = {
        "Authorization": f"Bearer {make_jwt(connection)}",
        "Accept": "application/json, application/vnd.api+json, application/octet-stream, application/gzip, application/a-gzip, application/zip",
        "User-Agent": "jala-app-store-connect-mcp/0.1.0",
        **parameter_headers,
    }
    body = None
    if operation.get("hasRequestBody"):
        body = json.dumps(arguments.get("body"), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=operation["method"])
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=90) as response:
            content_type = response.headers.get_content_type()
            if content_type in {"application/json", "application/vnd.api+json", "text/json"} or not content_type:
                result = parse_json_response(response)
                _capture_asset_reservations(result)
                return _hide_analytics_urls(_hide_upload_urls(result))
            if operation["method"] == "GET":
                resource = re.sub(r"[^A-Za-z0-9._-]+", "_", operation["path"].rstrip("/").split("/")[-1])
                extension = ".gz" if "gzip" in content_type else ".zip" if "zip" in content_type else ".bin"
                default_name = f"{resource}-{int(time.time())}{extension}"
                return save_download(response, arguments.get("outputFile"), default_name)
            return parse_json_response(response)
    except urllib.error.HTTPError as error:
        return {"error": api_error(error)}
    except urllib.error.URLError:
        raise ValueError("Could not reach the App Store Connect API. Writes are not retried; check the current state before trying again.") from None
    except TimeoutError:
        raise ValueError("The App Store Connect API request timed out. Writes are not retried; check the current state before trying again.") from None
    except OSError:
        raise ValueError("The local API operation or download failed. Writes are not retried; check the current state before trying again.") from None


def _tool_descriptor(operation: dict) -> dict:
    method = operation["method"]
    return {
        "name": operation["name"],
        "title": operation["title"],
        "description": operation["description"],
        "inputSchema": operation["inputSchema"],
        "annotations": {
            "readOnlyHint": method == "GET",
            "destructiveHint": method != "GET",
            "idempotentHint": method in {"GET", "PUT"},
            "openWorldHint": True,
        },
    }


def _control_tools() -> list[dict]:
    return [
        {
            "name": "asc_setup",
            "title": "Connect App Store Connect",
            "description": "Open a local browser form to import and verify a team or individual .p8 key. The key is saved only in the OS secret store.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
        },
        {
            "name": "asc_connection_status",
            "title": "Check App Store Connect connection",
            "description": "Check whether an API key is stored in the OS secret store. Shows only key type and Key ID, never the private key.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
        },
        {
            "name": "asc_forget_credentials",
            "title": "Remove saved App Store Connect credentials",
            "description": "Remove the local API key from the OS secret store. This does not revoke the key in App Store Connect.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            "annotations": {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False},
        },
        {
            "name": "asc_find_actions",
            "title": "Find App Store Connect API actions",
            "description": "Search the bundled named and typed Apple API actions by resource, operation, endpoint, tag, or description. This only searches the action catalog and makes no API request.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1, "maxLength": 120},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
        },
        {
            "name": "asc_transfer_reserved_asset",
            "title": "Upload a reserved App Store Connect asset",
            "description": "Upload a local image, video, or other file using the signed upload operations from a reservation created in this MCP process. The short-lived signed URLs remain in local memory and are never returned to the model or stored as credentials. Does not send the App Store Connect JWT to Apple's blob storage.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "assetId": {"type": "string", "minLength": 1, "maxLength": 128},
                    "filePath": {"type": "string", "minLength": 1, "maxLength": 4096, "description": "Absolute path to the local file matching the reservation's filename and byte size."},
                },
                "required": ["assetId", "filePath"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
        },
        {
            "name": "asc_download_analytics_segment",
            "title": "Download an App Store Connect analytics segment",
            "description": "Download a report segment using a current signed URL cached from Apple's analyticsReportSegments response. The signed URL is held only in local memory, never shown to the model or stored, and the App Store Connect JWT is not sent to report storage. Verifies Apple's size and checksum when returned.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "segmentId": {"type": "string", "minLength": 1, "maxLength": 128},
                    "outputFile": {"type": "string", "minLength": 1, "maxLength": 4096, "description": "Optional absolute destination. Existing files are never overwritten."},
                },
                "required": ["segmentId"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True},
        },
    ]


CONTROL_TOOLS = {tool["name"]: tool for tool in _control_tools()}


def _text_result(value: dict, *, is_error: bool = False) -> dict:
    return {
        "isError": is_error,
        "structuredContent": value,
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}],
    }


def call_tool(name: str, arguments: dict) -> dict:
    _purge_ephemeral_urls()
    if name in CONTROL_TOOLS:
        if name == "asc_find_actions":
            try:
                Draft202012Validator(CONTROL_TOOLS[name]["inputSchema"]).validate(arguments)
            except Exception:
                return _text_result({"error": "Provide a search query and a result limit from 1 to 50."}, is_error=True)
            query = arguments["query"].casefold()
            limit = arguments.get("limit", 20)
            matches = []
            for operation in CATALOG["operations"]:
                searchable = " ".join([
                    operation["name"], operation["operationId"], operation["title"],
                    operation["path"], " ".join(operation.get("tags", [])), operation["description"],
                ]).casefold()
                if query in searchable:
                    matches.append({
                        "tool": operation["name"],
                        "operationId": operation["operationId"],
                        "method": operation["method"],
                        "path": operation["path"],
                        "title": operation["title"],
                        "riskCategory": operation["riskCategory"],
                    })
                    if len(matches) >= limit:
                        break
            return _text_result({"apiVersion": CATALOG["apiVersion"], "matches": matches, "truncated": len(matches) == limit})
        if name == "asc_transfer_reserved_asset":
            try:
                Draft202012Validator(CONTROL_TOOLS[name]["inputSchema"]).validate(arguments)
                return _text_result(transfer_reserved_asset(arguments["assetId"], arguments["filePath"]))
            except (ValueError, OSError) as error:
                return _text_result({"error": str(error)}, is_error=True)
        if name == "asc_download_analytics_segment":
            try:
                Draft202012Validator(CONTROL_TOOLS[name]["inputSchema"]).validate(arguments)
                return _text_result(download_analytics_segment(arguments["segmentId"], arguments.get("outputFile")))
            except (ValueError, OSError) as error:
                return _text_result({"error": str(error)}, is_error=True)
        if arguments:
            return _text_result({"error": "This control action takes no arguments."}, is_error=True)
        if name == "asc_setup":
            try:
                return _text_result(start_background_setup())
            except Exception as error:
                message = str(error) if isinstance(error, (ValueError, StorageError)) else "Could not start local setup."
                return _text_result({"error": message}, is_error=True)
        if name == "asc_connection_status":
            try:
                return _text_result(connection_status())
            except StorageError as error:
                return _text_result({"error": str(error)}, is_error=True)
        try:
            return _text_result(forget_connection())
        except StorageError as error:
            return _text_result({"error": str(error)}, is_error=True)

    operation = OPERATIONS.get(name)
    if operation is None:
        return _text_result({"error": f"Unknown App Store Connect action: {name}"}, is_error=True)
    try:
        result = call_operation(operation, arguments)
        return _text_result(result, is_error="error" in result)
    except (ValueError, StorageError) as error:
        return _text_result({"error": str(error)}, is_error=True)
    except Exception:
        return _text_result({"error": "App Store Connect operation failed. No automatic retry was made; check the current state before repeating a write."}, is_error=True)


def _cursor_offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        if not isinstance(cursor, str) or len(cursor) > 128:
            raise ValueError
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        prefix, value = decoded.split(":", 1)
        offset = int(value)
        if prefix != "asc-tools-v1" or offset < 0:
            raise ValueError
        return offset
    except (ValueError, UnicodeError, base64.binascii.Error):
        raise ValueError("Invalid tools/list cursor.") from None


def tools_list(params: dict) -> dict:
    offset = _cursor_offset(params.get("cursor"))
    all_tools = [*CONTROL_TOOLS.values(), *(_tool_descriptor(operation) for operation in CATALOG["operations"])]
    page = all_tools[offset:offset + TOOL_PAGE_SIZE]
    result = {"tools": page}
    next_offset = offset + len(page)
    if next_offset < len(all_tools):
        result["nextCursor"] = base64.urlsafe_b64encode(f"asc-tools-v1:{next_offset}".encode()).decode("ascii").rstrip("=")
    return result


def handle(message: dict) -> dict | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "app-store-connect", "version": API_VERSION},
                "instructions": (
                    f"This server exposes {CATALOG['operationCount']} individually named, typed tools from Apple's App Store Connect API {CATALOG['apiVersion']}. "
                    "Each action maps to one published OpenAPI operation; use its path/query/body schema. High-impact deletes/revocations, submission/release changes, pricing/availability changes, and user/access changes open a local approval page; the Apple request is sent only after a person approves it there. The API key role remains authoritative."
                ),
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        try:
            return {"jsonrpc": "2.0", "id": request_id, "result": tools_list(params)}
        except ValueError as error:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(error)}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "tools/call requires a tool name and object arguments."}}
        return {"jsonrpc": "2.0", "id": request_id, "result": call_tool(name, arguments)}
    if request_id is None:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main() -> int:
    for line in sys.stdin:
        message = None
        try:
            message = json.loads(line)
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                response = {"jsonrpc": "2.0", "id": message.get("id") if isinstance(message, dict) else None, "error": {"code": -32600, "message": "Invalid JSON-RPC request."}}
            else:
                response = handle(message)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        except (json.JSONDecodeError, UnicodeError):
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error."}}) + "\n")
            sys.stdout.flush()
        except Exception:
            request_id = message.get("id") if isinstance(message, dict) else None
            response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": "Internal App Store Connect MCP error."}}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
