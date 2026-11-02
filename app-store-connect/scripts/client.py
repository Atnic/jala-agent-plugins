#!/usr/bin/env python3
"""App Store Connect REST client shared by the Python CLI."""

from __future__ import annotations

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
import ssl
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from asc_auth import make_jwt
from runtime import load_connection


API_BASE = "https://api.appstoreconnect.apple.com"
MAX_JSON_RESPONSE = 64 * 1024 * 1024
MAX_BINARY_RESPONSE = 512 * 1024 * 1024
APPROVAL_SECONDS = 300
UPLOAD_RESERVATIONS: dict[str, dict] = {}
ANALYTICS_DOWNLOADS: dict[str, dict] = {}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def build_url(path: str, query: dict) -> str:
    if not re.fullmatch(r"/v[0-9]+/[A-Za-z0-9_~.%/-]+", path):
        raise ValueError("Use an API path such as /v1/apps; pass query parameters with --query.")
    decoded = urllib.parse.unquote(path)
    if any(part in {".", ".."} for part in decoded.split("/")) or "\\" in decoded:
        raise ValueError("API paths cannot contain traversal segments.")
    pairs = []
    for key, value in query.items():
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        if not all(isinstance(item, (str, int, float, bool)) for item in values):
            raise ValueError("Query values must be scalars or arrays of scalars.")
        pairs.append((key, ",".join(str(item).lower() if isinstance(item, bool) else str(item) for item in values)))
    suffix = urllib.parse.urlencode(pairs)
    return API_BASE + path + ("?" + suffix if suffix else "")


def risk_for(method: str, path: str) -> str | None:
    if method == "DELETE":
        return "delete-or-revoke"
    if method == "GET":
        return None
    text = path.casefold()
    if re.search(r"revoke|revocation", text):
        return "delete-or-revoke"
    if re.search(r"submission|submit|release", text):
        return "submission-or-release"
    if re.search(r"price|pricing|availabilit|pre.?orders?|territory", text):
        return "pricing-or-availability"
    if re.search(r"/users?(?:/|$)|userinvitations|userroles|useraccess|userprovisioning|accesscontrol", text):
        return "user-or-access"
    return None


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
        "API operation": operation["path"],
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
            attributes["url"] = "[hidden; use download-segment with this segment ID]"
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
        raise ValueError("No live upload reservation with that asset ID is in this command. Create a new reservation and try again.")
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
    result = {
        "uploaded": True,
        "assetType": reservation["assetType"],
        "assetId": asset_id,
        "fileName": reservation.get("fileName"),
        "bytesUploaded": size,
        "partsUploaded": len(upload_operations),
        "sourceFileChecksum": checksum,
        "commitPath": f"/v1/{reservation['assetType']}/{asset_id}",
        "nextStep": "Use request PATCH on commitPath with Apple's uploaded=true and this sourceFileChecksum, then fetch the asset until its delivery state is COMPLETE.",
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
    request = urllib.request.Request(download["url"], headers={"Accept": "*/*", "User-Agent": "jala-app-store-connect-cli/0.2.0"}, method="GET")
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


def request(method: str, path: str, query: dict | None = None,
            body: dict | None = None, output_file: str | None = None) -> dict:
    if method not in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
        raise ValueError("Unsupported HTTP method.")
    if method == "GET" and body is not None:
        raise ValueError("GET requests cannot have a body.")
    query = query or {}
    url = build_url(path, query)
    connection = load_connection()
    risk = risk_for(method, urllib.parse.unquote(path))
    operation = {"title": f"{method} {path}", "method": method, "path": path, "riskCategory": risk}
    if risk and not request_approval(operation, url, {"query": query, "body": body}):
        return {"cancelled": True, "message": "The high-impact request was not approved. No request was sent."}

    request_headers = {
        "Authorization": f"Bearer {make_jwt(connection)}",
        "Accept": "application/json, application/vnd.api+json, application/octet-stream, application/gzip, application/a-gzip, application/zip",
        "User-Agent": "jala-app-store-connect-cli/0.2.0",
    }
    encoded_body = None
    if body is not None:
        encoded_body = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=encoded_body, headers=request_headers, method=method)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=90) as response:
            content_type = response.headers.get_content_type()
            if content_type in {"application/json", "application/vnd.api+json", "text/json"} or not content_type:
                result = parse_json_response(response)
                _capture_asset_reservations(result)
                return _hide_analytics_urls(_hide_upload_urls(result))
            if method == "GET":
                resource = re.sub(r"[^A-Za-z0-9._-]+", "_", path.rstrip("/").split("/")[-1])
                extension = ".gz" if "gzip" in content_type else ".zip" if "zip" in content_type else ".bin"
                default_name = f"{resource}-{int(time.time())}{extension}"
                return save_download(response, output_file, default_name)
            return parse_json_response(response)
    except urllib.error.HTTPError as error:
        return {"error": api_error(error)}
    except urllib.error.URLError:
        raise ValueError("Could not reach the App Store Connect API. Writes are not retried; check the current state before trying again.") from None
    except TimeoutError:
        raise ValueError("The App Store Connect API request timed out. Writes are not retried; check the current state before trying again.") from None
    except OSError:
        raise ValueError("The local API operation or download failed. Writes are not retried; check the current state before trying again.") from None
