---
name: scheduler
description: Schedule, list, edit, or stop prompts in the current ChatGPT/Codex desktop or Claude session. Detect native scheduling before installing anything; Claude uses guarded continuation hooks and latest-only catch-up.
---

# Session Scheduler

Keep one editable scheduled prompt per existing conversation. Identify the exact
session and the tools actually available; choose the backend by capability, not
by the app's name.

## Choose the backend first

- **Same-chat automation tool available:** read [native desktop scheduling](references/native.md).
  Use the app's native heartbeat at the requested cadence. This path needs no
  hook receipt, private runtime, or login helper installation.
- **Claude CronCreate available:** read [Claude setup](references/setup.md).
  Its guarded runner needs a working runtime and live hook receipt.
- **Neither available:** explain which capability is missing before installing
  anything. An unguarded CLI resume is not a scheduling backend.

For local helper commands, resolve `<helper>` as
`<plugin-root>/scripts/scheduler.py`. Native tracking works with existing Python
3.9+ and the standard library; the Claude runner needs Python 3.11+ and its private
runtime. Native app records remain authoritative when the helper is unavailable.

## Confirm and operate

Use the current session ID (`CODEX_THREAD_ID` for local Codex, the host-substituted
`${CLAUDE_SESSION_ID}` for Claude); never guess from recency. Resolve missing IDs
from trusted host context or ask the user. Agree the prompt, cadence and client
IANA timezone. A direct, unambiguous scheduling request is confirmation; ask only
for missing choices or a material change to an existing schedule.

Create or edit with the selected backend, verify the host's acknowledgement and
record the native ID. Report the backend and actual limitations. Native scheduling
inherits host availability; powered-off catch-up is not certified by a successful
creation. Claude's guarded runner coalesces missed occurrences into the latest one.

For list, edit, or stop, follow the same backend reference. Recover native IDs
from tracking and host records, rather than relying on this chat's memory. Keep
tracking until the host confirms deletion. A local record alone cannot stop an
app-native schedule.

## Scheduled execution

App-native heartbeats contain the confirmed user task directly; follow it and
the host's heartbeat response format. They do not need a helper or hook callback.
Claude controller prompts start with `Session Scheduler tick:`. Follow their
hook context without running setup again. Execute only the supplied `saved_prompt`;
a no-work tick is stopped before inference. Keep existing authentication and
permissions, and continue the same conversation.
