---
name: app-store-server-api
description: Read and verify individual App Store purchase transactions, customer transaction/refund histories, or attempted server notification deliveries. Use for invoice reconciliation and revocation dates; aggregate sales reports use app-store-connect.
---

# App Store Server API

Resolve `<plugin-dir>` two directories above this file. Read [the CLI reference](../../README.md#app-store-server-api) for command arguments and export semantics. Look up current endpoint fields in [Apple's Server API documentation](https://developer.apple.com/documentation/appstoreserverapi).

Use an explicitly selected local profile and production/sandbox environment. Check `python3 <plugin-dir>/scripts/manage.py server status --profile NAME`; if missing or authentication fails, use [app-store-server-setup](../app-store-server-setup/SKILL.md). Never borrow the Issuer ID or key from the reporting connection or scan the filesystem for a key.

```sh
python3 <plugin-dir>/scripts/manage.py server transaction-info --profile NAME --environment production --transaction-id TRANSACTION_ID
python3 <plugin-dir>/scripts/manage.py server refund-history --profile NAME --environment production --transaction-id TRANSACTION_ID --revocation-start START_MS --revocation-end END_MS
python3 <plugin-dir>/scripts/manage.py server transaction-history --profile NAME --environment production --transaction-id TRANSACTION_ID --query @/absolute/filters.json
python3 <plugin-dir>/scripts/manage.py server notification-history --profile NAME --environment production --body @/absolute/filters.json
```

Transaction-history filters use the SDK request names (`productIds` as an array, `startDate`/`endDate` in UNIX milliseconds). Date filters there select purchase dates. To investigate refunds during a period, collect refund history without restricting purchase dates, then use the inclusive `--revocation-start` and exclusive `--revocation-end` filters. Notification history requires body `startDate` and `endDate`; use `notificationType: "REFUND"` when appropriate.

The CLI verifies Apple's signed payloads and follows pagination up to `--max-pages` (default 100). Inspect `complete`, `scope`, `startedFromCursor`, and `nextCursor`. Resume an incomplete response with `--cursor`, preserving every original filter. Empty successful results differ from authentication, network, missing-field, or verification failures. Errors produce no transaction export.

Customer transaction/refund history covers the customer behind the supplied transaction ID, not every app customer. Notification history covers attempted deliveries and may omit purchases or refunds if delivery was not configured. Notification transactions describe their state when sent; query transaction info/history for current state. Report coverage limitations even when all pages have been read.

For a file export add `--output-file /absolute/new-file.json`; for CSV also add `--format csv`. CSV has a `.metadata.json` sidecar preserving completeness and filters. Original timestamp milliseconds and derived UTC fields are separate. `price` retains Apple's units; interpret currency/price against the current schema before comparing invoices. Missing fields remain null; do not invent `transaction_attributes` or infer customer identity from amounts. `appAccountToken` is included only if Apple supplies it.

This command group reads only. It cannot execute refunds, change transactions, send consumption information, or send test notifications. HTTP POST notification-history is a historical read. Keep JWTs, private keys, signed receipt blobs and customer names/emails out of handoffs. Store IDs and requested account-link tokens can be exported for authorized reconciliation.
