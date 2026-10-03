# JALA credentials and requests

The gateway is fixed to `https://9router.jala.tech`. Users receive their API key
from the JALA administrator. The helper requires Python 3.9+, `keyring`, and network access.
It works independently of shell environment inheritance in the desktop app.

## Runtime prerequisite

Run `python3 "<plugin-root>/scripts/gateway.py" install-runtime` once to install
`requirements.txt` in a per-user virtual environment. On Windows use `py -3`.
The helper locates this runtime automatically if the launching Python lacks
`keyring`. The runtime is outside the plugin cache and survives updates.

## First use

Resolve `<plugin-root>` from this installed skill's location: it is the directory
containing `skills/` and `scripts/`. Provide the user a concrete absolute command:

```bash
python3 "<plugin-root>/scripts/gateway.py" setup-web
```

The command starts a temporary server bound to `127.0.0.1` and opens the HTML
form in the user's browser. The **user enters the key directly in that form**.
It masks the key, checks `GET /v1/models`, and saves the key only after a valid
model list response. It clears the field after success, does not use browser
storage, and stops the server after saving or after 15 minutes. The server
requires its random session token and same-origin submissions.

The agent may launch `setup-web --no-open`, then open the printed URL in the
user's browser panel. Keep the process running while the user fills in the form.
Do not read or capture the API-key field, record submissions, collect the key in
chat, or include it in tool arguments. Use process completion or `gateway.py
status` to verify that setup succeeded. If the session expires, launch it again.
For a terminal fallback, give the user `gateway.py setup` to run in their own
interactive terminal; do not operate that hidden prompt yourself.

Saved keys use macOS Keychain, Windows Credential Manager, or Linux Secret Service, with service
`tech.jala.9router` and account `api-key`. Windows uses local-machine persistence
for the current user. The native encrypted backend is selected explicitly; a private plaintext
file is used as fallback if native storage fails. The user completes any OS authorization prompt.
Do not read saved credentials using a keychain CLI or display them in tool output.

`NINEROUTER_KEY` remains an environment override and is not encrypted by the
helper. Linux explicitly uses SecretStorage with a session D-Bus and Secret
Service provider (such as GNOME Keyring, or KWallet with Secret Service enabled).
Run `install-runtime` again after upgrading to install the Linux dependency.
Without an accessible service, Linux uses the permitted plaintext fallback.
Native Linux and Windows execution have not been verified on those systems.

For older versions, run `gateway.py migrate` to move the legacy plaintext file
at `~/.config/9router-jala/api-key` into the OS store. This command never prints
the key and removes the legacy file only after the saved value reads back
correctly. It refuses to replace an existing OS credential; setup replaces it
and removes the old file after verification instead. The helper can load plaintext fallback files internally. Do not read them
into agent context. File removal cannot erase copies in backups.

`setup-web` or `setup` replaces the saved key after verification. `forget` deletes the saved key
without revoking it on the server; revoke a compromised key in the dashboard.
The HTML asset is served by the helper; opening the file directly does not
enable submission. No credentials are embedded in the plugin or its manifests. Installing the
plugin does not automatically open a credential form.

## Execute without exposing the key

Check configuration (reports no credential values):

```bash
python3 "<plugin-root>/scripts/gateway.py" status
```

Discover models:

```bash
python3 "<plugin-root>/scripts/gateway.py" request /v1/models
python3 "<plugin-root>/scripts/gateway.py" request /v1/models/image
```

For a JSON POST, write the request body to a working file without credentials:

```bash
python3 "<plugin-root>/scripts/gateway.py" request /v1/chat/completions --body request.json
python3 "<plugin-root>/scripts/gateway.py" request /v1/audio/speech --body speech.json --output speech.mp3
```

For STT, put `model` and any supported scalar options in `transcription.json`:

```bash
python3 "<plugin-root>/scripts/gateway.py" request /v1/audio/transcriptions --body transcription.json --audio-file recording.mp3
```

The helper attaches the Bearer header internally, refuses redirects, exposes only bounded, sanitized JSON error message/code/type/parameter fields,
suppresses raw bodies and credentials, never retries automatically, and saves successful responses only to new
output paths. It buffers responses, so use `stream:false` for ordinary chat.
Inspect media responses after saving; a successful JSON response can still
contain base64 data or a download URL rather than raw media. For binary images,
use the endpoint's documented `?response_format=binary` option.

Missing configuration: launch the HTML form or show the setup-web command and
wait for the user to complete it. On 401, open setup-web with a new session. For generation failures, follow the shared [error and retry rules](../SKILL.md#errors):
an explicit validation rejection permits one corrected retry within the authorized
task; ambiguous outcomes require checking completion or explicit user authorization.

Fallback files use `~/.config/9router-jala/api-key`, mode `600` in a `700`
directory on macOS/Linux, and a current-user-only file ACL applied with `icacls`
on Windows. Failure to apply private permissions aborts the save. A fallback
file takes precedence over a possibly stale native key; a successful native
save removes it. Explicit `migrate` never falls back and keeps the file on failure.
