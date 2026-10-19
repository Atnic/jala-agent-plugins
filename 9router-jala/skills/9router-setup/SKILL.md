---
name: 9router-setup
description: Configure, update, or revert the JALA 9Router model provider setup in Codex config.toml. For 9Router API requests made by plugin skills, use 9router instead.
---

# Set up Codex with JALA 9Router

Use this skill only when the user explicitly asks to set up or change Codex itself to send inference requests through JALA 9Router, or agrees when asked, “Would you also like to set up Codex to use 9Router?” A general request to set up 9Router covers the plugin API credential only and does not authorize changes to `config.toml`. This provider configuration is separate from the credential used by plugin capability skills.

## Setup

1. Resolve the installed plugin root from this skill's location; it is the directory containing `skills/` and `scripts/`. On a repository checkout, use that checkout's `9router-jala` directory.
2. If the helper runtime is not installed or needs updated dependencies, run `python3 "<plugin-root>/scripts/gateway.py" install-runtime` (Windows: `py -3`).
3. Launch `python3 "<plugin-root>/scripts/gateway.py" setup-codex` (Windows: `py -3`). Setup defaults to ChatGPT + gateway for desktop Work; the local browser form asks only for the API key. Use `--auth-mode api` only when the user explicitly requests API-only use. It verifies the user's key against `/v1/models`, saves it for the other 9Router plugin skills using the established credential form, installs the bundled [Codex model catalog](assets/models_9router_jala.json) under the active Codex home, and merges the provider settings into `config.toml`.
4. Keep the key in the local form. The Codex provider stores it in `config.toml` as `experimental_bearer_token`, so that file contains a plaintext credential. Keep this token opaque to the agent: never read its existing value into model context, display, log, or report it; let the local helper preserve or replace it. A complete TOML parse is needed to place settings safely; it happens locally, and existing values are never sent. Never ask the user to paste the key into chat.
5. Confirm the helper reports success and any retained unsupported setting, then tell the user to restart Codex. In ChatGPT mode, sign in to the intended ChatGPT account if prompted. Ask the user to verify desktop Work access; successful local configuration alone does not verify account availability.

The helper honors `CODEX_HOME` when set; otherwise it uses `~/.codex` (or `%USERPROFILE%\.codex` on Windows). It preserves unrelated settings and provider entries, updates the 9Router provider in place, and writes `models_9router_jala.json` directly under the active Codex home. The provider uses the Responses wire API and makes `9router-jala` the active model/provider alias.

Both the browser form and saved-key setup validate the configuration before changing credentials. Files are replaced atomically, but credential, catalog, and configuration changes are separate operations. If setup fails, report the helper's sanitized completion status. When it confirms the credential was saved, fix the reported local issue and retry with `setup-codex --reuse-saved-key` and the intended `--auth-mode`; a failed later write retains that credential.

Setup removes the known legacy `preferred_auth_method = "apikey"`; a customized value remains unchanged and is reported as unsupported. It also removes the ignored `features.guardianv2.thread_context` setting, regardless of value, at the root and in embedded `[profiles.<name>]` overrides in this `config.toml`. Other Guardian settings and profile choices remain unchanged. Thread-owned Guardian context is always enabled. Separate `<name>.config.toml` profile files are outside this helper's write scope; if a warning names one, inspect and update that file only with the user's authorization. Revert retains its setup-ownership rules below; it is not a general deprecation cleanup.

## Authentication modes

The default mode (`--auth-mode chatgpt`) writes `forced_login_method = "chatgpt"` and provider-scoped `requires_openai_auth = true`. This keeps ChatGPT identity available for desktop Work while retaining the JALA gateway URL, model alias, Responses protocol, and explicit provider bearer credential for inference. Setup does not sign in, log out, refresh, or modify ChatGPT credentials. In the verified desktop build, an explicit provider bearer credential takes precedence for inference; confirm compatibility when changing Codex versions. This combination fixed desktop Work access on app version `26.1013.31256`; it is not a guarantee for every version or account.

