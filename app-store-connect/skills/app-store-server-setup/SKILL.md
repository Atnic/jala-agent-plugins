---
name: app-store-server-setup
description: Configure, inspect, verify, or remove a separate local App Store Server API profile using an In-App Purchase key. Use for missing transaction access or StoreKit authentication errors; reporting API setup remains separate.
---

# Connect App Store Server API

Resolve `<plugin-dir>` two directories above this file. Select an explicit profile name, then run:

```sh
python3 <plugin-dir>/scripts/manage.py server status --profile NAME
python3 <plugin-dir>/scripts/manage.py setup --profile NAME
```

Run setup for a missing profile or when setup/replacement was requested. The unified local page shows both connections; use its Purchases and refunds section and leave an existing reporting connection in place. A dedicated `server setup --profile NAME` form is also available. The purchase form imports an In-App Purchase `.p8` key with its matching Key ID and Issuer ID, bundle ID and numeric Apple app ID. Obtain that key and issuer from Users and Access → Integrations → In-App Purchase with the appropriate Apple role. [Apple key instructions](https://developer.apple.com/documentation/appstoreserverapi/creating-api-keys-to-authorize-api-requests).

Keep the process running while the person completes the form. Credentials are saved only in the OS-native secret store, independently of reporting credentials. Saving validates the key locally and leaves access **unverified**. Verify inline in the same page with a genuine transaction ID and explicit environment, or run:

```sh
python3 <plugin-dir>/scripts/manage.py server verify --profile NAME --environment production --transaction-id TRANSACTION_ID
```

Only a successful Apple response plus signature/app/environment verification records a verification timestamp. Status displays past checks, not a guarantee of current access. Transaction payloads verify bundle/environment; notification payloads additionally verify the production Apple app ID.

401 means authentication failed; inspect the selected key/issuer pairing, active key and app configuration. 403, transaction-not-found and network/verification errors are distinct. Do not infer "no refunds" from any error, silently switch environments, reuse another connection's issuer, or print/import credentials through chat or command arguments.

`server forget --profile NAME` removes only that local profile; Apple key revocation is separate. Runtime repair uses the existing `install-runtime` command. See [the README](../../README.md#app-store-server-api) for supported operations and the read-only boundary.
