---
name: crisp-jala-setup
description: Set up Crisp JALA, save its first browser session, explicitly replace a session, or recover a missing, expired, or invalid connection. Use this whenever a JALA operation has no working saved connection.
---

# Crisp JALA setup

Use this skill for an explicit setup or replacement request, or when a JALA
operation cannot continue because its saved connection is missing, expired, or
confirmed invalid.
For HTTP 403, check route and workspace permissions before replacing a session.
It saves the logged-in user's session in the operating system's native secret
store; it does not create a workspace API token.

## Workflow

1. **Resolve the helper.** Find `scripts/crisp_api.py` in the bundled `crisp-jala`
   skill directory and read its [connection reference](../crisp-jala/references/connection.md).
   Keep the helper path relative to the installed plugin, not a source checkout.
2. **Prepare the runtime.** Reuse the persistent runtime if present. Otherwise run
   `<HOST_PYTHON> <HELPER_PATH> install-runtime` (`python3` on macOS/Linux,
   `python` on Windows) and use the Python path it returns. Run `status` only with
   that runtime. If `status` reports a configured connection and replacement was
   not requested, make one read-only inbox-list request. If it succeeds, finish
   setup or resume the original task without recapturing the session. Capture a
   new session only when the connection is missing, confirmed invalid, or the user
   asked to replace it.
3. **Open the right browser.** Reuse an authenticated Crisp tab when available.
   Honor the user's browser choice and exclusions; when no preference is given,
   prefer the in-app browser if it supports network inspection. If Crisp asks for
   login, let the user enter their password and complete MFA.
4. **Capture a supported request.** Observe a real GET request to the exact JALA
   inbox. Prefer `/api/v1/website/bca9165d-d26a-4a8f-a8d5-5625fb1a3f2b/conversations/{page}`.
   If the inbox does not issue that request, a message-list request may be used
   only for a conversation the inbox clearly marks as already read. Do not open an
   unread or uncertain conversation to create a request. If no supported request
   is available, report that blocker and leave Crisp state untouched.
5. **Import privately.** Send the request URL and Basic authorization header from
   browser memory to `import-session` over stdin using the procedure in the
   connection reference. The helper validates the exact origin, workspace, and
   read access before saving. Keep credential values and conversation content out
   of output, chat, screenshots, command arguments, and files.
6. **Verify and resume.** Confirm `status` and make one read-only inbox-list
   request. Report whether the connection is saved and the HTTP status; do not
   include customer content. For setup-only requests, stop after verification.
   If setup was needed for another task, resume that task with the saved session.

Completion: `status` reports a saved native connection and a read-only JALA inbox
request succeeds, or the exact browser, runtime, or secret-store blocker is
reported.

## Connection replacement

When replacing a rejected or expired session, preserve the old saved connection
until a newly captured session passes verification. The helper does this on
import. Do not retry a write after an authentication failure; verify its state
before continuing the original task.
