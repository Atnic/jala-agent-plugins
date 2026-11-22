---
name: to-tickets
description: Break a plan, spec, or conversation into tickets with verifiable outcomes and explicit blockers. Save one file per ticket or use the project's tracker.
---

# To Tickets

Break a plan, spec, or conversation into a set of **tickets**: small, independently verifiable outcomes, each declaring the tickets that **block** it.

Use the project's tracker conventions when the user wants tracker tickets. Otherwise, use local files.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments.

### 2. Read the project documents (optional)

Check the relevant plans, glossary, and decision records to understand the current work. Look for existing work to reuse and prerequisites the plan depends on.

### 3. Draft tickets around outcomes

Give each ticket a small, complete outcome. For example, pilot a workshop with one group before opening registration to everyone.

<vertical-slice-rules>

- Include the work needed to deliver the outcome.
- Make the outcome verifiable on its own.
- Size each ticket so it can be picked up and completed in one work session.
- Put shared prerequisites first when they genuinely block delivery.

</vertical-slice-rules>

Give each ticket its **blocking edges**: the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

**Changes that must roll out in stages are an exception.** If switching everything at once would interrupt the work, introduce the new process beside the existing one. Move teams or materials over in batches, then retire the old process once every batch is complete. Give the rollout, each batch, and the retirement their own tickets and dependencies. Include a final check when only the combined change can be verified.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the outcome this ticket delivers

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct: does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the user approves the breakdown.

### 5. Save the approved tickets

Use the same outcomes and blockers in either format:

- **Local files** → write one file per ticket where the project keeps tasks, or under `docs/tasks/<effort-slug>/<NN>-<slug>.md` if there is no convention, numbered from `01` in dependency order (blockers first). Each file's "Blocked by" links to the files it depends on. Use the per-ticket file template below: one ticket per file, never a single combined file.
- **Project tracker (when requested)** → publish one issue per ticket in dependency order (blockers first) so each ticket's blocking edges can reference real identifiers. Use the platform's native blocking relationship where it has one; otherwise set each ticket's "Blocked by" to the blocking issues. If the source was an existing issue, make each ticket its sub-issue (tracker doc's operation). Apply the project's ready label only if its tracker conventions call for it.

Report which tickets can start because all their blockers are done.

Leave the parent issue open and its content intact.

<local-ticket-template>

# <NN>: <Ticket title>

**What it delivers:** the outcome and who benefits.

**Blocked by:** relative links to the tickets that gate this one, or "None (can start immediately)".

**Status:** open

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2

</local-ticket-template>

<issue-template>

## Parent

A reference to the parent issue on the tracker (if the source was an existing issue, otherwise omit this section).

## What it delivers

The outcome and who benefits.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by

- A reference to each blocking ticket, or "None (can start immediately)". Omit this section when blockers were set as native edges.

</issue-template>

Include a short excerpt from a prototype when it captures the outcome or an agreed constraint more precisely than prose.
