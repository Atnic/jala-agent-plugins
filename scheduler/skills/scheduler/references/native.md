# Native desktop scheduling

Use this branch when a same-chat automation tool such as `automation_update` is
available. Detect that tool from the environment before running setup commands.
Native app scheduling needs no CLI hook menu, hook receipt, private runtime,
or custom minute clock. Use the requested cadence directly.

## Preflight

Resolve the exact current chat ID and the client timezone. If Python 3.9+ is
already available, the helper can confirm the selected path without dependencies:

```sh
python3 <helper> preflight --engine codex --session-id <exact-id> --native-automation
```

Pass `--native-automation` only after finding the actual same-chat tool. If Python
is unavailable, use the app tools and their persisted records directly; do not
install a runtime just to access native scheduling. Inspect the tool schema for
accepted recurrence and timezone fields. Use client-local time for wall-clock
schedules; if the host cannot express a requested timezone, explain that limit
before creating the task. The helper's timezone field records intent, not a
conversion of the host schedule.

## Find existing schedules

Check the helper's `list` when available. Also search the host's persisted
automation records for the exact target chat and confirm matching IDs with the
native view tool. For the local desktop tool, use its documented
`$CODEX_HOME/automations/*/automation.toml` location (default `~/.codex`). These
records hold the native ID, destination, prompt, recurrence, and status across
conversations. Read them as data; create/update/delete only through the native
tool. For a host without local record access, use its available schedule listing
or Scheduled interface; explain discovery limits instead of assuming none exist.

Prefer names beginning `Session Scheduler:` to identify schedules created here.
Match both destination and saved prompt/name; do not adopt unrelated automations
silently. If multiple candidates match, ask which one to edit or stop. For legacy
`codex` helper records without `backend: app-native`, cancel the saved definition
first, then delete its old controller heartbeat before replacing it.

## Create or edit

1. Create a **heartbeat in the exact existing chat**, with the confirmed user
   prompt directly, the requested recurrence, and status `ACTIVE`. Use a readable
   name. Preserve the user's notification preference in the tool's notification
   field. Do not put a scheduler tick/controller prefix in the prompt.
2. On edit, view and update the existing native ID with its full current fields;
   retain destination and other settings unless the user changes them. If a tool
   call has an unknown outcome, inspect host records before attempting another
   create. Never create a second timer merely because tracking is missing.
3. Verify the returned ID/status, then view its saved prompt, cadence and target
   chat. The app is the source of truth. If view renders only a card without returning
   fields, read the persisted host record to verify `kind`, `target_thread_id`,
   `prompt`, `rrule`, and `status`. Only claim activation after this check.
4. When the helper is available, mirror the verified result for unified local
   listing. Write the prompt to a private UTF-8 temporary file, then run:

```sh
python3 <helper> native-record --engine codex --session-id <exact-id> \
  --cwd <existing-working-directory> --native-id <verified-id> \
  --name '<verified-name>' --rrule '<verified-rrule>' --timezone <client-zone> \
  --status ACTIVE --prompt-file <private-prompt-file>
```

On edit or adoption of an already tracked ID, add
`--expected-native-id <previously-tracked-id>`. Remove the temporary file afterward.
If tracking fails, retain the native ID in the response and recover from the
app records; do not recreate the task. If destination or prompt verification
fails on a newly created task, delete that new task and report the failure.

Local tracking status is the last observed host state, not proof of a successful
run. List requests should view/reconcile it against the native tool; mirror an
updated status using `native-record` and the expected ID. External deletion can
be reconciled with `native-forget` after the host confirms absence.

## Stop

Find the matching ID, delete it with the native automation tool, and check its
acknowledgement. Only after confirmed deletion/absence, remove local tracking:

```sh
python3 <helper> native-forget --engine codex --session-id <exact-id> --native-id <deleted-id>
```

If deletion fails, keep the tracking record and report that the task is still
active or its state is unknown. The helper's `cancel` command deliberately returns
`requires_native_delete` for this backend and keeps the ID. Stopping does not
create a replacement schedule.

## Availability and acceptance

Native desktop work requires the computer and app to be available. This branch
does not install a login helper or open the app automatically. Same-chat native
delivery was observed here, but powered-off latest-only catch-up and restart
behavior are **not certified**. State that limitation when the user needs it;
never substitute a local hookless runner to imply equivalent guarantees.

For an installed release, check actual capability detection, create, view, edit,
list and delete in the user's host. Use a paused disposable automation for
lifecycle checks. Delivery checks need an explicitly approved short-lived active
schedule, followed by deletion. Separate those observations from injected-clock
unit tests and other hosts' results.
