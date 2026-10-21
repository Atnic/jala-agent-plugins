# Crisp JALA

Version 0.1.0. Skills for JALA customer support through the Crisp REST API,
packaged for Codex and Claude Code.

## Included skills

- `crisp-jala`: JALA workspace routing and JALA-only saved credentials.
- `crisp`: API workflow and references for conversations, messages, people,
  visitors, workspace settings, campaign templates, and analytics.

Both skills are bundled; no separate base-skill installation is needed. For
JALA work, invoke `crisp-jala` first. Example: “Use Crisp JALA to find unresolved
customer conversations and summarize them.” Sending and changing data follows
the user's authorized scope; reading conversations does not authorize replies.

## Requirements and setup

The primary setup flow is **open Crisp → user logs in → capture the user-session
credential from an inbox request → verify → save to the OS secret store**.
Users do not generate a workspace API token, fill in a token form, or set env.

Ask “Set up Crisp JALA.” The agent opens the JALA inbox, lets you complete login
and MFA, and observes the actual GET request for the conversation list. It transfers
that request's Basic authentication header directly to the helper through stdin,
without displaying the token pair or writing it to a file. The helper verifies
read access, then saves the user credential and workspace ID in macOS Keychain,
Windows Credential Manager, or Linux Secret Service. Subsequent requests load the
saved connection automatically.

Requires Python 3.9+, shell execution, an available native secret store, and a
browser tool with network inspection and private subprocess transfer. The plugin
does not install a browser capability. Linux requires an available Secret Service
session. If the browser integration or native store is unavailable, setup reports
the blocker. No plaintext fallback or static credential is bundled.

The default JALA workspace is `bca9165d-d26a-4a8f-a8d5-5625fb1a3f2b`.
The API URL is fixed to `https://api.crisp.chat`. The user-session Basic header
was verified from Crisp's inbox request on 2026-10-21. Sessions can expire or be
revoked; repeat login capture to replace an invalid session. Saving a session does
not convert it to a permanent workspace token.

For helper/runtime commands and the capture procedure, see the
[connection workflow](skills/crisp-jala/references/connection.md). After setup:

```bash
<RUNTIME_PYTHON> <SKILL_DIR>/scripts/crisp_api.py status
<RUNTIME_PYTHON> <SKILL_DIR>/scripts/crisp_api.py request 'conversations/1?per_page=20'
```

`forget` removes the local saved connection without revoking the session in Crisp.
Saved credentials survive plugin updates. Authorization follows the active host's
permissions and the user's instructions; setup does not authorize customer replies.

## Try the local unpublished package

From this checkout, register its absolute path as your marketplace source:

```bash
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin add crisp-jala@jala-agent-plugins
```

For Claude Code:

```bash
claude plugin marketplace add /absolute/path/to/jala-agent-plugins
claude plugin install crisp-jala@jala-agent-plugins
```

If the same marketplace name already points to GitHub, follow the root
[local checkout instructions](../README.md#from-a-local-checkout) to switch its
source. Restart Codex or start a new session after installation. For Claude Code,
start a new session or reload plugins. Installation does not configure credentials.
GitHub installs use published commits; these working-tree changes are local.

## Limitations

Request examples use Basic Auth with the configured token pair. Campaign dispatch, profile export, operator membership
changes, and inbox writes require a verified supported route before execution.
Verify current schemas before execution. API availability remains subject to token scopes and
workspace access. Browser-session capture and native storage were verified locally
with a read request returning 20 conversations. No customer messages were sent.

## Icon

`assets/crisp-icon.png` is the unmodified 512px app logo from Crisp’s official
[Brand Assets archive](https://storage.crisp.chat/public/documents/Brand%20Assets.zip),
linked from the [Crisp website](https://crisp.chat/en/). The original square artwork
includes padding and works on both light and dark surfaces. This plugin is
maintained by JALA; the icon identifies the integrated service.
