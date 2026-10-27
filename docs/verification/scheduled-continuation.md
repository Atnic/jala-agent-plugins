# Scheduled continuation: integration verification

Issue: [#9](https://github.com/Atnic/jala-agent-plugins/issues/9)

Verified on 26 October 2026, Asia/Jakarta, on macOS with Codex CLI 0.162.1
and Claude Code 2.1.258. This is the verification-first deliverable, not a
scheduler implementation or a claim of cross-platform support.

## Outcome

Both installed tools successfully resumed a saved session and recalled a marker
from its previous turn, preserving the original session ID. Codex's desktop
thread reader also retrieved both completed turns under that ID.

The first probe found that plain Claude `--resume` allowed a second process to
complete a turn under the same session ID while the original process continued streaming.
That path does not meet the requirement to wait for an idle session without
concurrent scheduled/manual turns. A different coordination mechanism was
initially unverified. Implementation paused at that gate. The follow-up
below verifies alternative native delivery paths for Codex desktop and
participating Claude clients; plain resume remains unsuitable for a live session.

## Test conditions

- Used disposable working directories and test sessions, not the user's chats.
- Used existing default authentication; no provider configuration was changed.
- Codex reported an existing login. Claude reported first-party OAuth login.
- Disabled MCP integrations for the probes. Prompts requested only text; Claude
  tools were disabled, and the Codex seed used a read-only sandbox.
- Saved raw outputs outside the repository. No credentials or transcripts from
  unrelated sessions are included in this report.
- The earlier 9router profile's HTTP 401 does not establish a failure of the
  default-provider path: the default Codex integration succeeded in this run.

## Successful resumption

| Agent | Seed | Resume | Evidence |
| --- | --- | --- | --- |
| Codex | Exit 0 | Exit 0 | Same ID `01a178ff-49fb-7912-a4e4-1b65f70f882a`; resumed answer recalled `SCHEDULER_SEED_CODEX_9`; desktop reader returned both turns. |
| Claude | Exit 0 | Exit 0 | Same ID `72fb934a-9982-45f2-95e1-db9a81939879`; resumed answer recalled `SCHEDULER_SEED_CLAUDE_9`. |

For Codex, the tested command was `codex exec resume <id> <prompt> --json`
with the disposable project as the working directory. For Claude it was
`claude -p <prompt> --resume <id> --output-format json`.

These tests establish idle-session history continuation, not safe dispatch
against an independently active interactive client. Codex desktop visibility
was checked through the app's thread reader, not by a visual UI inspection.

## Reproduced Claude concurrency failure

Test session: `e0ccd8a3-b7f0-4774-a44d-3efb2dd1e5f4`.

1. Started a disposable Claude session with an explicit session ID, requesting
   integers 1 through 3000, one per line. Enabled stream JSON and partial
   messages; disabled tools and MCP integrations.
2. Waited for the first `content_block_delta`, establishing that the first
   process was generating its answer.
3. Queried `claude agents --json`. It listed the target with `pid`, `cwd`,
   `kind`, `startedAt`, `sessionId`, and `name`; that entry had no turn-level
   busy/idle field.
4. Started `claude -p "Reply exactly SCHEDULER_FRESH_RACE_SECOND_9. Do not use tools."
   --resume <same-id> --output-format json`, with tools and MCP disabled.
5. The second process exited 0 and returned the expected marker and the exact
   original session ID. The first process was still alive and emitted further
   content deltas after the second process completed.
6. Terminated the remaining test process at the probe's time limit. This
   termination affected only the disposable test session.

Observed timestamps, Unix seconds:

| Event | Timestamp |
| --- | --- |
| First process's first content delta | 1793031620.171220 |
| Second dispatch began | 1793031620.171296 |
| Second process completed | 1793031623.625292 |

Reproduce with the following command shapes in a disposable directory. Use a
fresh UUID for `<id>` and launch the second command only after the first emits
content. The first request generates a long answer and consumes model usage.

```sh
claude -p "Write all integers from 1 to 3000, each on its own line. This is the complete requested answer; do not summarize or use tools." \
  --session-id <id> --output-format stream-json --verbose \
  --include-partial-messages --tools '' --strict-mcp-config \
  --mcp-config '{"mcpServers":{}}'

claude agents --json

claude -p "Reply exactly SCHEDULER_FRESH_RACE_SECOND_9. Do not use tools." \
  --resume <id> --output-format json --tools '' --strict-mcp-config \
  --mcp-config '{"mcpServers":{}}'
```

The commands must run in separate processes; compare session IDs and observe
the first process continuing to stream after the second completes. A matching
ID alone is not proof of safe coordination.

## Gate after the initial probe

These were the outstanding checks before the follow-up below. Its adapter
implications and remaining-work section now describe the current findings.

- Verify a supported mechanism that coordinates dispatch with active Claude
  clients. A scan followed by `--resume`, or a scheduler-owned lock, does not
  establish atomic coordination with those clients. This result does not prove
  that every possible Claude integration is incapable of meeting the contract.
- Verify active-client coordination for Codex, including the shared app-server
  alternative demonstrated by the existing Office bridge. Idle CLI resumption
  and desktop readability do not establish this behavior.
- Use the follow-up's verified configurations when designing adapters. Other
  configurations still need integration checks; do not silently fall back to
  unsafe resumption, interrupt work, or drop an agent.
- No scheduler, OS timer, fake-clock/backend suite, or Windows/Linux integration
  was implemented or verified during this gate. No provider-specific sandbox
  write behavior was tested.

References: [Codex app-server lifecycle](https://learn.chatgpt.com/docs/app-server#lifecycle-overview),
[Claude noninteractive continuation](https://code.claude.com/docs/en/headless#continue-conversations).

## Follow-up: verified native delivery paths

Tested on 26–27 October 2026, Asia/Jakarta, on the same machine. Codex's desktop runtime reported
`0.164.0-alpha.11.1`; the installed standalone CLI remained `0.162.1`.
Claude remained `2.1.258`. These findings resolve the live-delivery question
for the tested configurations, not all of the scheduler's acceptance criteria.
They introduce no dependency on the 9router plugin.

### Codex desktop: native thread heartbeat

The app-native message API continued the original disposable thread successfully.
However, sending another message during an active response appended work to
that same turn. It is not an idle-only delivery primitive.

A temporary native **heartbeat**, targeting that existing thread, behaved
differently:

1. Created a heartbeat with a one-minute recurrence and a harmless marker prompt.
2. Started a manual turn requesting all integers from 1 through 3000.
3. The heartbeat became due while the manual turn was active. The manual turn
   completed its full list, without a scheduled prompt being added to that turn.
4. The heartbeat subsequently ran as a separate completed turn in the same
   thread and returned the expected marker.
5. Deleted the temporary automation after observing the result.

| Event | Turn ID | Unix seconds |
| --- | --- | --- |
| Manual turn started | `01a1791c-476a-7ec0-8936-f2da29ce3331` | 1793033258 |
| Manual turn completed | Same | 1793033342 |
| Heartbeat turn started | `01a1791e-72fd-7490-be06-4450c5efd7d8` | 1793033401 |
| Heartbeat turn completed | Same | 1793033411 |

Both turns belong to `01a178ff-49fb-7912-a4e4-1b65f70f882a`.
This verifies same-thread delivery on a subsequent idle tick, without interrupting
the manual response. It does not distinguish retaining a missed occurrence from
skipping busy ticks and running the next regular occurrence. Retention and
coalescing, an immediate idle callback, laptop-off catch-up, and arbitrary Codex
CLI coordination remain unverified by this test.

A second test removed the recurrence ambiguity. It used a one-time heartbeat
(`FREQ=DAILY;BYHOUR=23;BYMINUTE=58;BYSECOND=0;COUNT=1`) due at
1793033880, while a manual turn ran `/bin/sleep 110` and waited for completion:

| Event | Turn ID | Unix seconds |
| --- | --- | --- |
| Manual turn started | `01a17925-8a20-7142-b086-8b7e3089423a` | 1793033865 |
| Sole heartbeat occurrence due | — | 1793033880 |
| Manual turn completed | Same manual turn | 1793033987 |
| Heartbeat turn started | `01a17927-9af8-76c1-89c5-f730bcf01893` | 1793034001 |
| Heartbeat turn completed | Same heartbeat turn | 1793034017 |

The manual turn returned its completion marker first. The heartbeat then
returned its own marker under the same thread ID. Because the recurrence had
only one occurrence, this verifies retention of a due occurrence across a busy
turn, not execution at a later recurrence. The automation was deleted afterward.
Multiple-occurrence coalescing and laptop-off catch-up remain separate checks.

To repeat, use the app's `automation_update` capability with `kind: heartbeat`
and the disposable thread's `targetThreadId`, then observe turns through
`wait_threads` and `read_thread`. Use the native scheduling API, not repeated
calls to the ordinary message API. Delete the automation afterward.

### Claude: native cron plus a session lease

A disposable probe combined two mechanisms:

- `CronCreate` delivered scheduled prompts inside the running session's own
  event loop, preserving both its identity and its live conversation context.
- All participating clients loaded a `UserPromptSubmit` hook that atomically
  claimed a SQLite lease for the session, held until `SessionEnd`. A different
  live owner caused the hook to block the competing prompt. The owner's native
  scheduled turns reused its lease. A rejected client's `SessionEnd` could not
  release the other client's lease.

The first test used session `c00853f3-bd22-4db8-9b49-b61acd7428f1`.
The original process owned the lease with PID 40863. A second resume process,
PID 40889, was blocked by the hook before generating the requested marker.
The original native timer then answered its scheduled arithmetic prompt in
that same session. The task was cancelled and the session's task list was empty.

**Do not use exit status alone as an acknowledgement:** the blocked resume
returned exit 0 and `is_error: false`, with a result explicitly saying
`UserPromptSubmit operation blocked by hook`. A production adapter needs an
explicit busy/delivery acknowledgement.

A separate one-time timer verified busy-session behavior in session
`4ebf007c-1419-4eb6-b12f-d8d5f4424b72`:

| Event | Unix seconds |
| --- | --- |
| Manual prompt accepted by its hook | 1793033277.076308 |
| Scheduled prompt due | 1793033280 |
| Manual response completed | 1793033314.531775 |
| Scheduled response completed | 1793033317.348298 |

The manual response contained the entire requested sequence from 1 through 2000.
The scheduled response followed it and answered `Four.`. Both result records
retained the original session ID. The due time occurred during the manual turn,
including its initial model-processing time, rather than while the session was
idle. The one-time task removed itself after firing.

To repeat, run a persistent `claude -p --input-format stream-json
--output-format stream-json --verbose` process with disposable per-invocation
hook settings. Keep its stdin open, create the native timer, and send a long
manual prompt before its due time. Run the competing resume with the same hook
settings and session ID. Check hook acknowledgements, the complete manual
response, and the subsequent scheduled response; cancel test tasks afterward.

### Adapter implications and remaining work

For a live session, prefer the host's native scheduler rather than a new
resume process. For an inactive Claude session, an external catch-up runner
would need to obtain the same lease before resuming it. Every manual and
scheduled client that can open that session must participate in this protocol;
these tests do not protect against a client that bypasses the hooks.

The lease was a disposable probe, not production locking code. Packaging,
hook activation/trust, owner identity and stale-lease recovery, atomic dispatch
acknowledgements, and other platforms still need implementation and tests.
The Codex result applies to app-native heartbeats, including the observed
one-time retention across a busy turn, not a standalone CLI adapter.

Native scheduling alone does not establish the required catch-up after a laptop
has been off. Retain the approved latest-only, no-age-cutoff requirement and
verify it separately before claiming the complete feature works. The plugin and
its persisted occurrence state have not been implemented in this investigation.

All temporary Codex automations were deleted. Claude recurring test tasks were
cancelled and their lists checked; one-time test tasks were cancelled or fired
and removed themselves. Test processes were terminated after verification.
No global provider or hook configuration was modified.

References: [Claude scheduling behavior and limitations](https://code.claude.com/docs/en/scheduled-tasks),
[Claude hook contracts](https://code.claude.com/docs/en/hooks).


## Package implementation checks — 2026-10-27

The `scheduler/` package now implements durable latest-only occurrence state,
native-clock hooks, the skill setup flow, and a per-user startup helper. The
investigation-only limitations above describe the earlier probes, not the
current code. These checks used disposable stores and the existing local agent
authentication; provider configuration was not changed.

### Codex helper and native delivery boundary

The packaged helper was exercised through Codex CLI 0.162.1 lifecycle hooks in
session `01a17adf-6510-7931-935b-95767c9141c8`. A seed turn was followed by an exact-ID
resume carrying the native heartbeat envelope and a due saved definition. The
helper supplied the confirmed task, the response was `PACKAGE_CODEX_FOUR`, and
Stop recorded completion. A repeated tick returned a completed turn with all
usage counters zero. Both resumes retained the seed session ID.

This fixture loaded only its own reviewed inline hook commands, with
`--ignore-user-config` and the invocation-only hook-trust override. These flags
are test isolation, never plugin setup instructions. It verifies the packaged
helper against a real host; the earlier app-native heartbeat probes verify busy
serialization. A complete installed desktop-plugin trust/setup smoke test is
still separate from those checks. Standalone CLI delivery remains unsupported.

### Claude cold continuation

The actual package was loaded with `--plugin-dir` for seed session
`0f79e0b8-812c-4657-827c-6169cb81e908` using Claude Code 2.1.258. After that client
exited, the public scheduler API saved an hourly definition with its baseline
two hours in the past. The runner resumed the exact original ID. Its answer was
`2+2 = 4. COLD_SEED marker recalled: confirmed.` The worker checked a matching
child PID, dispatch token, terminal hook acknowledgement, session ID, and CLI
result before recording completion. A second tick delivered nothing. The saved
definition was removed afterward.

A separate subprocess regression test returns successful CLI JSON without any
hook acknowledgement. That result records failure, consumes its occurrence,
and is not retried. Terminal Stop alone also cannot override a later CLI
permission failure. A completed delivery means the agent received and finished
its turn; the conversation contains its task outcome, including any refusal.

### Claude live native clock and setup

A clean private runtime was installed through `install-runtime`. In persistent
session `9194bcdc-b9ae-434f-acb0-cdc08cbb2267`, the actual `scheduler:scheduler`
skill was loaded through the host Skill tool. The agent checked its live receipt,
saved a confirmed minutely UTC arithmetic prompt using the CLI, and created its
native clock. PostToolUse supplied the actual response shape
`{"id":"110dc94e","humanSchedule":"Every minute","recurring":true,"durable":false}`;
the plugin bound it automatically and reported `ready`.

The native timer then submitted the controller directly, without an extra
wrapper in UserPromptSubmit. The hook supplied the task, the answer was
`2+2 = 4. PACKAGE_FOUR`, the session ID was unchanged, and status became
`completed`. The native task and saved definition were removed afterward. The
login helper was intentionally omitted from that setup fixture because its
actual installation was exercised separately below.

Early fixture attempts supplied controller strings without the genuine skill
setup flow, or used a symlinked development runtime. The model refused those
setups. The successful check used host skill substitution, the helper's own
context/set output, and a real private runtime. Claude's skill session-ID
substitution is not a guaranteed shell environment variable.

### Claude idle restoration after resume

A second genuine skill setup in session `0f1d0e6c-bffb-4a14-b0bf-36f5a53c7115`
created native task `233aad2c` and delivered `PACKAGE_FOUR`. The client then exited
without cancelling its saved definition. A new process resumed that same ID with
the same plugin and tool set, with stdin kept open but no manual prompt. The
SessionStart asynchronous lifecycle check woke it; Stop requested clock repair.
CronCreate produced `76fd391c`, and PostToolUse bound it to the new owner's PID
and birth time. The fixture observed that binding before cancelling its saved
record and terminating the session-only clock. This verifies restoration after
native clock loss without inventing a replacement conversation.

An earlier restoration fixture recreated an already-cancelled definition and
changed the available tools; the model refused it. That was not a valid resume
of an existing confirmed schedule. The successful check retained the actual
confirmed record and conversation context across process exit.

### Startup installation

On macOS, a disposable state directory was installed using the actual
LaunchAgent adapter. `launchctl print` showed one run and `last exit code = 0`.
The worker used the copied private package, and the LaunchAgent was then removed.
No test timer or automation was left installed. Linux user-unit and Windows
interactive-token task definitions are parsed in tests; actual login/wake on
those systems has not been exercised.

The timer re-registers on every explicit install, allowing recovery after an
installation failure leaves its files behind. Reconfiguration first disables
new cold reservations and refuses to stop an active cold attempt. Dead desktop
claims are marked interrupted without rolling back their handled occurrence;
subsequent due work can start the app again.

### Reproducible local checks

Install `scheduler/requirements-dev.txt` in an isolated Python 3.11+ environment.
Run individual files during development, then the complete package suite:

```sh
python -m unittest discover -s scheduler/tests
mypy --strict scheduler/scripts
python3 .agents/skills/create-plugin/scripts/validate_plugin.py scheduler
claude plugin validate scheduler
```

The suite exercises injected clocks and real isolated SQLite stores at the public
scheduling/delivery boundaries: long-off catch-up, concurrent claims, live leases,
explicit busy deferral, failure/no-retry, edits/cancellation, stale native keys,
DST transitions, dead-claim recovery, hook acknowledgement, and OS definitions.
Skill YAML is checked separately with the skill-creator validator.


Final package suite: **24 tests passed**. Strict mypy, repository structural
validation, Claude manifest validation, skill YAML validation, and whitespace
checks passed. No generated bytecode is included in the package.

## Standards

The review found generated Python bytecode in the working tree; package ignore
rules now exclude it. No documented-standard violations remain. The review's
optional suggestion to replace generic document dictionaries with TypedDicts is
deferred as a maintainability improvement, not a release requirement.

## Spec

The review found two correctness problems: stale Codex claims could prevent app
startup, and cold Claude results lacked a correlated hook acknowledgement. Both
were fixed and received regression tests. Follow-up review reported no additional
concrete findings. Real Linux/Windows login and installed Codex desktop hook-trust
setup remain manual validation coverage, as distinguished from the tested native
mechanisms and packaged helper above.


## Desktop setup correction — v0.1.1, 2026-10-27

The first installed v0.1.0 desktop setup failed: its skill required `/hooks`,
which was unavailable in this ChatGPT interface, and no live helper hook receipt
was produced. Earlier CLI hook fixtures did not verify that installed entry flow.
A direct app-native hello heartbeat subsequently delivered twice in this same
chat (01:28 and 01:33 UTC) and was deleted on the user's stop request. That proved
native same-chat delivery, not a working v0.1.0 plugin setup.

The user approved the retrospective fixes: capability-first native setup,
durable schedule identification across later conversations, installed-package
lifecycle coverage, and wired automated checks. v0.1.1 uses direct native
heartbeats when that tool exists, and keeps the guarded runtime for Claude.
Native setup neither installs a private runtime nor requires hook activation.
The app's own automation records remain authoritative; an optional standard-
library helper mirror supports unified local listing and explicit backend IDs.
Deletion is acknowledged by the host before tracking is forgotten. Failed or
stale edits retain the existing record; legacy operations cannot erase it.

### Installed candidate lifecycle test

The real `codex plugin marketplace add` and `codex plugin add` commands installed
the unpublished v0.1.1 candidate from the local repository into an isolated
`CODEX_HOME`. The installed helper ran with the system Python 3.9 and `-S`, a fresh
state directory and no private runtime. Preflight selected `app-native` with no
hook/runtime requirements. Dependency-free subprocess tests also cover missing
tools, unavailable Claude prerequisites and an unusable optional runtime.

A paused disposable native heartbeat, `session-scheduler-installation-test`,
was created in the actual current chat. Its persisted host record verified
`kind=heartbeat`, the exact `target_thread_id`, direct prompt, five-minute
recurrence, and `PAUSED` status. The native view tool rendered a card without
returning those fields, so verification read the host's automation record as data.
The installed helper recorded its ID and a later fresh process listed it.

The native update tool changed its prompt/name and cadence to seven minutes,
retaining that same ID, chat and paused status. The installed helper mirrored
the verified edit using its expected-ID guard. Its cancel command retained the
record and returned `requires_native_delete`; after the native delete tool
acknowledged deletion, `native-forget` removed the mirror. A fresh list was empty
and the native record was absent. The disposable test was never activated, and
the user's previously stopped hello task was not recreated.

### Coverage boundaries and checks

This exercise verifies installed artifact packaging and the actual native
create/view/list/edit/delete path. Native delivery itself was observed in the
user's two hello runs above; the candidate lifecycle fixture was paused.
Powered-off latest-only catch-up, native restart/failure semantics, and actual
Linux/Windows desktop clients remain unverified. The skill reports those limits
instead of borrowing guarantees from the Claude occurrence store. Official
[scheduled-task documentation](https://learn.chatgpt.com/docs/automations) says
local desktop work requires the machine and app to be available.

The local/CI entry point is `python scheduler/scripts/check.py`. The workflow
runs existing scheduling/hook/platform tests, new dependency-free CLI regressions,
strict mypy, skill YAML validation, native setup instruction checks and the repo
package validator on Linux/macOS/Windows with Python 3.11/3.13. CI verifies these
commands and definitions; it does not certify actual agent UI or wake behavior.

Final v0.1.1 local check: all 30 tests passed, strict mypy passed for four
script modules, skill YAML and native setup instruction checks passed, and
repository package validation plus Claude manifest validation passed. Both
required review axes reported no new findings. The pre-existing optional typed
record suggestion is unchanged. The stopped hello task remains stopped.

The first hosted matrix run passed scheduling tests and mypy on all six jobs,
but exposed a Windows locale bug in the shared packaging validator: its default
text encoding could not read the repository's UTF-8 README. The validator now
reads UTF-8 explicitly and reports invalid UTF-8 as a validation error. Two
regressions cover this through its public API and a CLI with missing-encoding
warnings promoted to errors. The existing 16-test validator suite is now also
wired into the shared CI entry point. Python bytecode is ignored repository-wide.
