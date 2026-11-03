# App Store Connect

Agent instructions and a Python CLI for Apple's App Store Connect REST API. The agent finds endpoint details in [Apple's current API documentation](https://developer.apple.com/documentation/appstoreconnectapi/) and uses the CLI for authentication and requests. No MCP server or generated endpoint catalog is required.

## Requirements and setup

Use Python 3.9+ and `pip`, network access for Apple requests and the first runtime install, and an App Store Connect team or individual `.p8` API key. The CLI installs `cryptography` and `keyring` in a per-user runtime automatically. Credentials are saved only in macOS Keychain, Windows Credential Manager, or Linux Secret Service; setup fails if native storage is unavailable.

Run these commands from the installed plugin directory, or use the `app-store-connect-setup` skill:

```sh
python3 scripts/manage.py setup --profile my-app
python3 scripts/manage.py status
```

Setup opens one temporary local browser page for reporting/app management and individual purchases/refunds. Configure either service or both; `--profile` optionally prefills the purchase connection name. Existing connection status is shown, and only a connection whose Save button you submit is replaced. The reporting form accepts a team or individual App Store Connect key, verifies `GET /v1/apps?limit=1`, then saves it. The purchase form accepts a separate In-App Purchase key with its own matching issuer and app identifiers; it saves locally as unverified and offers an inline transaction verification step with explicit production/sandbox selection. Success or failure on one side does not roll back the other side. Select **Done** when finished and keep the command running until then. Key material stays out of command arguments, chat, and the plugin directory. See [Apple's key setup instructions](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api) for reporting key permissions and the [Server API section](#app-store-server-api) for purchase access.

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

## App Store Server API

Version 0.3.0 adds a separate, read-only `server` command group for individual transactions, refund history, and attempted notification deliveries. Existing reporting commands and saved credentials remain compatible. The first runtime check installs the additional [Apple Server Library](https://github.com/apple/app-store-server-library-python) dependency. Its HTTP client requires a Python installation linked against OpenSSL 1.1.1 or later for supported urllib3 2.x operation.

### Setup and verification

```sh
python3 scripts/manage.py server status --profile my-app
python3 scripts/manage.py setup --profile my-app
python3 scripts/manage.py server verify --profile my-app --environment production --transaction-id TRANSACTION_ID
python3 scripts/manage.py server forget --profile my-app
```

Profile names are explicit and independent of the reporting connection. The unified setup page includes a purchase form for the In-App Purchase Key ID, its matching Issuer ID, `.p8` file, bundle ID and numeric Apple app ID. For a dedicated purchase-only form, `server setup --profile my-app` remains available. Find the key and issuer under Users and Access → Integrations → In-App Purchase. The setup form validates and saves locally; it does **not** claim authentication succeeded. Both APIs retain OS-native secret storage with no plaintext fallback. Setup replaces only the named Server API profile and resets its verification history.

Verify inline in the unified page, or use `server verify` with a genuine store transaction ID in the explicitly selected production or sandbox environment. A successful response and signed transaction check records a timestamp for that environment. `status` reports saved configuration and past verification timestamps without contacting Apple. An expired/revoked key can fail despite a past verification timestamp. No key/issuer is inferred from reporting credentials and no automatic environment switching occurs.

401, 403, transaction-not-found, network failure and signed-data verification failure are reported separately. A failure is not a successful empty result. Recheck the matching key/issuer/app configuration after 401; never share private keys or JWTs through chat. Removing a profile does not revoke the Apple key or affect the reporting connection. Root `status` and `forget` still refer only to reporting; use the explicit `server` variants for a purchase profile.

### Reading and exporting

```sh
python3 scripts/manage.py server transaction-info --profile my-app --environment production --transaction-id TRANSACTION_ID
python3 scripts/manage.py server transaction-history --profile my-app --environment production --transaction-id TRANSACTION_ID --query '{"productIds":["com.example.monthly","com.example.annual"],"startDate":START_MS,"endDate":END_MS}'
python3 scripts/manage.py server refund-history --profile my-app --environment production --transaction-id TRANSACTION_ID --revocation-start START_MS --revocation-end END_MS --format csv --output-file /absolute/new-refunds.csv
python3 scripts/manage.py server notification-history --profile my-app --environment production --body @/absolute/notification-filters.json --output-file /absolute/new-notifications.json
```

Replace `START_MS` and `END_MS` with numeric UNIX milliseconds before running the examples. Notification filters require `startDate` and `endDate`, and may include `notificationType` (for example `REFUND`), `notificationSubtype`, `onlyFailures` and `transactionId`. Transaction filters use SDK `TransactionHistoryRequest` names: `productIds`, `productTypes`, `subscriptionGroupIdentifiers`, `sort`, `inAppOwnershipType`, `revoked`, `startDate`, and `endDate`. Arrays become repeated API query parameters through Apple's SDK, rather than the reporting CLI's comma-separated convention. Unknown filters fail locally.

Transaction-history dates filter **purchaseDate**. Refund-history reads all customer refunds before applying optional inclusive `--revocation-start` and exclusive `--revocation-end` bounds, so a September refund of a July purchase is retained. Notification-history body dates apply to Apple's notification history; an optional revocation range filters the decoded transaction rows separately.

Every signed transaction and notification is checked through Apple's library using bundled Apple trust roots, certificate checks, bundle ID, and environment. Production notification payloads additionally check Apple app ID; transaction payloads do not contain appAppleId. Certificate trust sources and SHA256 fingerprints are recorded in [assets/apple-roots/sources.json](assets/apple-roots/sources.json). Online certificate status checks are enabled; failed verification produces no decoded export.

Results include `verified`, `complete`, `scope`, `filters`, `pages`, `startedFromCursor`, `nextCursor`, and the requested transaction/app identifiers. The CLI follows pages automatically up to `--max-pages` (default 100, maximum 1000). If capped, `complete:false` and the next cursor are explicit. Resume with `--cursor` and identical filters/environment/profile. Missing or repeated pagination cursors, missing result lists, and malformed completeness indicators fail instead of reporting success. Transaction/refund history collapses repeated snapshots of a transaction ID within the collected batch, keeping the newest signing date (last encountered when unavailable/tied), and reports `duplicateSnapshotsRemoved`. When combining separately resumed exports, apply the same transaction-ID deduplication. Notification history preserves separate events, with `notificationSignedDate` and `notificationSignedDateUTC` distinct from the transaction signing timestamp. There are no automatic retries. Errors never produce a transaction export.

JSON retains metadata alongside transactions. CSV requires `--output-file` and writes a `.metadata.json` sidecar with coverage/filter information. Both destinations must be new, absolute paths; existing files are never overwritten. UNIX milliseconds are preserved and separate `*UTC` fields provide ISO timestamps. Missing transaction fields remain null; `price` is retained in Apple's original units. Account-link token `appAccountToken` is included when supplied by Apple; arbitrary backend `transaction_attributes` are not invented. Signed payload blobs, purchase tokens, names and emails are omitted.

### Coverage and read-only boundary

`complete:true` means the selected request pages have been exhausted, not that every app customer has been enumerated. Transaction/refund histories belong to the customer associated with the supplied transaction ID. Notification history includes only deliveries Apple attempted and reflects historical state at sending time; it may omit events when notification delivery was not configured. Check current transaction info/history for current revocation status. Notification records without transaction data remain visible in the JSON/CSV metadata.

The transport allows only transaction-info GET, transaction-history v2 GET, refund-history v2 GET, and notification-history POST on the explicit production/sandbox hosts. POST here reads history. Refund execution, consumption submission, test notification delivery and other Server API writes are unsupported. Redirects are disabled and HTTP calls have timeouts.

Official references: [transactions](https://developer.apple.com/documentation/appstoreserverapi/get-transaction-info), [customer history](https://developer.apple.com/documentation/appstoreserverapi/get-transaction-history), [refunds](https://developer.apple.com/documentation/appstoreserverapi/get-refund-history), and [notifications](https://developer.apple.com/documentation/appstoreserverapi/get-notification-history).

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
