# 9Router JALA

Version: `0.1.0`. A skills-only plugin for Codex and Claude Code that uses a
hosted [JALA 9Router gateway](https://9router.jala.tech) for chat, images, audio, embeddings, and web tools.

## Requirements and API key setup

The gateway is already deployed at **https://9router.jala.tech**. Each user
uses an API key supplied by the JALA administrator. The plugin includes a Python
request helper; it does not require users to deploy 9Router or enter its URL.
Python 3.9+, network access, and the bundled `keyring` dependency are required.
Install the helper dependencies once in an isolated per-user environment:

```bash
python3 "<plugin-root>/scripts/gateway.py" install-runtime
```

On Windows use `py -3` instead of `python3`. The helper automatically uses this
private environment when the launching Python does not have `keyring`.

After installing, ask “Set up my JALA 9Router API key.” The agent gives you a
command with the installed plugin's absolute path. Launch the local HTML form:

```bash
python3 "<plugin-root>/scripts/gateway.py" setup-web
```

The browser form masks the key and verifies it through `/v1/models`, then saves
it in **macOS Keychain** or **Windows Credential Manager**, under service
`tech.jala.9router` and account `api-key`. Windows credentials persist for the
current user on this machine. The helper selects these native encrypted stores
explicitly and falls back to a private plaintext file if native storage is unavailable. OS access prompts may
appear; the user completes them directly. Never paste the key into chat.
The saved key survives plugin updates and works across Codex and Claude Code.

For a checkout of this repository, the command is:

```bash
python3 /absolute/path/to/jala-agent-plugins/9router-jala/scripts/gateway.py setup-web
```

`NINEROUTER_KEY` can be supplied through an existing environment or managed
secret store instead; it takes precedence over the saved key. The helper does
not encrypt environment variables. Linux uses the plaintext fallback for saved keys.

The form opens when `setup-web` runs, rather than automatically during installation.
It is served on a temporary loopback URL with a session token, closes after a
successful save or 15 minutes, and never stores the key in browser storage.
The HTML source is [assets/setup.html](assets/setup.html). Opening that file
directly previews the form; submitting requires the local helper server.
The original hidden terminal prompt remains available with `gateway.py setup`.
It remains a skills package with a local helper, rather than an MCP connector.
It does not change the host agent's own model provider. Provider availability,
quota, billing, model IDs, and supported options depend on the deployment.

## Use and replace a key

```bash
python3 "<plugin-root>/scripts/gateway.py" status
python3 "<plugin-root>/scripts/gateway.py" request /v1/models
python3 "<plugin-root>/scripts/gateway.py" setup-web
python3 "<plugin-root>/scripts/gateway.py" forget
```

`status` reports configuration without showing the key. `request` loads it and
adds authentication internally. Run `setup-web` (browser) or `setup` (terminal) to replace a saved key; `forget`
removes it locally without revoking it in the dashboard. Environment overrides
remain active after forgetting a saved key. For POSTs, media output, and audio
uploads, see the [helper guide](skills/9router/references/authentication.md).

## Plaintext fallback and migration

Fallback storage is `~/.config/9router-jala/api-key`. On macOS/Linux the file
has mode `600` and its directory mode `700`. On Windows the helper removes
inherited file access and grants access to the current user using `icacls`.
If private permissions cannot be applied, saving fails. A fallback file takes
precedence over the native store because it may contain a newer key. A later
successful native save removes the fallback file. Environment overrides still
take precedence. The fallback file is not encrypted.

Migrating an older plaintext key

```bash
python3 "<plugin-root>/scripts/gateway.py" migrate
```

The helper reads the legacy `~/.config/9router-jala/api-key` internally, writes it
to the native store, confirms it reads back correctly, and then removes the old
file. Failed migration keeps the file. It does not overwrite an existing native
credential; use setup to replace it instead. Plaintext fallback files are usable for requests. Removing a file does not erase older backups.

## Skills

See the [verified model mapping and live catalog](skills/9router/references/models.md)
for the two JALA chat combos and capability defaults for Codex, OpenAI API, and Exa connections.
These request models are selected separately from the harness configuration.
`gateway.py run <skill> --body request.json` selects the configured default,
checks the live model catalog, and submits to the correct capability endpoint.

| Skill | Purpose |
| --- | --- |
| `9router` | Gateway setup, authentication, model discovery, and capability routing |
| `9router-chat` | OpenAI and Anthropic chat formats, streaming, and fallback combos |
| `9router-image` | Image generation and provider options |
| `9router-tts` | Voice discovery and text-to-speech |
| `9router-stt` | Audio transcription and subtitle formats |
| `9router-embeddings` | Embedding generation and batch inputs |
| `9router-web-search` | Web and X search through configured providers |
| `9router-web-fetch` | URL extraction to markdown, text, or HTML |

Invoke `$9router` in Codex, or ask “Use the JALA 9Router gateway to discover
available models.” In Claude Code, invoke `/9router-jala:9router` or mention
9Router in your request. Capability skills link to the packaged setup skill.
Discover models on the actual deployment before using example model IDs.

## Installation

For these unpublished working-tree changes, register this local repository:

```bash
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin add 9router-jala@jala-agent-plugins
```

If `jala-agent-plugins` already points to GitHub, use the root README's
[local checkout instructions](../README.md#from-a-local-checkout) to switch it
to the local source. Restart Codex or start a new task after installation.

For Claude Code:

```bash
claude plugin marketplace add /absolute/path/to/jala-agent-plugins
claude plugin install 9router-jala@jala-agent-plugins
```

Start a new session or run `/reload-plugins`. Resolve any existing marketplace
registration with the same name before adding a different source.

After this package is published to `main`, the same installation selectors work
with the GitHub marketplace described in the [root README](../README.md).
Installing from GitHub before publication will not include these local changes.

## Attribution and validation limits

Adapted from the [upstream 9Router skill](https://github.com/decolua/9router/blob/a99cf57239ff778b61e434c2786009d5ed1c412c/skills/9router/SKILL.md)
and its seven linked capability skills at commit
`a99cf57239ff778b61e434c2786009d5ed1c412c`. The upstream MIT license is retained
in [LICENSE.upstream](LICENSE.upstream). Local adaptations add the hosted JALA endpoint, a credential setup and
request helper, narrow discovery descriptions to 9Router requests, replace
remote skill loading with bundled links, and correct the web-fetch JavaScript
response example. The separate upstream video skill is outside this inventory.

Optional icon fields are omitted because no artwork was selected and verified.
Structural and skill-format checks do not establish gateway compatibility.
Package creation passed the repository structural validator, all eight skill
format checks, Claude's strict manifest validation, and `git diff --check`.
The installed Codex CLI has no standalone plugin validation command, so its
manifest was checked for local consistency without installing the package.
The hosted `/api/health` check returned `200` and `{"ok":true}`. Thirty-two
credential/request tests passed using mocked native stores, temporary legacy files, and mocked HTTP.
A native macOS Keychain save/read/replace/delete test passed with a disposable
dummy credential. Windows backend selection and local persistence were checked
in tests; native Windows execution has not been verified on a Windows machine. Authenticated model catalogs were checked using the key submitted in the local
form. Live smoke tests passed for the default chat and finance combos, Sunburst
image generation, embeddings, spoken-audio transcription, TTS, and Exa search/fetch.
TTS and Exa require translating catalog IDs to endpoint-specific formats; the
helper performs that translation after checking the catalog. These smoke tests
do not cover every listed model. No plugin installation is performed by this package.
