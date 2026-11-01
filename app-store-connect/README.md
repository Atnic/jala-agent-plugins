# App Store Connect

An MCP server and agent skills for App Store Connect. The server exposes each HTTP operation in Apple's published OpenAPI specification as a separate named action with an operation-specific schema. It includes read and write operations, not a free-form REST caller.

The initial catalog is generated from App Store Connect API 4.5.1 and contains 1,303 operations. Use `asc_find_actions` to locate an operation by resource or task. Apple publishes a newer OpenAPI file as its API changes; refresh the catalog with `python3 scripts/update_openapi.py` and review the generated actions and risk categories.

## Capabilities

- Read and download sales, finance, analytics, and power/performance reports.
- Manage apps, metadata, localizations, in-app purchases, subscriptions, reviews, TestFlight, provisioning, users, Xcode Cloud, and other resources exposed by the API.
- Reserve, locally upload, commit, and check binary metadata assets without exposing Apple's temporary signed upload URLs to the model.
- Use team or individual App Store Connect API keys. Apple applies the role and app scope configured for the key.
- Require a local browser approval before delete/revoke, submission/release, pricing/availability, and user/access changes.
- Store the `.p8` key only in the operating system secret store.

The API does not expose every App Store Connect website action. Apple documents app creation and build upload as website/Xcode/Transporter tasks rather than these REST operations. Apple also warns that API writes affect production data.

See Apple's [App Store Connect API documentation](https://developer.apple.com/documentation/appstoreconnectapi/) for current endpoint behavior and key requirements.

## Requirements

- Codex or Claude Code with local stdio MCP support.
- Python 3.9+ and `pip`; the first MCP launch installs `cryptography`, `jsonschema`, and `keyring` into a per-user runtime.
- macOS Keychain, Windows Credential Manager, or Linux Secret Service. The server fails closed if the native secret store is unavailable.
- App Store Connect API access and a downloaded team or individual `.p8` key. A team key needs its Issuer ID; an individual key does not.

Team keys apply across all apps in the team and use their assigned role. Individual keys use the associated user's role and app access; Apple excludes Sales and Finance reports and provisioning endpoints from individual keys.

## Setup

After installing the plugin and reloading the host, invoke the `app-store-connect-setup` skill or call `asc_setup`. A local browser form imports the key, makes a safe `GET /v1/apps?limit=1` verification request, and saves the credential in the OS secret store. The `.p8` file is never stored in the repository or plugin cache. `asc_connection_status` reports whether a key is configured; `asc_forget_credentials` removes it locally without revoking it at Apple.

## Use

Ask for a task such as “get last month's sales report,” “show recent reviews for this app,” “assign the latest build to the internal TestFlight group,” or “update this localization.” The skill finds and calls the corresponding named API actions. Binary report downloads are saved under `~/Downloads/App Store Connect/`; pass an absolute `outputFile` on the action to select another new destination. For analytics report segments, fetch the details with `url`, `sizeInBytes`, and `checksum`, then use `asc_download_analytics_segment` promptly; its temporary signed URL stays in local memory. For metadata assets, use the reservation action, then `asc_transfer_reserved_asset` with the returned asset ID and local file path, then the typed commit action.

High-impact requests open a temporary loopback browser page that shows the exact endpoint and request details. A person must approve the request there before the server sends it. Cancel, timeout, or an unavailable browser means no request is sent. Other writes still require the user's direct instruction.

## Host setup and installation

Install from the repository marketplace or a local checkout using the root [README](../README.md). Both host packages use a local stdio MCP process and the same per-user credential store. Restart/reload the selected host after installation.

## API source

See [UPSTREAM.md](UPSTREAM.md) for the Apple source URL, API version, source hash, and refresh procedure.

## Branding

The plugin's `logo` and `composerIcon` use Apple's App Store Connect sign-in logo, served by the [App Store Connect website](https://appstoreconnect.apple.com) at [this official PNG asset](https://appstoreconnect.apple.com/static/img/app_store_connect_icon@3x.1768505445909.png). The original 150×150 source is preserved at `assets/app-store-connect-icon-original.png`. The display asset at `assets/app-store-connect-icon.png` adds 15 pixels of transparent padding on each side, for a 180×180 square canvas.
