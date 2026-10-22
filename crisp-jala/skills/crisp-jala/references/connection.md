# Browser login and saved user session

Use for setup, missing credentials, replacement, or authentication failures.
Setup uses the Crisp user session observed in an authenticated browser request.
The user logs in themselves, including password, SSO, and MFA. No workspace-token
creation, token-entry form, or manual environment variables are required.

Honor the user's browser preference and exclusions. If no preference is given,
prefer the in-app browser when it supports network inspection. If the user rules
out the available browser, report that blocker instead of switching silently.

Requires Python 3.9+, browser automation with network-request inspection, and
native OS secret storage: macOS Keychain, Windows Credential Manager, or Linux
Secret Service. This plugin supplies the helper and workflow, not a browser or a
network-inspection MCP server. If the host lacks network inspection or a way to
transfer captured values privately to a subprocess, report that concrete blocker;
do not expose the credential in tool output to bridge tools.

## Runtime and existing connection

Resolve `<SKILL_DIR>` from this installed skill, and reuse its runtime if present.
If it is missing, run `install-runtime` with the host's Python 3.9+ before running
`status`; do not run `status` with the system Python. Bootstrap using the host's
Python command (`python3` on macOS/Linux, `python` on Windows):

```bash
<HOST_PYTHON> <SKILL_DIR>/scripts/crisp_api.py install-runtime
```

Use the Python path returned by that command for all subsequent helper commands.
It lives at `~/.config/crisp-jala/runtime/bin/python` on macOS/Linux or
`~/.config/crisp-jala/runtime/Scripts/python.exe` on Windows. Runtime and saved
secrets remain outside the plugin cache and survive plugin updates.

```bash
<RUNTIME_PYTHON> <SKILL_DIR>/scripts/crisp_api.py status
```

If configured, reuse it. On HTTP 401/403 check the route and workspace permissions;
when the session has expired, repeat browser login and import a fresh session.
A saved user session can expire or be revoked by logout. Do not claim permanent
access, silently retry writes, or change the credential type to bypass an error.

## Capture the actual inbox request

1. Reuse or open `https://app.crisp.chat/website/bca9165d-d26a-4a8f-a8d5-5625fb1a3f2b/inbox/`.
   If a login page appears, hand it to the user and continue after login.
2. Enable network observation using the available browser's documented API.
   For `cua_repl`, discover the tab's `cdp` capability and read its documentation.
   Enable `Network`, record an event cursor, then reload the inbox normally.
3. Read `Network.requestWillBeSent` events from that cursor, paging if needed.
   Select a **GET** request to the exact HTTPS host `app.crisp.chat` with path
   `/api/v1/website/bca9165d-d26a-4a8f-a8d5-5625fb1a3f2b/conversations/{page}`
   or `/api/v1/website/.../conversation/{session}/messages` for that workspace.
   Prefer the inbox list. If it emits no list request, use a message-list request
   only after the inbox clearly marks that conversation as already read. Do not
   open an unread or uncertain conversation to create a request; stop and report
   the blocker if no safe request is available.
4. Keep the selected request in browser-runtime memory. Read its `Authorization`
   header case-insensitively and require `Basic`. Print only route, method, header
   names, or authentication scheme when debugging. Never print header values,
   decoded credentials, cookies, complete network events, or request dumps.

Observed on 2026-10-21: the inbox uses a Basic user-session credential and no
`X-Crisp-Tier`. Use the actual observed header, not an inferred workspace token.
If the authentication scheme changes, stop and report the mismatch.

## Import without revealing the secret

Send only `request_url` and `authorization` as JSON through stdin to:

```bash
<RUNTIME_PYTHON> <SKILL_DIR>/scripts/crisp_api.py import-session
```

Do this directly from the runtime holding the request, without rendering the
payload in chat/tool output, interpolating it into a command, writing a file, or
using the clipboard. For a Node-capable browser runtime, use `spawnSync` with the
`input` option. Resolve `runtimePython` and `helperPath` from the installed helper
and runtime first; `observedRequest` below is the selected GET request from the
network event, not a new request or a local-storage lookup:

```javascript
const authorization = Object.entries(observedRequest.headers)
  .find(([key]) => key.toLowerCase() === 'authorization')?.[1];
const { spawnSync } = await import('node:child_process');
const result = spawnSync(runtimePython, [helperPath, 'import-session'], {
  input: JSON.stringify({request_url: observedRequest.url, authorization}),
  encoding: 'utf8', timeout: 45000
});
// The helper emits only sanitized status. Never emit its stdin or network events.
nodeRepl.write({exitCode: result.status, saved: result.status === 0});
```

The helper validates the request origin/path, decodes the Basic pair in memory,
verifies `GET https://api.crisp.chat/v1/website/{website_id}`, and saves the pair
and workspace together under service `tech.jala.crisp`, account `connection`.
A failed verification leaves the previously saved connection unchanged. No
plaintext fallback exists. If the native store is unavailable or locked, fix its
access and retry. Linux needs an available Secret Service session.

Confirm `status` and make one inbox-list read using the saved connection. Report
HTTP status and a count rather than customer content when testing setup. This
verifies read access, not every route's permissions. Disable network capture and
clear temporary variables holding headers, network events, or decoded secrets.
For setup-only requests, stop after this verification; no customer replies or
other Crisp mutations are authorized by setup.

## Forget or replace

Repeat login/capture/import to replace a saved session. Remove the local copy with:

```bash
<RUNTIME_PYTHON> <SKILL_DIR>/scripts/crisp_api.py forget
```

This does not log the user out of Crisp or revoke the session there. Existing
explicit user authorization covers the requested setup or local removal.
