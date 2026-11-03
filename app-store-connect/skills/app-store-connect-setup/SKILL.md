---
name: app-store-connect-setup
description: Open unified Apple setup for reporting, purchases, or both; inspect or disconnect reporting access, or repair the local runtime.
---

# Connect App Store Connect

The main setup command opens one page for reporting and purchases. For individual transaction/refund verification details, also read [app-store-server-setup](../app-store-server-setup/SKILL.md). Credentials remain separate; replacing a reporting key does not establish purchase access.

Resolve `<plugin-dir>` from this skill's installed location (two directories above this file). Run:

```sh
python3 <plugin-dir>/scripts/manage.py status
python3 <plugin-dir>/scripts/manage.py setup
# Optionally prefill an explicitly chosen purchase profile:
python3 <plugin-dir>/scripts/manage.py setup --profile NAME
```

Run setup when the requested connection is missing, the user requests setup, or replacement is authorized. A configured reporting key does not mean the purchase profile is configured. Let the person configure either service or both in the page; an existing connection is replaced only when its own Save button is submitted. The first credential/API command installs a per-user Python runtime from the declared requirements. To repair it, run `python3 <plugin-dir>/scripts/manage.py install-runtime`.

Setup opens a temporary loopback browser form and remains running until import succeeds or the form expires. The local link is printed to stderr; keep the command running while the person completes it. Check `status` after setup succeeds.

Use a downloaded team or individual App Store Connect `.p8` key with the roles needed for the work. Enter the Key ID, team Issuer ID only for team keys, and choose the private-key file in the form. The form verifies access with a read request and stores credentials only in Keychain, Windows Credential Manager, or Linux Secret Service. Native storage must be available. Keep the private key out of chat, CLI arguments, and the plugin directory. Purchase keys use their matching issuer and app identifiers, save initially as unverified, and can be verified inline with a genuine transaction and explicit environment. Select Done to finish the unified page; partial successes remain saved if the other connection fails.

An Account Holder must request API access. Generate the key in App Store Connect before importing it; see Apple's [API key instructions](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api) and [JWT requirements](https://developer.apple.com/documentation/appstoreconnectapi/generating-tokens-for-api-requests). Team keys can cover all team apps; individual keys follow user access and cannot access Sales/Finance reports or provisioning endpoints.

To disconnect, run `python3 <plugin-dir>/scripts/manage.py forget`. This removes the local credential only. Revocation happens in App Store Connect's Integrations page.
