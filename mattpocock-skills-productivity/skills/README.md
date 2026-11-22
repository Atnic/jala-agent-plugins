# Productivity

General workflow tools, not code-specific.

## User-invoked

Reachable only when you type them (Claude Code: `disable-model-invocation: true`; Codex: `policy.allow_implicit_invocation: false` in `agents/openai.yaml`).

- **[grill-me](./grill-me/SKILL.md)**: Get relentlessly interviewed about a plan or design until every branch of the design tree is resolved.
- **[grill-with-docs](./grill-with-docs/SKILL.md)**: Stress-test a plan and document agreed terms and decisions.
- **[handoff](./handoff/SKILL.md)**: Compact the current conversation into a handoff document so another agent can continue the work.
- **[teach](./teach/SKILL.md)**: Teach the user a new skill or concept over multiple sessions, using the current directory as a stateful teaching workspace.
- **[to-questionnaire](./to-questionnaire/SKILL.md)**: Turn a decision you can't answer alone into a Markdown questionnaire for the one person who can (filled in async, or together over a meeting).
- **[to-spec](./to-spec/SKILL.md)**: Turn a settled conversation into a project spec.
- **[to-tickets](./to-tickets/SKILL.md)**: Break a plan into verifiable tickets with explicit blockers.
- **[retro](./retro/SKILL.md)**: Review a work session and rank improvements for future runs.
- **[wayfinder](./wayfinder/SKILL.md)**: Map the decisions for a large effort and resolve them in dependency order.
- **[wait-what](./wait-what/SKILL.md)**: Fire this the moment a message doesn't land. The agent re-pitches it with the context you're missing, in plain English, using your `GLOSSARY.md` vocabulary.

## Model-invoked

Model- or user-reachable (rich trigger phrasing so the model can reach for them).

- **[domain-modeling](./domain-modeling/SKILL.md)**: Clarify shared project terms and record significant decisions.
- **[grilling](./grilling/SKILL.md)**: Interview the user relentlessly about a plan, decision, or idea until every branch of the design tree is resolved.
- **[research](./research/SKILL.md)**: Investigate a question with primary sources and save cited findings.
- **[writing-for-agents](./writing-for-agents/SKILL.md)**: Writing documents for agents: skills, AGENTS.md/CLAUDE.md, and any doc an agent reaches by a pointer.
