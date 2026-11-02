#!/usr/bin/env python3
"""Download Google's official Discovery documents and refresh the typed action catalog."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

from generate_discovery import API_SOURCES, generate


OUTPUT = Path(__file__).parents[1] / "operations.json"
APPROVALS = Path(__file__).parents[1] / "codex-high-impact-approvals.toml"
USER_AGENT = "jala-google-play-console-mcp/0.1.0 (Google API Discovery catalog updater)"


def write_codex_approvals(catalog: dict) -> None:
    high_impact = [item["name"] for item in catalog["operations"] if item.get("riskCategory")]
    lines = [
        "# Copy these tool entries into your Codex config.toml to require a prompt.",
        "# Refresh this file when operations.json is regenerated.",
        "",
    ]
    for name in high_impact:
        lines.extend([
            f'[plugins."google-play-console@jala-agent-plugins".mcp_servers.google_play_console.tools."{name}"]',
            'approval_mode = "prompt"',
            "",
        ])
    APPROVALS.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    documents = []
    hashes = []
    for source in API_SOURCES:
        request = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
        except (OSError, TimeoutError) as error:
            raise SystemExit(f"Could not download Google's {source['name']} {source['version']} Discovery document: {error}") from None
        if len(raw) > 8 * 1024 * 1024:
            raise SystemExit(f"Google's {source['name']} {source['version']} Discovery document exceeded the 8 MiB limit.")
        try:
            document = json.loads(raw)
        except (UnicodeError, ValueError):
            raise SystemExit(f"Google's {source['name']} {source['version']} Discovery document was not valid JSON.") from None
        if document.get("name") != source["name"] or document.get("version") != source["version"]:
            raise SystemExit(f"Google returned an unexpected Discovery document for {source['name']} {source['version']}.")
        documents.append((source, document))
        hashes.append({
            "api": source["name"],
            "version": source["version"],
            "sha256": hashlib.sha256(raw).hexdigest(),
        })

    catalog = generate(documents)
    catalog["specSha256"] = hashes
    OUTPUT.write_text(json.dumps(catalog, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    write_codex_approvals(catalog)
    print(json.dumps({
        "operationCount": catalog["operationCount"],
        "apis": [{"name": item["name"], "version": item["version"], "status": item["status"]} for item in catalog["apis"]],
        "output": str(OUTPUT),
        "codexApprovals": str(APPROVALS),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
