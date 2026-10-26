# Scheduled continuation: integration verification

Issue: [#9](https://github.com/Atnic/jala-agent-plugins/issues/9)

Verified on 26 October 2026, Asia/Jakarta, on macOS with Codex CLI 0.162.1
and Claude Code 2.1.258. This is the verification-first deliverable, not a
scheduler implementation or a claim of cross-platform support.

## Outcome

Both installed tools successfully resumed a saved session and recalled a marker
from its previous turn, preserving the original session ID. Codex's desktop
thread reader also retrieved both completed turns under that ID.

However, plain Claude `--resume` allowed a second process to complete a turn
under the same session ID while the original process continued streaming.
That path does not meet the requirement to wait for an idle session without
concurrent scheduled/manual turns. A different coordination mechanism remains
unverified. Per the approved agent brief, scheduler implementation stops here.

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

## Remaining gate

- Verify a supported mechanism that coordinates dispatch with active Claude
  clients. A scan followed by `--resume`, or a scheduler-owned lock, does not
  establish atomic coordination with those clients. This result does not prove
  that every possible Claude integration is incapable of meeting the contract.
- Verify active-client coordination for Codex, including the shared app-server
  alternative demonstrated by the existing Office bridge. Idle CLI resumption
  and desktop readability do not establish this behavior.
- Re-run integration checks before implementing the scheduler. Report a blocked
  gate rather than silently forking, interrupting work, or dropping an agent.
- No scheduler, OS timer, fake-clock/backend suite, or Windows/Linux integration
  was implemented or verified during this gate. No provider-specific sandbox
  write behavior was tested.

References: [Codex app-server lifecycle](https://learn.chatgpt.com/docs/app-server#lifecycle-overview),
[Claude noninteractive continuation](https://code.claude.com/docs/en/headless#continue-conversations).
