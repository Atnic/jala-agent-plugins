# Setup and host delivery

## Prerequisites

The installed plugin's hooks must run in the target session. Install Python 3.11+
as `python3` on PATH, then run:

```sh
python3 <plugin-root>/scripts/scheduler.py install-runtime
```

Start or resume the target session after installation. In Codex, review and trust
the plugin hooks with `/hooks`; installing the plugin alone does not trust them.
If the runtime was installed during the current turn, submit setup again so the
next prompt can produce a live hook receipt. This check prevents an unguarded
session from being scheduled.

```sh
python3 <helper> context --engine codex --session-id <CODEX_THREAD_ID>
python3 <helper> context --engine claude --session-id <CLAUDE_SESSION_ID>
```

Claude substitutes `${CLAUDE_SESSION_ID}` when loading this skill; it is not
guaranteed to exist as a shell environment variable. Pass the substituted exact
ID explicitly. Use only the command for the current host. A missing or stale receipt requires
activation/resumption, not permission bypasses. Existing schedules can be
inspected with `list` and diagnosed with `doctor`.

## Save the confirmed definition

Write the exact confirmed prompt to a private UTF-8 temporary file using a file
tool, not shell interpolation. Then invoke:

```sh
python3 <helper> set --engine <codex-or-claude> --session-id <exact-id> \
  --cwd <receipt-working-directory> --cron '0 8 * * *' \
  --timezone Asia/Jakarta --prompt-file <private-prompt-file>
```

Read the returned `schedule`, `controller_prompt`, and `previous_native_id`.
Delete the temporary prompt file afterward. The definition remains
`setup_required` until a native timer is bound. Each session has one definition;
edits reset its timing baseline to the confirmed edit time, so changing a cadence
does not replay times under the previous definition. An active continuation must
finish before editing.

The native clock runs every minute, but its hook stops no-work ticks before model
inference. The saved cron and timezone are evaluated locally. There is no age
cutoff: the first available tick executes only the latest occurrence after the
definition's baseline. Repeated daylight-saving minutes run once; nonexistent
local minutes are skipped.

## Codex desktop

Use the app's native automation capability, discovered by name
`automation_update`. Create a **heartbeat** targeting the exact existing session,
with the returned `controller_prompt`, status `ACTIVE`, and a one-minute
recurrence. On edits update `previous_native_id` with the full heartbeat fields;
do not create duplicates. Respect any notification preference already chosen by
the user. This is an existing-chat heartbeat, not a standalone cron chat.

Bind the returned automation ID and install the login/startup helper:

```sh
python3 <helper> bind --engine codex --session-id <exact-id> \
  --key <schedule-key> --native-id <automation-id>
python3 <helper> install
```

If the app-native scheduling tools are absent, stop setup and explain that this
host is unsupported. The login helper starts the recorded desktop app when
Codex work is due and the app is not running; it does not submit prompts or use
CLI resume. The persistent native heartbeat and local occurrence state then
perform catch-up without replaying a backlog. Tell the user before confirmation
that due work can start the desktop app. No provider profile is installed.

## Claude

Use `CronCreate` in the exact target session with cron `* * * * *`,
`recurring: true`, and the returned `controller_prompt`. The plugin's PostToolUse
hook binds the native ID automatically. Verify `list` reports the same task ID
and `ready`; if not, stop rather than claiming activation. On an edit, delete
`previous_native_id` after the replacement has bound successfully.

Install the one per-user catch-up timer:

```sh
python3 <helper> install
```

This uses a LaunchAgent on macOS, `systemd --user` on Linux, or an interactive-token
Task Scheduler task on Windows. It starts at login and checks inactive Claude
sessions each minute. It does not install a root/system service. User scheduling
confirmation authorizes this timer; report installation errors rather than
silently omitting startup catch-up. `install --dry-run` shows the plan without
changing services; `uninstall` removes it when no background attempt is active.

The native clock handles a live session. All clients opening a scheduled session
must load the plugin hooks. A competing or stale client is blocked; exit that
client and resume the same session again after the owner finishes. A new process
loads the updated transcript. Do not bypass the hooks or fork the conversation.

Claude clocks may be session-only and expire after seven days. Lifecycle hooks
restore clocks when a session resumes, and maintenance renews a live clock before
expiry. The PostToolUse hook records new IDs without granting Bash permissions.
The cold runner resumes the original ID with existing authentication and a
non-interactive restrictive permission mode. Tools requiring additional approval
fail rather than broadening permissions. Failures and interruptions consume their
occurrence; the next scheduled occurrence remains eligible.
