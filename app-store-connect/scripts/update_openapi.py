#!/usr/bin/env python3
"""Download Apple's published OpenAPI ZIP and refresh every named MCP action."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

from generate_openapi import SOURCE_URL, generate


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "jala-app-store-connect-mcp/0.1.0"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            archive = response.read(32 * 1024 * 1024 + 1)
    except (OSError, TimeoutError, ValueError):
        raise SystemExit("Could not download Apple's OpenAPI ZIP. Existing operation catalog was left unchanged.")
    if len(archive) > 32 * 1024 * 1024:
        raise SystemExit("Apple's OpenAPI ZIP exceeded the 32 MiB safety limit.")
    archive_sha = hashlib.sha256(archive).hexdigest()
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(archive)) as zipped:
            matches = [info for info in zipped.infolist() if Path(info.filename).name == "openapi.oas.json"]
            if len(matches) != 1 or matches[0].file_size > 32 * 1024 * 1024:
                raise ValueError
            info = matches[0]
            raw = zipped.read(info)
        document = json.loads(raw)
        if document.get("info", {}).get("title") != "App Store Connect API":
            raise ValueError
        catalog = generate(document)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        raise SystemExit("The downloaded ZIP did not contain Apple's expected OpenAPI file. Existing catalog was left unchanged.") from None

    catalog["specSha256"] = hashlib.sha256(raw).hexdigest()
    catalog["sourceArchiveSha256"] = archive_sha
    catalog["specFileDate"] = "-".join(str(part).zfill(2) for part in info.date_time[:3])
    output = PLUGIN_ROOT / "operations.json"
    output.write_text(json.dumps(catalog, separators=(",", ":")) + "\n", encoding="utf-8")
    upstream = PLUGIN_ROOT / "UPSTREAM.md"
    upstream.write_text(
        "# Apple OpenAPI source\n\n"
        f"The bundled named action schemas are generated from Apple's published App Store Connect OpenAPI ZIP: {SOURCE_URL}.\n\n"
        f"- API version: `{catalog['apiVersion']}`\n"
        f"- OpenAPI file date: `{catalog['specFileDate']}`\n"
        f"- Operations exposed: `{catalog['operationCount']}`\n"
        f"- OpenAPI SHA-256: `{catalog['specSha256']}`\n"
        f"- ZIP SHA-256: `{archive_sha}`\n\n"
        "Refresh with `python3 scripts/update_openapi.py`. Review the generated catalog and adjust the plugin's risk classification when Apple adds or changes operations.\n",
        encoding="utf-8",
    )
    print(json.dumps({"apiVersion": catalog["apiVersion"], "operations": catalog["operationCount"], "openapiSha256": catalog["specSha256"], "zipSha256": archive_sha}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
