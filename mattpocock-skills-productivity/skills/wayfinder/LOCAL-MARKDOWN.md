# Wayfinder in local Markdown

Follow the project's planning folder convention. With no convention, create `docs/wayfinder/<effort-slug>/MAP.md` and a sibling `tickets/` folder. Use the map body from [Wayfinder](./SKILL.md). Put each ticket in `tickets/NNNN-short-title.md`, using the next available number. The path is its stable link and the number gives it a place in the order.

## Ticket format

```markdown
# {Ticket title}

- Type: research | prototype | grilling | task
- Status: open | resolved | out-of-scope
- Claimed by: {session or owner, or None}
- Blocked by: {relative links to blocking tickets, or None}

## Question

{The decision or investigation this ticket resolves}
```

Create the ticket files before linking blockers. List ready tickets in filename order. A ticket is ready when it is open, unclaimed, and every linked blocker is resolved or the dependency has been removed. When a blocker goes out of scope, update dependent tickets to reflect whether they can proceed or need a replacement decision.

Re-read a ticket immediately before claiming it and set **Claimed by** before starting. If another session already claimed it, choose another ready ticket. For parallel work, use a shared workspace and coordinate ticket claims before dispatch. Each worker writes to its own findings file, and the coordinating session updates the map.

When a ticket is resolved, add a **Resolution** section with the answer and links to any supporting files, set its status to **resolved**, and add its title link and a one-line summary to the map's **Decisions so far**. For work ruled out, set its status to **out-of-scope** and link it from the map's **Out of scope** section with the reason. If work stops before resolution, clear the claim so another session can resume.
