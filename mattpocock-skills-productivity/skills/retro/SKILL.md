---
name: retro
description: "Review a project or work session and suggest improvements for future runs."
---

The user has asked for a **retrospective**. You are suggesting improvements to the project's **working environment** to improve future runs.

## Steps

1. Read the bundled [writing-for-agents](../writing-for-agents/SKILL.md) when proposing changes to instructions agents use.

2. Read the primary sources for the work the user specifies, such as the conversation, project documents, handoffs, and outputs. Default to the current session when no other work is named.

3. Look for candidates for improvement in these categories.

- **Navigation**: how easy was it to find the right documents and decisions? Are there hidden dependencies between files? Would a **navigation pointer** make it easier? _Use when_ the session took a long time to find a piece of information.
- **Automated checks**: could a repeatable check have caught the error, such as a missing field or broken link? Look for an existing check before proposing one.
- **Review standards**: did a deliverable miss a quality criterion that required judgment? Suggest a concrete review rule in the checklist people already use.
- **Handoffs**: did the next person or agent have the decisions, source links, and open work they needed? Suggest the smallest change to the handoff that would have helped.
- **Project instructions**: are relevant instructions easy to find at the point of use? Move detailed guidance to a focused reference when readers only need a pointer.
- **Tool economy**: did the agent make expensive tool calls that could be streamlined? Is there any custom tooling (CLI's, MCP's) that is particularly token-inefficient? _Use when_ the agent made an expensive tool call.
- **No-ops**: look for instructions in steering files that don't modify the agent's behavior. _Use when_ the steering files are large and unwieldy.
- **Information access**: look for opportunities to increase the agent's access to information. A current source document, an activity record, or access to a reference. _Use when_ a crucial piece of information was not available to the agent.

4. Present candidates in order of severity. For each, cite the observed friction and suggest the smallest change that would improve the next run.

## Reference

### Doing the work and reviewing it

The person or agent doing the work has to keep the current task in view. Put detailed quality criteria with the review checklist so the reviewer can apply them against the actual deliverable.

### Where improvements belong

- Put navigation pointers in the instructions people or agents already read.
- Put judgment calls in the relevant review checklist or project standards.
- Put repeatable checks in the workflow that can catch the mistake.
- Put reusable workflows in skills. Use the bundled writing guidance to keep instructions short and discoverable.
