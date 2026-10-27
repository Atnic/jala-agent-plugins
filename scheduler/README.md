# Session Scheduler

Schedule a prompt to continue the session you are already using. One prompt and
recurring schedule per session; list, edit, or cancel it with the `scheduler`
skill. Missed occurrences coalesce into the latest one, without an age cutoff.
There is no dependency on a particular model provider.

## Setup

Install from the local marketplace while these changes are unpublished:

```sh
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin add scheduler@jala-agent-plugins

claude plugin marketplace add /absolute/path/to/jala-agent-plugins
claude plugin install scheduler@jala-agent-plugins
```

Use the commands for your host. Python 3.11+ must be available as `python3`,
including on Windows. Install the helper's private runtime:

```sh
python3 /absolute/path/to/scheduler/scripts/scheduler.py install-runtime
```

Start or resume the target session with the plugin enabled. Codex also requires
reviewing and trusting the hook definitions in `/hooks`. Ask:

> Schedule this session to summarize the repository every weekday at 8 AM in
> Asia/Jakarta.

The skill confirms the prompt and cadence, saves them, and creates a native
clock in the same session. A live hook receipt is required. If runtime installation
happened during the setup turn, submit setup again after activating the hooks.

## Delivery and catch-up

- **Codex desktop:** a persistent app-native heartbeat wakes the existing chat.
  Its pre-model hook checks the saved cron and timezone. Non-due ticks consume
  no model tokens. The login helper starts the recorded desktop app when work is
  due, and its native clock delivers it. Generic standalone Codex
  CLI sessions are not a live-session backend.
- **Claude:** a native minute clock handles a live session. Hooks hold a
  process-identity lease shared with the cold runner, preventing concurrent
  clients and stale transcript snapshots. Other clients of a scheduled session
  must load the plugin. Exit a rejected competing client and resume the original
  session after its owner finishes; do not bypass the hooks.
- **After login or wake:** one per-user LaunchAgent, `systemd --user` timer, or
  logged-on-only Windows task checks each minute. It starts the recorded desktop
  app for pending Codex work. For Claude it resumes the exact original
  ID with existing authentication, never a fork. The skill installs this timer
  after confirmation. No root/system service is used.

The durable record contains the prompt, session context, cron/timezone, native
timer reference, latest handled occurrence, and minimal delivery status. The
conversation remains the work history. State is private under:

- macOS: `~/Library/Application Support/SessionScheduler`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/session-scheduler`
- Windows: `%LOCALAPPDATA%\SessionScheduler`

`SESSION_SCHEDULER_HOME` selects an alternative private directory for tests or
explicit local configuration. Never share a store between different users.

The first available tick claims only the latest due occurrence after the saved
definition's baseline. The claim is persisted before delivery, so an interrupted
or uncertain attempt is not replayed. Failed work waits for the next occurrence.
Editing resets the timing baseline; cancelling prevents new work while an active
attempt finishes. DST gaps are skipped and repeated local minutes run once.

Claude's native clocks may be session-only and expire after seven days. The
plugin restores them on resume and renews them before expiry. Native task IDs are
captured by a PostToolUse hook, without granting the agent additional shell
permissions. The cold runner uses restrictive unattended permissions; approval-
gated tools fail instead of widening access.

## Inspect or remove

```sh
python3 /path/to/scheduler/scripts/scheduler.py list
python3 /path/to/scheduler/scripts/scheduler.py doctor
python3 /path/to/scheduler/scripts/scheduler.py install --dry-run
python3 /path/to/scheduler/scripts/scheduler.py uninstall
```

Cancellation should use the skill so it also deletes the host-native timer.
Removing the saved definition prevents execution even if native cleanup fails.
Uninstalling the catch-up timer does not cancel native live-session clocks.
Timer reconfiguration pauses future cold starts and waits for an active cold
attempt to finish; repeat the command afterward. Reinstall after updating the
plugin to refresh the private worker copy. Runtime/provider credentials are not
copied into the package or changed by setup.

## Development and verification

```sh
python3 -m venv /tmp/session-scheduler-dev
/tmp/session-scheduler-dev/bin/pip install -r scheduler/requirements-dev.txt
/tmp/session-scheduler-dev/bin/python -m unittest discover -s scheduler/tests
/tmp/session-scheduler-dev/bin/mypy --strict scheduler/scripts
python3 .agents/skills/create-plugin/scripts/validate_plugin.py scheduler
```

See [the integration evidence](../docs/verification/scheduled-continuation.md).
The native delivery mechanisms were exercised on macOS with Codex CLI 0.162.1,
Codex desktop runtime 0.164.0-alpha.11.1, and Claude Code 2.1.258. Unit tests use
an injected clock, isolated stores, and delivery boundaries. Linux and Windows
timer definitions are checked structurally; real login/wake installation on
those systems is not certified by macOS tests. Complete package/host integration
coverage is recorded in that report, rather than inferred from structural checks.
