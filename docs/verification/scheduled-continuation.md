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
