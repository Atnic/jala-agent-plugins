---
status: accepted
---

# Google Play Console plugin scope and identity

The `google-play-console` plugin will expose each operation in the official Android Publisher v3 and Play Developer Reporting v1beta1 and v1alpha1 Discovery documents as its own typed action, with guided workflows layered on those actions. It excludes Play Console monthly sales and financial CSV exports, the separate Custom App Publishing API, Play Games Services, and EMM APIs. Credentials may use a Google user's OAuth grant or an optional service account; OAuth is the default, installers supply the Desktop OAuth client JSON file, and local setup uses loopback with PKCE. Credentials are stored only in the OS-native secret store. Multiple named profiles are supported, and every operation requires an explicit profile.

Google identity permissions remain the authority boundary. The plugin will require host approval for every Android Publisher edit commit and for classified direct high-impact writes. Claude Code can force interaction using tool metadata; Codex approval remains a per-tool user configuration. Testing-mode OAuth refresh-token expiry, Google API/Console permission prerequisites, and UI-only Play Console operations must be documented.
