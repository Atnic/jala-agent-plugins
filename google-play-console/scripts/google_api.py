"""Typed Google Play API request execution driven by the bundled Discovery catalog."""

from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from jsonschema import Draft202012Validator

from google_auth import access_token
from runtime import state_directory


CATALOG_PATH = Path(__file__).parents[1] / "operations.json"
MAX_JSON_RESPONSE = 64 * 1024 * 1024
MAX_BINARY_RESPONSE = 512 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024
API_ORIGINS = {
    "androidpublisher": "androidpublisher.googleapis.com",
    "playdeveloperreporting": "playdeveloperreporting.googleapis.com",
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def load_catalog() -> tuple[dict, dict[str, dict]]:
    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise RuntimeError("The bundled Google Play API action catalog is missing or invalid. Reinstall the plugin.") from None
    operations = catalog.get("operations")
    if not isinstance(operations, list) or catalog.get("operationCount") != len(operations):
        raise RuntimeError("The bundled Google Play API action catalog is incomplete. Reinstall the plugin.")
    return catalog, {operation["name"]: operation for operation in operations}


CATALOG, OPERATIONS = load_catalog()


def _scalar(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _parameter_details(operation: dict, location: str) -> dict[str, dict]:
    return {item["name"]: item for item in operation["parameters"].get(location, [])}


def _encode_path(value, *, reserved: bool) -> str:
    if isinstance(value, (dict, list)):
        raise ValueError("Path parameters must be scalar values.")
    safe = "-._~/:@!$&'()*+,;=" if reserved else "-._~"
    return urllib.parse.quote(_scalar(value), safe=safe)


def _query_pairs(operation: dict, query: dict | None) -> list[tuple[str, str]]:
    values = query or {}
    definitions = _parameter_details(operation, "query")
    pairs: list[tuple[str, str]] = []
    for name, value in values.items():
        details = definitions.get(name)
        if details is None:
            raise ValueError(f"Undocumented query parameter: {name}")
        if value is None:
            continue
        if details.get("repeated"):
            if not isinstance(value, list):
                raise ValueError(f"Query parameter {name} must be an array.")
            pairs.extend((name, _scalar(item)) for item in value)
        elif isinstance(value, (dict, list)):
            raise ValueError(f"Query parameter {name} must be a scalar value.")
        else:
            pairs.append((name, _scalar(value)))
    return pairs


def _path_for(operation: dict, template: str, path_values: dict) -> str:
    definitions = _parameter_details(operation, "path")

    def substitute(match):
        reserved = bool(match.group(1))
        name = match.group(2)
        if name not in path_values:
            raise ValueError(f"Missing path parameter: {name}")
        details = definitions.get(name)
        if details is None:
            raise ValueError(f"Undocumented path parameter: {name}")
        if reserved != bool(details.get("reservedExpansion")):
            raise ValueError(f"Path template for {name} does not match the Discovery document.")
        return _encode_path(path_values[name], reserved=reserved)

    rendered = re.sub(r"\{(\+?)([^{}]+)\}", substitute, template)
    if "{" in rendered or "}" in rendered:
        raise ValueError("The endpoint path could not be resolved from its documented parameters.")
    return rendered


def build_url(operation: dict, arguments: dict, *, upload: bool = False, extra_query: list[tuple[str, str]] | None = None) -> tuple[str, dict[str, str]]:
    path_values = arguments.get("path", {})
    template = operation.get("uploadPath") if upload else operation["path"]
    if upload and not template:
        raise ValueError("This API operation does not document a resumable upload path.")
    path = _path_for(operation, template, path_values)
    expected_origin = API_ORIGINS.get(operation.get("apiName"))
    base = urllib.parse.urlsplit(operation["baseUrl"])
    if (not expected_origin or base.scheme != "https" or base.netloc != expected_origin
            or base.username or base.password or base.query or base.fragment):
        raise ValueError("The Google API host is fixed by the plugin and its official API catalog.")
    url = operation["baseUrl"].rstrip("/") + "/" + path.lstrip("/")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != base.netloc or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("The Google API host is fixed by the bundled Discovery document.")
    query_pairs = _query_pairs(operation, arguments.get("query"))
    if extra_query:
        query_pairs.extend(extra_query)
    if query_pairs:
        url += "?" + urllib.parse.urlencode(query_pairs, doseq=True)

    header_values = arguments.get("headers", {})
    allowed_headers = _parameter_details(operation, "header")
    headers = {}
    for name, value in header_values.items():
        if name not in allowed_headers:
            raise ValueError(f"Undocumented request header: {name}")
        if name.casefold() in {"authorization", "host", "content-length", "content-type", "connection", "transfer-encoding"}:
            raise ValueError(f"The {name} header is managed by the plugin and cannot be overridden.")
        if (not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name)
                or isinstance(value, (dict, list))):
            raise ValueError(f"Request header {name} must be a scalar value.")
        rendered = _scalar(value)
        if "\r" in rendered or "\n" in rendered:
            raise ValueError(f"Request header {name} contains an invalid line break.")
        headers[name] = rendered
    return url, headers


def _redact(value):
    if isinstance(value, dict):
        return {
            key: "[redacted]" if re.search(r"password|secret|token|private.?key|authorization", str(key), re.I) else _redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def api_error(error: urllib.error.HTTPError) -> dict:
    try:
        raw = error.read(65_536)
        payload = json.loads(raw.decode("utf-8")) if raw else None
    except (OSError, UnicodeError, ValueError):
        payload = None
    if isinstance(payload, dict):
        payload = _redact(payload)
    return {"status": error.code, "error": payload or {"message": "Google returned a non-JSON API error response."}}


def _parse_json_response(response) -> dict:
    raw = response.read(MAX_JSON_RESPONSE + 1)
    if len(raw) > MAX_JSON_RESPONSE:
        raise ValueError("Google returned a JSON response larger than 64 MiB. Refine the query or use pagination.")
    if not raw:
        return {"status": response.status, "data": None}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise ValueError("Google returned an invalid JSON response. Verify the current resource state before repeating a write.") from None
    return {"status": response.status, "data": payload}


def _destination(output_file: str | None, prefix: str, suffix: str) -> Path:
    if output_file is None:
        directory = state_directory() / "downloads"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        return directory / f"{prefix}-{int(time.time())}-{os.urandom(4).hex()}{suffix}"
    path = Path(output_file)
    if not path.is_absolute():
        raise ValueError("Download destination must be an absolute path.")
    if not path.parent.is_dir():
        raise ValueError("Download destination folder does not exist.")
    return path


def save_download(response, output_file: str | None, default_name: str, max_size: int = MAX_BINARY_RESPONSE) -> dict:
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", default_name)[:128] or "google-play-download.bin"
    path = _destination(output_file, Path(filename).stem, Path(filename).suffix or ".bin") if output_file else _destination(None, Path(filename).stem, Path(filename).suffix or ".bin")
    total = 0
    try:
        with path.open("xb") as target:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    raise ValueError(f"Google's download exceeded the {max_size // (1024 * 1024)} MiB limit. No file was kept.")
                target.write(chunk)
    except FileExistsError:
        raise ValueError("Download destination already exists. Choose a new path; existing files are never overwritten.") from None
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {
        "filePath": str(path),
        "bytes": total,
        "contentType": response.headers.get_content_type(),
    }


def _read_upload_file(value: str, maximum: int) -> tuple[Path, int]:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("Upload file path must be absolute.")
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise ValueError("Upload path must point to a regular file.")
        size = resolved.stat().st_size
    except OSError:
        raise ValueError("Upload file could not be read. Check its path and permissions.") from None
    if size == 0:
        raise ValueError("Upload file is empty.")
    if maximum > 0 and size > maximum:
        raise ValueError(f"Upload file exceeds the API's documented {maximum // (1024 * 1024)} MiB size limit.")
    return resolved, size


def _upload_file(operation: dict, arguments: dict, token: str, header_values: dict[str, str]) -> dict:
    file_path, size = _read_upload_file(arguments["uploadFile"], operation.get("uploadMaxSize", 0))
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    accepted = operation.get("uploadContentTypes") or []
    normalized_type = content_type.casefold()
    matches_accepted_type = any(
        accepted_type == "*/*"
        or normalized_type == accepted_type.casefold()
        or (accepted_type.endswith("/*") and normalized_type.startswith(accepted_type[:-1].casefold()))
        for accepted_type in accepted
    )
    if accepted and not matches_accepted_type:
        raise ValueError(f"The detected upload type {content_type} is not accepted by this API operation ({', '.join(accepted)}).")
    initiation_url, _ = build_url(operation, arguments, upload=True, extra_query=[("uploadType", "resumable")])
    base_host = urllib.parse.urlsplit(operation["baseUrl"]).netloc
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "jala-google-play-console-mcp/0.1.0",
        "X-Upload-Content-Type": content_type,
        "X-Upload-Content-Length": str(size),
        **header_values,
    }
    metadata = None
    if operation.get("hasRequestBody"):
        metadata = json.dumps(arguments.get("body"), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=UTF-8"
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(initiation_url, data=metadata, headers=headers, method="POST")
    try:
        with opener.open(request, timeout=60) as response:
            location = response.headers.get("Location")
            response.read(4096)
    except urllib.error.HTTPError as error:
        return {"error": api_error(error)}
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError("Could not start Google's upload session. No file bytes were uploaded; check the API state and retry.") from None
    if not location:
        raise ValueError("Google did not return a resumable upload location. No file bytes were uploaded.")
    parsed_location = urllib.parse.urlsplit(location)
    if parsed_location.scheme != "https" or parsed_location.netloc != base_host or parsed_location.username or parsed_location.password or parsed_location.fragment:
        raise ValueError("Google returned an unexpected resumable upload host. No file bytes were sent.")

    offset = 0
    try:
        with file_path.open("rb") as source:
            while offset < size:
                chunk = source.read(min(UPLOAD_CHUNK_SIZE, size - offset))
                if not chunk:
                    raise ValueError("Upload file ended before its recorded size. Google may have received a partial upload; inspect the edit before retrying.")
                end = offset + len(chunk) - 1
                put = urllib.request.Request(
                    location,
                    data=chunk,
                    headers={
                        "Content-Type": content_type,
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {offset}-{end}/{size}",
                        "User-Agent": "jala-google-play-console-mcp/0.1.0",
                    },
                    method="PUT",
                )
                try:
                    with opener.open(put, timeout=180) as response:
                        payload = _parse_json_response(response)
                        if response.status not in {200, 201}:
                            return {"status": response.status, "data": payload.get("data")}
                        return {"status": response.status, "data": payload.get("data"), "uploadedBytes": size}
                except urllib.error.HTTPError as error:
                    if error.code == 308:
                        received = error.headers.get("Range", "")
                        matched = re.fullmatch(r"bytes=0-(\d+)", received.strip())
                        next_offset = int(matched.group(1)) + 1 if matched else 0
                        if next_offset <= offset:
                            raise ValueError("Google's upload session made no progress. Inspect the edit before retrying.") from None
                        offset = next_offset
                        source.seek(offset)
                        continue
                    return {"error": api_error(error)}
                except (urllib.error.URLError, TimeoutError, OSError):
                    raise ValueError("The upload status is uncertain after a network interruption. Inspect the Play Console edit before retrying.") from None
    except ValueError:
        raise
    except OSError:
        raise ValueError("Could not read the upload file. Check its permissions and retry.") from None
    raise ValueError("Google's upload session ended without a final response. Inspect the Play Console edit before retrying.")


def call_operation(operation: dict, arguments: dict) -> dict:
    errors = sorted(Draft202012Validator(operation["inputSchema"]).iter_errors(arguments), key=lambda item: list(map(str, item.absolute_path)))
    if errors:
        location = ".".join(str(part) for part in errors[0].absolute_path) or "input"
        raise ValueError(f"Input does not match this typed Google API action at {location}. Check required values and documented types.")

    url, parameter_headers = build_url(operation, arguments)
    token, _profile = access_token(arguments["profile"])
    if operation.get("supportsMediaUpload"):
        return _upload_file(operation, arguments, token, parameter_headers)

    query = arguments.get("query", {})
    media_requested = bool(operation.get("supportsMediaDownload")) and query.get("alt", "media") == "media"
    if operation.get("supportsMediaDownload") and "alt" not in query:
        separator = "&" if "?" in url else "?"
        url += separator + "alt=media"
    request_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, application/octet-stream, application/gzip, application/zip",
        "User-Agent": "jala-google-play-console-mcp/0.1.0",
        **parameter_headers,
    }
    body = None
    if operation.get("hasRequestBody"):
        body = json.dumps(arguments.get("body"), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=operation["method"])
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=90) as response:
            content_type = response.headers.get_content_type()
            if media_requested or content_type not in {"application/json", "text/json"}:
                name = re.sub(r"[^A-Za-z0-9._-]+", "_", operation["operationId"].split(".")[-1])
                suffix = ".gz" if "gzip" in content_type else ".zip" if "zip" in content_type else ".bin"
                return {"status": response.status, **save_download(response, arguments.get("outputFile"), f"{name}-{int(time.time())}{suffix}")}
            return _parse_json_response(response)
    except urllib.error.HTTPError as error:
        return {"error": api_error(error)}
    except urllib.error.URLError:
        raise ValueError("Could not reach the Google API. Writes are not retried; inspect the current state before trying again.") from None
    except TimeoutError:
        raise ValueError("The Google API request timed out. Writes are not retried; inspect the current state before trying again.") from None
    except OSError:
        raise ValueError("The local API operation or download failed. Writes are not retried; inspect the current state before trying again.") from None
