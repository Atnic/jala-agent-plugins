---
name: app-store-connect-setup
description: Connect or disconnect an App Store Connect API key, check the local connection, or repair its runtime setup.
---

# Connect App Store Connect

Call `asc_connection_status` first. If it is not configured, call `asc_setup`. The tool opens a temporary local browser form. Use a team or individual key that has the Apple roles needed for the intended work. Team keys can cover every app in the team; individual keys follow the user's access and cannot access Sales or Finance reports.

An Account Holder must request App Store Connect API access. Generate and download the key in App Store Connect before importing it. See Apple's [API key instructions](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api) and [JWT requirements](https://developer.apple.com/documentation/appstoreconnectapi/generating-tokens-for-api-requests).

In the local form, enter the Key ID, add the team Issuer ID only for a team key, and choose the `.p8` file downloaded from App Store Connect. The form sends the key material only to the loopback helper on this computer. The helper verifies it with a read request to Apple and stores it in Keychain, Windows Credential Manager, or Linux Secret Service. Setup fails if native secure storage is unavailable. The private key is never sent to chat or stored in the plugin directory.

After setup, check status again. If the MCP server cannot start its runtime, run `python3 scripts/manage.py install-runtime` from the installed plugin directory, then reload the plugin. The first server start may also install its user-local Python runtime from the declared requirements.

To remove the saved local key, call `asc_forget_credentials` or run `python3 scripts/manage.py forget`. This removes only the local secret; it does not revoke the key in App Store Connect. To revoke a compromised key, use App Store Connect's Integrations page.
