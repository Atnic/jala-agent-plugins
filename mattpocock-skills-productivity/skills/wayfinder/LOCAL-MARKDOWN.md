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

### Claims and parallel work

Use one coordinating session per local map. It claims tickets before work starts by setting **Claimed by**, assigns ticket numbers, and writes ticket and map updates. Workers can run in parallel in a shared workspace. They write their own findings files and return the results to the coordinator to record. If no session is coordinating concurrent work, run tickets one at a time.

When a ticket is resolved, add a **Resolution** section with the answer and links to any supporting files, set its status to **resolved**, and add its title link and a one-line summary to the map's **Decisions so far**. For work ruled out, set its status to **out-of-scope** and link it from the map's **Out of scope** section with the reason. If work stops before resolution, clear the claim so another session can resume.
