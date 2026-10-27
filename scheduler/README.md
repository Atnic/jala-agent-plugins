# Session Scheduler

One `scheduler` skill schedules, lists, edits, and stops a prompt in the existing
conversation. It chooses the backend from the tools available in that session.
It does not change model providers or authentication.

## Install and use

```sh
codex plugin marketplace add Atnic/jala-agent-plugins
codex plugin add scheduler@jala-agent-plugins

claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install scheduler@jala-agent-plugins
```

Use the commands for your host. For unpublished local changes, pass this
repository's absolute path to `plugin marketplace add` instead of its GitHub name.
After updating, start or resume a session that loads the new skill version.

Invoke `scheduler`, then ask:

> Say hello in this chat every five minutes.

A clear request supplies confirmation. The skill asks only for missing choices
or material changes, then verifies the saved destination, prompt and cadence.
No separate setup skill is needed. Ask `scheduler list`, `scheduler edit`, or
`scheduler stop` to manage it later.

## Backends and prerequisites

| Backend | Requirements | Timing and limits |
| --- | --- | --- |
| ChatGPT/Codex desktop native | Same-chat automation tool; existing app records | Uses the requested cadence directly. No hook receipt, private runtime, or login helper. Computer/app availability governs execution. Powered-off latest-only catch-up is not certified. |
| Claude guarded continuation | Native Claude executable, CronCreate, Python 3.11+ private runtime, live plugin hooks | Native clock serializes live turns. Per-user login runner resumes inactive sessions and coalesces missed occurrences into the latest one, without an age cutoff. |
| Host without either capability | Unsupported | Explains the missing capability before installing anything. |

Native schedules store their IDs and settings in the app's own durable records.
The helper can mirror verified native metadata for unified local listing using
existing Python 3.9+ and its standard library; it needs no dependency installation.
If Python is unavailable, the skill still uses host tools and persisted native
records. The app remains authoritative for edits, status, and deletion.

Claude alone needs the private runtime and startup helper; the skill follows
[Claude setup](skills/scheduler/references/setup.md) for that branch. The desktop
branch follows [native scheduling](skills/scheduler/references/native.md).
Neither path substitutes an unguarded standalone Codex CLI resume.

## Tracking, migration and cancellation

Native metadata records the backend, exact target chat, native ID, prompt,
recurrence/timezone intent, and last observed host status. A successful delivery
is visible in the conversation; tracking status alone does not prove a run.
The skill reconciles records with the native view tool before listing or editing.
If a native API call has an unknown outcome, inspect existing records before
creating another task. If deletion fails, keep its ID for a later stop request.

The helper's store is private under:

- macOS: `~/Library/Application Support/SessionScheduler`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/session-scheduler`
- Windows: `%LOCALAPPDATA%\SessionScheduler`

`SESSION_SCHEDULER_HOME` selects an isolated store for tests. Native app records
remain in the app's own automation store. The helper supports:

```sh
python3 /path/to/scheduler/scripts/scheduler.py list
python3 /path/to/scheduler/scripts/scheduler.py doctor
```

For native schedules, `cancel` returns `requires_native_delete` and retains the
record. The skill deletes through the app first, then calls `native-forget` after
confirmed deletion/absence. Removing tracking alone cannot stop an app schedule.

Existing v0.1.0 Codex hook-backed records remain readable. Cancel the local
legacy definition and delete its old controller heartbeat before replacing it
with one direct native schedule. New desktop setup does not activate those hooks.
Existing Claude schedules keep their occurrence claims and lease protocol.

For Claude, failed/interrupted occurrences are not automatically retried; later
occurrences remain eligible. Its native clocks may be session-only and expire
in seven days; lifecycle hooks restore/renew them. The cold runner uses existing
authentication with restrictive unattended permissions. Its login timer is
user-level on macOS, Linux, and Windows. Actual Linux/Windows login/wake remains
unverified even though definitions and unit behavior run in CI.

## Checks and evidence

```sh
python3 -m pip install -r scheduler/requirements-dev.txt
python3 scheduler/scripts/check.py
```

This is also the CI entry point on Linux, macOS and Windows with Python 3.11 and
3.13. It runs the package tests, strict mypy, structural package validation,
skill YAML validation, and a check against CLI-only setup instructions in the
native desktop branch. These checks do not certify host UI compatibility.

See [integration evidence](../docs/verification/scheduled-continuation.md) for
which installed-package and real-host flows were exercised. Claims about one
host or isolated hook fixture do not certify another host's setup path.

## Artwork

The clock-in-a-chat-bubble mark in `assets/scheduler-icon.svg` is original vector
artwork created for Session Scheduler. Its padded violet tile uses the same
asset on light and dark backgrounds. The 512 px PNG is exported from that SVG
for the composer icon. Light/dark previews were inspected at 24, 32, 64, 128
and 256 px; this verifies the assets, not the live host rendering.
