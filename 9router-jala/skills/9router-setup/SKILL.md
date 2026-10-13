---
name: 9router-setup
description: Configure Codex to use JALA 9Router as its model provider or update the 9Router settings in Codex config.toml. For 9Router API requests made by plugin skills, use 9router instead.
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
