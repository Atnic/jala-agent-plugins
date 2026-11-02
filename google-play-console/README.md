# Google Play Console

Manage Google Play Console apps and API analytics from Codex or Claude Code. This plugin exposes a separately named, typed MCP action for every operation in Google's published Android Publisher v3 and Play Developer Reporting Discovery documents. The bundled catalog currently contains **195 API actions**:

- Android Publisher API v3: 145 operations
- Play Developer Reporting API v1beta1: 25 operations
- Play Developer Reporting API v1alpha1: 25 operations (preview)

There is no free-form method/path tool. The API catalog does not cover every Play Console website action. The separate Custom App Publishing, Play Games Services, and EMM APIs are excluded.

## Features

- Inspect and manage apps, store listings, images, releases, reviews, monetization, subscriptions, access, and other API-supported resources.
- Query Play Developer Reporting API metrics with the typed beta and preview actions.
- Connect multiple named profiles using Google user OAuth (default) or an optional service account.
- Keep OAuth refresh tokens and service-account keys only in the OS-native secret store.
- Require host approval for every Android Publisher edit commit and cataloged high-impact direct write.

## Install

### Codex

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin add google-play-console@jala-agent-plugins
```

### Claude Code

```bash
claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install google-play-console@jala-agent-plugins
```

For an unpublished local checkout, follow the repository's [local marketplace instructions](../README.md#install-in-codex) and install this plugin from that marketplace.

## Connect an account

1. Install Python 3.9+ and make sure `pip` and network access are available. The first MCP launch installs an isolated, per-user runtime.
2. Create a Google Cloud **Desktop app** OAuth client and enable the Android Publisher and Play Developer Reporting APIs in that project. Configure its OAuth consent screen for the requested scopes and add test users if the app is in Testing.
3. In Codex or Claude Code, call `gpc_setup`. It opens the local setup page. Enter a profile name, choose Google user OAuth, and upload the downloaded Desktop OAuth client JSON file. Then authorize with Google.
4. Call `gpc_connection_status` and `gpc_list_profiles` to confirm the connection.

Google user OAuth follows that user's Play Console permissions. For unattended automation, an administrator can instead add a service account email to Play Console and grant only the required permissions; then call `gpc_setup` and import its JSON key through the same local form. Google recommends avoiding long-lived user-managed service-account keys when possible.

The first MCP connection installs `google-auth`, `jsonschema`, `keyring`, and `requests` into the plugin's per-user runtime. Credentials are saved in macOS Keychain, Windows Credential Manager, or Linux Secret Service. Setup fails if that OS secret store is unavailable; there is no plaintext file fallback. Multiple profiles are supported, and every API action requires an explicit profile.

For the step-by-step flow, read the [`google-play-console-setup` skill](skills/google-play-console-setup/SKILL.md).

### OAuth Testing mode

Google OAuth refresh tokens for these scopes expire after seven days when an external consent screen is in **Testing**. Reconnect the profile when prompted, or configure the OAuth consent screen for production after completing Google's applicable verification. Service accounts are an option for durable automation.

## Use the API actions

Call `gpc_find_actions` with a resource or task, such as `reviews`, `subscriptions`, `tracks update`, or `vitals metrics`. It returns exact tool names from the catalog. Call the selected tool with its schema-defined values, including the explicit `profile`. The server paginates its MCP tool list so all API actions remain discoverable.

The catalog is generated from [Android Publisher API Discovery](https://androidpublisher.googleapis.com/$discovery/rest?version=v3), [Play Developer Reporting v1beta1 Discovery](https://playdeveloperreporting.googleapis.com/$discovery/rest?version=v1beta1), and [Play Developer Reporting v1alpha1 Discovery](https://playdeveloperreporting.googleapis.com/$discovery/rest?version=v1alpha1). Alpha operations are preview; prefer beta actions in guided workflows. Successful API responses describe API state, not completion of Google Play review or rollout.

## Writes and host approvals

Google permissions granted to the OAuth user or service account are the authority boundary. Every tool requires an explicit profile. Routine reversible edits may run after the user's direct instruction. Every Android Publisher edit commit requires approval. The typed catalog also marks deletes, refunds/cancellations, user or grant changes, app-signing changes, release-state actions, price/availability changes, and product/subscription state changes as high impact.

Claude Code receives `anthropic/requiresUserInteraction` metadata on each cataloged high-impact action, so its host can prompt for that call. MCP servers cannot force Codex approval; add the per-tool entries in [`codex-high-impact-approvals.toml`](codex-high-impact-approvals.toml) to your Codex `config.toml`. Those entries set `approval_mode = "prompt"` for the current high-impact catalog actions. Refresh the file whenever the discovery catalog is regenerated.

The server never retries API writes after a timeout or network failure. Inspect the current resource or edit state before trying again. To remove a local connection, call `gpc_forget_profile`; this removes local credentials but does not revoke Google OAuth access or delete/revoke a service-account key.

## Refresh the operation catalog

From this directory, run:

```bash
python3 scripts/update_catalog.py
```

The updater fetches only Google's official Discovery documents and regenerates `operations.json` and `codex-high-impact-approvals.toml`. Review operation-count and risk-classification changes before release. `scripts/generate_discovery.py` contains the read-only and high-impact classification rules.

## Artwork

The icon is adapted from the official [Google Play Console app listing](https://play.google.com/store/apps/details?id=com.google.android.apps.playconsole). `assets/google-play-console-icon-original.png` preserves the source image; `assets/google-play-console-icon.png` is padded for the plugin's square icon slot.

## Official references

- [Android Publisher API reference](https://developers.google.com/android-publisher/api-ref/rest)
- [Play Developer Reporting API](https://developers.google.com/play/developer/reporting)
- [Google OAuth for installed applications](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google service-account best practices](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys)
- [Codex MCP tool approval configuration](https://developers.openai.com/codex/mcp)
- [Claude MCP per-tool user interaction](https://code.claude.com/docs/en/mcp#require-approval-for-a-specific-tool)
