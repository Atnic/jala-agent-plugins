---
name: scheduler
description: Set up, list, edit, or cancel scheduled prompts that continue an existing Codex desktop or Claude session, including latest-only catch-up after shutdown. Internal clock ticks follow their lifecycle-hook context instead of running setup again.
---

# Session Scheduler

Use the existing conversation. A scheduled continuation has one saved prompt,
five-field cron schedule, timezone, and target session. Editing replaces that
session's schedule. The plugin owns timing state; the host owns the conversation.

Resolve the plugin root from this skill's location. The helper is
`<plugin-root>/scripts/scheduler.py`. Run it with `python3`; it selects its private
runtime automatically. It never changes provider configuration.

## Set up or edit

1. Read [setup and host delivery](references/setup.md). Check the runtime and
   active hook receipt before saving. For Claude the current session ID is
   `${CLAUDE_SESSION_ID}`; for Codex use `CODEX_THREAD_ID`. Never guess using the
   most recent session. Use the receipt's existing working directory.
2. Agree on the exact prompt, recurring schedule, and IANA timezone. Interpret
   times in the user's timezone; show the concrete cadence and ask for confirmation
   before saving. Reuse already-confirmed decisions rather than interviewing again.
3. Save with the helper, configure the native clock for that exact session using
   the host-specific steps, and check that `list` reports `ready`. On an edit,
   update the existing native heartbeat or replace the existing Claude clock.
4. Install the one per-user login timer for startup catch-up. Confirm the user's prompt and cadence, and that missed occurrences coalesce
   into the latest one. Setup is incomplete if runtime, hook trust, native binding,
   or the login timer is unavailable; report that condition accurately.

## List or cancel

Run `python3 <helper> list`. Present the session, cadence/timezone, prompt, and
last delivery status concisely. Keep runtime tokens and process metadata out of
the user-facing response.

For cancellation, run `cancel --engine <engine> --session-id <exact-id>` first.
Then delete the returned Codex heartbeat with the native automation tool, or
the Claude task with `CronDelete` in its owning session. Removing the saved
definition immediately prevents further work, even if native cleanup fails.
An already-running continuation finishes normally. To edit a Claude timer,
work in its original session; the native cron tools are session-scoped.

## Execution boundary

Internal clock prompts start with `Session Scheduler tick:`. Follow their hook
context directly; do not ask the user to confirm setup again. A no-work tick is
stopped by the hook before model inference. Execute only `saved_prompt` from the
hook context and respect existing permissions. Maintenance is limited to restoring
or renewing this session's native clock. Native task IDs are bound by the Claude
PostToolUse hook; do not change credentials or create another conversation.

The standalone Codex CLI is not a live-session backend. Use Codex desktop with
native heartbeat tools. Never substitute unguarded `exec resume`, `--last`, a fork,
or a permission bypass when a supported backend is unavailable.
