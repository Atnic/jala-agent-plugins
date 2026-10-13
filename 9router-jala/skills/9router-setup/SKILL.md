---
name: 9router-setup
description: Configure, update, or revert the JALA 9Router model provider setup in Codex config.toml. For 9Router API requests made by plugin skills, use 9router instead.
---

# Set up Codex with JALA 9Router

Use this skill when the user wants Codex itself to send inference requests through JALA 9Router. This is separate from configuring the 9Router plugin's API credential for its capability skills.

## Setup

1. Resolve the installed plugin root from this skill's location; it is the directory containing `skills/` and `scripts/`. On a repository checkout, use that checkout's `9router-jala` directory.
2. If the helper runtime is not installed or needs updated dependencies, run `python3 "<plugin-root>/scripts/gateway.py" install-runtime` (Windows: `py -3`).
3. Launch `python3 "<plugin-root>/scripts/gateway.py" setup-codex` (Windows: `py -3`). The local browser form verifies the user's key against `/v1/models`, saves it for the other 9Router plugin skills using the established credential form, installs the bundled [Codex model catalog](assets/models_9router_jala.json) under the active Codex home, and merges the provider settings into `config.toml`.
4. Keep the key in the local form. The Codex provider stores it in `config.toml` as `experimental_bearer_token`, so that file contains a plaintext credential. Keep this token opaque to the agent: never read its existing value into model context, display, log, or report it; let the local helper preserve or replace it. A complete TOML parse is needed to place settings safely; it happens locally, and existing values are never sent. Never ask the user to paste the key into chat.
5. Confirm the helper reports success, then tell the user to restart Codex. Restarting Codex is the final setup step.

The helper honors `CODEX_HOME` when set; otherwise it uses `~/.codex` (or `%USERPROFILE%\.codex` on Windows). It preserves unrelated settings and provider entries, updates the 9Router provider in place, and writes `models_9router_jala.json` directly under the active Codex home. The provider uses the Responses wire API and makes `9router-jala` the active model/provider alias.

## Revert setup

Use this branch when the user asks to undo setup, remove the 9Router Codex provider, or return Codex to its default sign-in. Reverting Codex setup is separate from deleting the API credential used by the other plugin skills.

1. Resolve the active Codex home using `CODEX_HOME`, falling back to `~/.codex` (Windows: `%USERPROFILE%\.codex`). Install the helper runtime if needed, and use its Python interpreter with `tomlkit` for the local edit.
2. Parse `config.toml` locally without printing its contents or token values. If it is missing, report that there is no Codex configuration to revert. For invalid TOML or a symlink, leave it unchanged and report a sanitized error.
3. If the active `model_provider` is `9router-jala`, remove that setting and the setup-owned global settings: remove `model` only when it equals `9router-jala`, `preferred_auth_method` only when it equals `apikey`, `forced_login_method` only when it equals `api`, and `model_reasoning_effort` only when it equals `high`. Preserve settings with other values and all unrelated configuration. Removing these overrides returns Codex to its defaults; setup does not save the previous model/provider, so do not claim to restore the previous configuration. If the user requests a particular prior provider or model, use their specified values instead.
4. Remove `model_catalog_json` only when its resolved path equals `<active-codex-home>/models_9router_jala.json`. Remove the `model_providers.9router-jala` table, including its bearer token; preserve every other provider. Leave the catalog file on disk, since other configuration profiles may still reference it.
5. Serialize and reparse the result locally, then write it with the helper's `atomic_private_write`. Verify locally that the 9Router provider entry and targeted overrides are gone, without displaying credentials. Preserve any remaining settings that reference 9Router (for example, a profile), and report their names so the user knows those profiles still need an explicit update.
6. Tell the user to restart Codex and sign in if prompted. The saved plugin API credential remains available. Only when the user also requests deleting that credential, run `python3 "<plugin-root>/scripts/gateway.py" forget` (Windows: `py -3`); this removes the saved key without revoking it or clearing an environment override.

Keep this operation local. Do not send configuration contents to an external service or copy an entire old configuration over newer unrelated settings.

## Configuration example

Setup produces the following shape in `config.toml`, preserving other settings and provider entries. The catalog path is written as an absolute path for the active Codex home; replace the illustrative path below with that path when configuring manually. The local setup form verifies the key and writes it as `experimental_bearer_token`.

```toml
# Global settings
model = "9router-jala"
model_provider = "9router-jala"
preferred_auth_method = "apikey"
forced_login_method = "api"
model_reasoning_effort = "high"
model_catalog_json = "/absolute/path/to/.codex/models_9router_jala.json"

# Other Codex settings remain here.

# Providers
[model_providers.9router-jala]
name = "9Router JALA"
base_url = "https://9router.jala.tech/v1"
wire_api = "responses"
experimental_bearer_token = "<NINEROUTER_API_KEY>"
```

If `config.toml` is invalid or the helper reports an error, leave it unchanged and explain the sanitized failure. Do not overwrite or repair unrelated TOML settings by guesswork.
