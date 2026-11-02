---
name: google-play-console-setup
description: Connect or disconnect a Google Play Console account, inspect local profile status, and repair the local runtime.
---

# Connect Google Play Console

Call `gpc_connection_status` and `gpc_list_profiles` first. If the user needs a new connection, call `gpc_setup`. This opens a temporary form served only on `127.0.0.1`; the selected OAuth client or service-account JSON file is sent to that local helper, never to chat or the plugin repository.

## Google user OAuth (default)

The user uploads the JSON file downloaded for a Google Cloud **Desktop app** OAuth client. The project must have the Android Publisher and Play Developer Reporting APIs enabled, and its OAuth consent screen must permit the requested scopes. Setup opens Google's consent page using a loopback redirect and PKCE. The local helper extracts the client ID and secret, then stores the OAuth client details and tokens only in the OS secret store. The selected file is sent only to the local helper, never to chat or the repository. The granted user role and app access remain the authority boundary.

When an external OAuth consent screen is in **Testing**, refresh tokens for these non-basic scopes expire after seven days and the user must reconnect. A production consent configuration avoids this testing-only expiry, subject to Google's verification and policy requirements. For unattended automation, a service account may be more durable.

## Optional service account

The user can select a service-account JSON key downloaded from Google Cloud. Before setup, a Play Console administrator must add that service-account email to the developer account and grant only the needed permissions. The plugin imports the JSON locally, verifies authentication, and saves it to the OS secret store. Google recommends avoiding long-lived user-managed service-account keys when alternatives are available; protect, rotate, and revoke imported keys according to the account's policy.

## Storage and profiles

Credentials are saved only in macOS Keychain, Windows Credential Manager, or Linux Secret Service. Setup stops with an error if native secure storage is unavailable; it has no plaintext fallback. Profile metadata contains profile names and auth type, but no credentials.

Multiple named profiles are supported. All API calls require a named profile.

To remove local credentials, call `gpc_forget_profile` with the exact profile name or run `python3 scripts/manage.py forget-profile <name>` in the installed plugin directory. This removes only the local profile. Revoke OAuth access or delete/revoke a service-account key in Google Cloud separately if needed.

The first MCP launch installs a user-local Python runtime from the plugin's declared requirements. If that step fails, check Python 3.9+, `pip`, network access, and the OS secret store, then run `python3 scripts/manage.py install-runtime` and restart the host.
