#!/usr/bin/env python3
"""App Store Connect CLI: authenticate and call Apple's REST API operations."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from runtime import StorageError, install_runtime, runtime_python

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def read_arguments(value: str) -> dict:
    if value == "-":
        raw = sys.stdin.read()
    elif value.startswith("@"):
        raw = Path(value[1:]).expanduser().read_text(encoding="utf-8")
    else:
        raw = value
    try:
        result = json.loads(raw)
    except ValueError:
        raise ValueError("Arguments must be valid JSON (an object).") from None
    if not isinstance(result, dict):
        raise ValueError("Arguments must be a JSON object.")
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("setup", "status", "forget", "install-runtime"):
        commands.add_parser(name)
    call = commands.add_parser("request", help="Call an endpoint from Apple's API documentation")
    call.add_argument("method", type=str.upper, choices=("GET", "POST", "PATCH", "PUT", "DELETE"))
    call.add_argument("path", help="API path, e.g. /v1/apps")
    call.add_argument("--query", default="{}", help="Query JSON object, @file, or - for stdin; arrays become comma-separated values")
    call.add_argument("--body", help="Body JSON object, @file, or - for stdin")
    call.add_argument("--output-file", help="Absolute destination for a binary response")
    download = commands.add_parser("download-segment", help="Fetch segment details and download in one command")
    download.add_argument("segment_id")
    download.add_argument("--output-file")
    upload = commands.add_parser("upload-asset", help="Fetch an existing asset reservation and transfer its file")
    upload.add_argument("asset_type", help="Apple resource type, e.g. appScreenshots")
    upload.add_argument("asset_id")
    upload.add_argument("file_path", help="Absolute local file path")
    return root


def execute(args: argparse.Namespace) -> dict:
    if args.command == "install-runtime":
        return install_runtime(PLUGIN_ROOT)
    if args.command in {"setup", "status", "forget"}:
        from local_setup import run_setup
        from runtime import connection_status, forget_connection
        return {"setup": run_setup, "status": connection_status, "forget": forget_connection}[args.command]()
    import client
    import urllib.parse

    if args.command == "request":
        if args.query == "-" and args.body == "-":
            raise ValueError("Use stdin for only one of --query or --body.")
        return client.request(args.method, args.path, read_arguments(args.query),
                              read_arguments(args.body) if args.body is not None else None,
                              args.output_file)
    if args.command == "download-segment":
        segment_id = urllib.parse.quote(args.segment_id, safe="")
        result = client.request("GET", f"/v1/analyticsReportSegments/{segment_id}", {
            "fields[analyticsReportSegments]": ["url", "sizeInBytes", "checksum"]})
        if failed(result):
            return result
        return client.download_analytics_segment(args.segment_id, args.output_file)
    if not args.asset_type.isascii() or not args.asset_type.isalnum():
        raise ValueError("Asset type must be an Apple resource name, such as appScreenshots.")
    asset_id = urllib.parse.quote(args.asset_id, safe="")
    result = client.request("GET", f"/v1/{args.asset_type}/{asset_id}", {
        f"fields[{args.asset_type}]": ["fileName", "fileSize", "uploadOperations"]})
    if failed(result):
        return result
    return client.transfer_reserved_asset(args.asset_id, args.file_path)


def failed(result: dict) -> bool:
    return "error" in result or result.get("cancelled") is True


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command != "install-runtime":
            python = runtime_python()
            if Path(sys.executable).absolute() != python.absolute():
                install_runtime(PLUGIN_ROOT)
                os.execv(str(python), [str(python), str(Path(__file__).resolve()),
                                     *(sys.argv[1:] if argv is None else argv)])
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if failed(result) else 0
    except (StorageError, ValueError, OSError, StopIteration) as error:
        message = str(error) if isinstance(error, ValueError) else "Local CLI operation failed. Check files, runtime, and connection; inspect API state before repeating a write."
        print(json.dumps({"error": message}), file=sys.stderr)
        return 1
    except Exception:
        print(json.dumps({"error": "App Store Connect operation failed. No automatic retry was made; inspect API state before repeating a write."}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
