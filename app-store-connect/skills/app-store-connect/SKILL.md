---
name: app-store-connect
description: Use App Store Connect for sales reports and app management, or route individual purchase and refund investigations to the App Store Server API skills.
---

# App Store Connect

For individual purchase transactions, revocation/refund dates, or server notification history, use [app-store-server-api](../app-store-server-api/SKILL.md). Its In-App Purchase credentials are separate from this reporting connection; a successful `/v1/apps` request does not verify Server API access.

Look up the current endpoint, HTTP method, query parameters, JSON:API body, permissions, and workflow in [Apple's API documentation](https://developer.apple.com/documentation/appstoreconnectapi/) before making requests. Search official Apple documentation for the user's task; the plugin supplies authentication and transport rather than a bundled API catalog.

Resolve `<plugin-dir>` from this skill's installed location (two directories above this file). Run the Python CLI through the shell:

```sh
python3 <plugin-dir>/scripts/manage.py status
python3 <plugin-dir>/scripts/manage.py request GET /v1/apps --query '{"limit":5}'
```

If no key is configured, follow the `app-store-connect-setup` skill. Use `request --help` for arguments and [the plugin README](../../README.md) for local CLI behavior. Pass the endpoint path separately from query parameters. For large payloads, use `--body @/absolute/body.json` or `--body -` for stdin. Query arrays become comma-separated values.

Get resource IDs from API results and follow Apple's documented relationships and pagination. Read the current resource before editing it. Run writes after the user's direct instruction. High-impact requests require approval in a local browser page; let the person review it. Check the CLI exit status and returned HTTP status/data before reporting success. After a timeout or connection failure, inspect API state before repeating a write; requests are never retried automatically.

For binary reports, use an absolute new `--output-file` path or the default Downloads folder. For analytics segments, use `download-segment <segment-id>` to fetch the signed URL and download within one command. For reserved metadata assets, use `upload-asset <asset-type> <asset-id> /absolute/file`; follow Apple's documentation to commit the returned checksum using `request PATCH`, then verify delivery state. These helpers keep temporary signed URLs out of output.

The key's Apple permissions determine access. If Apple rejects an operation, inspect the documented key type, roles, and app scope required for that endpoint. Report Apple's returned state: submission success does not mean Apple approved the app.
