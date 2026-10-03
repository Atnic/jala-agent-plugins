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
it in **macOS Keychain**, **Windows Credential Manager**, or **Linux Secret Service**, under service
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
not encrypt environment variables. Linux uses Secret Service when available, with the same plaintext fallback otherwise.

The form opens when `setup-web` runs, rather than automatically during installation.
It is served on a temporary loopback URL with a session token, closes after a
successful save or 15 minutes, and never stores the key in browser storage.
The HTML source is [assets/setup.html](assets/setup.html). Opening that file
directly previews the form; submitting requires the local helper server.
The original hidden terminal prompt remains available with `gateway.py setup`.
It remains a skills package with a local helper, rather than an MCP connector.
It does not change the host agent's own model provider. Provider availability,
quota, billing, model IDs, and supported options depend on the deployment.

## Linux credential storage

The helper explicitly selects the Freedesktop Secret Service backend through
`SecretStorage`, installed by `install-runtime` on Linux. A running session
D-Bus and a Secret Service provider such as GNOME Keyring are required. KWallet
works when its Secret Service interface is enabled; a KWallet-only D-Bus service
is not selected. Users complete any desktop unlock prompt themselves.

On headless systems without an accessible Secret Service, setup saves the
permitted plaintext fallback with private permissions. `NINEROUTER_KEY` remains
an alternative. Run `install-runtime` again after upgrading to install the Linux
dependency. The private runtime is located at
`~/.config/9router-jala/runtime`, as on macOS.

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
| `9router` | JALA setup, credentials, model defaults, and capability routing |
| `9router-chat` | OpenAI and Anthropic chat formats, streaming, and fallback combos |
| `9router-image` | Image generation and provider options |
| `9router-tts` | Voice discovery and text-to-speech |
| `9router-stt` | Audio transcription and subtitle formats |
| `9router-embeddings` | Embedding generation and batch inputs |
| `9router-web-search` | Web and X search through configured providers |
| `9router-web-fetch` | URL extraction to markdown, text, or HTML |

Invoke `$9router` in Codex, or ask “Use the JALA 9Router gateway.”
In Claude Code, invoke `/9router-jala:9router`. This entry point loads the JALA
credential helper and model defaults before reading a capability skill. The
seven capability skills each require reading this local entry point before
execution, including when invoked directly. The helper loads the saved key even
when the shell has no `NINEROUTER_URL` or `NINEROUTER_KEY`.

The helper reports bounded, sanitized JSON error diagnostics. Explicit validation
rejections allow one corrected retry under the shared skill rules; timeouts and
unclear generation outcomes require checking completion or user authorization.
The helper itself never repeats a request automatically.

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

The seven capability `SKILL.md` files are minimally adapted from
[decolua/9router at `a99cf57239ff`](https://github.com/decolua/9router/tree/a99cf57239ff778b61e434c2786009d5ed1c412c/skills).
The `9router` entry point has minimal JALA changes: setup/helper guidance,
model-default references, bundled capability links, and API-key recovery.
Each capability replaces its generic environment setup paragraph with a required
link to the local entry point; its remaining upstream content is preserved.
There is no separate wrapper skill.

[upstream.json](upstream.json) records the commit, hashes for unchanged files,
and the original hashes and changes for adapted skills. An automated test
reverses the capability setup substitution and verifies the seven upstream hashes
and MIT license. The license is
retained in [LICENSE.upstream](LICENSE.upstream). Model mappings and credential
instructions live in the entry point's references and the helper. The separate
upstream video skill is outside the entry point's inventory.

The logo and composer icon use the user-supplied 9Router hub artwork, preserved
unchanged in `assets/9router-logo.png` (112 × 112). `9router-icon.svg` embeds the
original with an 8-pixel outer margin on a 128-pixel canvas and rounded clipping
to hide its opaque cream corner pixels. The artwork is centered without
stretching. A rendered preview was inspected; actual host icon display has not
been verified. This replaces the upstream numeric favicon previously selected.
Structural and skill-format checks do not establish gateway compatibility.
Package creation passed the repository structural validator, all eight skill
format checks, Claude's strict manifest validation, and `git diff --check`.
The installed Codex CLI has no standalone plugin validation command, so its
manifest was checked for local consistency without installing the package.
The hosted `/api/health` check returned `200` and `{"ok":true}`. Forty-two
credential/request tests passed using mocked native stores, temporary legacy files, and mocked HTTP.
A native macOS Keychain save/read/replace/delete test passed with a disposable
dummy credential. Windows backend selection and local persistence were checked
in tests; native Windows and Linux Secret Service execution have not been verified on their respective systems. Linux backend selection and unavailable-service fallback are covered with mocks. Authenticated model catalogs were checked using the key submitted in the local
form. Live smoke tests passed for the default chat and finance combos, Sunburst
image generation, embeddings, spoken-audio transcription, TTS, and Exa search/fetch.
TTS and Exa require translating catalog IDs to endpoint-specific formats; the
helper performs that translation after checking the catalog. These smoke tests
do not cover every listed model. No plugin installation is performed by this package.
