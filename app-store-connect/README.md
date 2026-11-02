# App Store Connect

Agent instructions and a Python CLI for Apple's App Store Connect REST API. The agent finds endpoint details in [Apple's current API documentation](https://developer.apple.com/documentation/appstoreconnectapi/) and uses the CLI for authentication and requests. No MCP server or generated endpoint catalog is required.

## Requirements and setup

Use Python 3.9+ and `pip`, network access for Apple requests and the first runtime install, and an App Store Connect team or individual `.p8` API key. The CLI installs `cryptography` and `keyring` in a per-user runtime automatically. Credentials are saved only in macOS Keychain, Windows Credential Manager, or Linux Secret Service; setup fails if native storage is unavailable.

Run these commands from the installed plugin directory, or use the `app-store-connect-setup` skill:

```sh
python3 scripts/manage.py setup
python3 scripts/manage.py status
```

Setup opens a temporary local browser form. Enter the Key ID, team Issuer ID for a team key, and select the downloaded `.p8` file. Keep the command running while completing the form. It verifies access with `GET /v1/apps?limit=1`, then saves the credential. Key material stays out of command arguments, chat, and the plugin directory. See [Apple's key setup instructions](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api) for account requirements and permissions.

`python3 scripts/manage.py forget` removes the local credential without revoking the key at Apple. `install-runtime` repairs the Python runtime. Existing saved credentials and the previous runtime directory remain compatible.

## Requests

Look up the endpoint and request shape in Apple's documentation, then supply its HTTP method and API path:

```sh
python3 scripts/manage.py request GET /v1/apps --query '{"limit":5}'
python3 scripts/manage.py request GET /v1/apps --query '{"filter[bundleId]":"com.example.app","fields[apps]":["name","bundleId"]}'
python3 scripts/manage.py request PATCH /v1/appStoreVersionLocalizations/LOCALIZATION_ID --body @/absolute/localization.json
```

The last example requires a JSON:API body prepared from Apple's endpoint documentation and a real localization ID. `--query` and `--body` accept JSON objects, `@file`, or `-` for stdin (only one may read stdin). Query arrays are serialized as comma-separated values. API paths start with `/v1/`, `/v2/`, or another version; query parameters go in `--query`. Requests always go to `api.appstoreconnect.apple.com`, and credentials are attached locally.

Commands print JSON to stdout; local failures print JSON to stderr. Errors and cancelled requests return a nonzero exit status. Help works without installing dependencies. API requests are not retried automatically: inspect current state before repeating a failed write. Apple validates the endpoint, body, and permissions.

High-impact deletes/revocations, submission/release, pricing/availability, and user/access requests require approval in a temporary local browser page showing the exact request. Cancellation, timeout, or browser failure sends no request. Other writes should follow the user's direct instruction.

## Downloads and assets

Binary GET responses are saved under `~/Downloads/App Store Connect/` by default. Pass `--output-file /absolute/new-file.gz` to choose another destination. Existing files are never overwritten.

```sh
python3 scripts/manage.py download-segment SEGMENT_ID --output-file /absolute/report.csv.gz
python3 scripts/manage.py upload-asset appScreenshots ASSET_ID /absolute/screenshot.png
```

`download-segment` fetches current analytics segment details and downloads in one process, checking Apple's size and checksum when supplied. `upload-asset` fetches an existing reservation and transfers the local file after checking its size and byte ranges. Reserve the asset first using the documented API; after upload, use `request PATCH` on the returned `commitPath` with the checksum and Apple's documented commit body, then verify delivery state. Failed uploads retain no progress across CLI invocations; inspect the asset and reserve again when needed.

Signed upload/download URLs stay in process memory and are hidden from output. The App Store Connect JWT is not sent to storage hosts.

## Installation

Install the plugin through the repository marketplace as described in the root [README](../README.md), then reload the host to discover its skills. If upgrading from the MCP version, reload to remove the previous server registration. The Python CLI also works directly from a checkout.

## Branding

The App Store Connect icon comes from Apple's App Store Connect website. The original source is preserved at `assets/app-store-connect-icon-original.png`; the display asset adds transparent padding.
