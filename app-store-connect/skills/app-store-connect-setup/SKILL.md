---
name: app-store-connect-setup
description: Connect or disconnect an App Store Connect API key, check the local connection, or repair its runtime setup.
---

# Connect App Store Connect

Resolve `<plugin-dir>` from this skill's installed location (two directories above this file). Run:

```sh
python3 <plugin-dir>/scripts/manage.py status
python3 <plugin-dir>/scripts/manage.py setup
```

Run setup only when no key is configured or the user requests replacement. The first credential/API command installs a per-user Python runtime from the declared requirements. To repair it, run `python3 <plugin-dir>/scripts/manage.py install-runtime`.

Setup opens a temporary loopback browser form and remains running until import succeeds or the form expires. The local link is printed to stderr; keep the command running while the person completes it. Check `status` after setup succeeds.

Use a downloaded team or individual App Store Connect `.p8` key with the roles needed for the work. Enter the Key ID, team Issuer ID only for team keys, and choose the private-key file in the form. The form verifies access with a read request and stores credentials only in Keychain, Windows Credential Manager, or Linux Secret Service. Native storage must be available. Keep the private key out of chat, CLI arguments, and the plugin directory.

An Account Holder must request API access. Generate the key in App Store Connect before importing it; see Apple's [API key instructions](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api) and [JWT requirements](https://developer.apple.com/documentation/appstoreconnectapi/generating-tokens-for-api-requests). Team keys can cover all team apps; individual keys follow user access and cannot access Sales/Finance reports or provisioning endpoints.

To disconnect, run `python3 <plugin-dir>/scripts/manage.py forget`. This removes the local credential only. Revocation happens in App Store Connect's Integrations page.