`--auth-mode api` writes `forced_login_method = "api"` and provider-scoped `requires_openai_auth = false`. This is the intentional API-only path; desktop features requiring a ChatGPT account may be unavailable.

Omitting `--auth-mode` selects ChatGPT + gateway for fresh and existing configurations, including older API-only setups. The form uses the mode selected by the command and has no sign-in selector. Setup never inspects saved ChatGPT tokens to choose a mode.

The [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) documents these keys. The official [ChatGPT-through-gateway workflow](https://learn.chatgpt.com/docs/enterprise/sign-in-with-chatgpt-through-a-gateway) describes a different managed route that forwards ChatGPT credentials to the Codex backend. This helper retains JALA bearer inference; do not substitute gateway headers, change the endpoint, or claim an upstream model or billing route from account visibility alone.

## Revert setup

Use this branch when the user asks to undo setup, remove the 9Router Codex provider, or return Codex to its default sign-in. Reverting Codex setup is separate from deleting the API credential used by the other plugin skills.

1. Resolve the installed plugin root and install the helper runtime if needed, as in Setup. Run `python3 "<plugin-root>/scripts/gateway.py" revert-codex` (Windows: `py -3`). The helper resolves the active Codex home, validates TOML, preserves the provider credential in native storage, and removes setup-owned configuration through a private atomic write.
2. Report the helper's result and any remaining 9Router references by name. Profiles and unrelated settings remain unchanged; update a profile only when explicitly requested. Missing configuration or an already-completed revert succeeds without changes. Malformed configuration, symlinks, a missing provider credential when removal is needed, inaccessible native storage, or conflicting saved credentials stop removal. Explain sanitized failures and retain the configuration for retry.
3. After a completed revert, tell the user to restart Codex and sign in if prompted. Setup never recorded the previous provider or model, so revert does not restore them. ChatGPT sign-in preferences remain. For later setup, run `python3 "<plugin-root>/scripts/gateway.py" setup-codex --reuse-saved-key` (Windows: `py -3`), adding the intended `--auth-mode` to switch modes. Only when the user also requests deleting the saved plugin credential, run `python3 "<plugin-root>/scripts/gateway.py" forget`; this does not revoke the key or clear an environment override.

The helper owns the removal rules: it removes matching setup values, the API-only login restriction, and the known legacy `preferred_auth_method = "apikey"` only while 9Router is the active provider. It preserves and reports `forced_login_method = "chatgpt"` because that account preference may predate setup; workspace restrictions also remain. It removes the global catalog reference only when it resolves to the bundled catalog, and removes the 9Router provider entry (including its auth-mode flag). Customized values and other providers remain. The catalog file stays on disk because profiles may still reference it. `backup-codex-key` remains available for standalone credential preservation; revert performs that preservation itself.

Keep this operation local. Do not send configuration contents to an external service or copy an entire old configuration over newer unrelated settings.

## Configuration example

ChatGPT mode produces the following shape in `config.toml`, preserving other settings and provider entries. API-only mode instead uses `forced_login_method = "api"` and `requires_openai_auth = false`. The catalog path is written as an absolute path for the active Codex home; replace the illustrative path below with that path when configuring manually. The local setup form verifies the key and writes it as `experimental_bearer_token`.

```toml
# Global settings
model = "9router-jala"
model_provider = "9router-jala"
forced_login_method = "chatgpt"
model_reasoning_effort = "high"
model_catalog_json = "/absolute/path/to/.codex/models_9router_jala.json"

# Other Codex settings remain here.

# Providers
[model_providers.9router-jala]
name = "9Router JALA"
base_url = "https://9router.jala.tech/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "<NINEROUTER_API_KEY>"
```

If `config.toml` is invalid or the helper reports an error, leave it unchanged and explain the sanitized failure. Do not overwrite or repair unrelated TOML settings by guesswork.
