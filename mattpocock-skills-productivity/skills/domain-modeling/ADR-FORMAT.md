# ADR Format

By default, decision records (ADRs) live in `docs/adr/` and use sequential numbering: `0001-slug.md`, `0002-slug.md`, etc.

Create the `docs/adr/` directory lazily: only when the first ADR is needed.

## Template

```md
# {Short title of the decision}

{1-3 sentences: what's the context, what did we decide, and why.}
```

That's it. An ADR can be a single paragraph. The value is in recording *that* a decision was made and *why*, not in filling out sections.

## Optional sections

Only include these when they add genuine value. Most ADRs won't need them.

- **Status** frontmatter (`proposed | accepted | deprecated | superseded by ADR-NNNN`): useful when decisions are revisited
- **Considered Options**: only when the rejected alternatives are worth remembering
- **Consequences**: only when non-obvious downstream effects need to be called out

## Numbering

Scan `docs/adr/` for the highest existing number and increment by one.

## When to offer an ADR

All three of these must be true:

1. **Hard to reverse**: the cost of changing your mind later is meaningful
2. **Surprising without context**: a future reader will wonder "why on earth did they do it this way?"
3. **The result of a real trade-off**: there were genuine alternatives and you picked one for specific reasons

If a decision is easy to reverse, skip it: you'll just reverse it. If it's not surprising, nobody will wonder why. If there was no real alternative, there's nothing to record beyond "we did the obvious thing."

### What qualifies

- **How the work is organized.** “One team coordinates registration for all workshops.”
- **Handoffs between teams.** “Facilitators receive the final participant list two days before each workshop.”
- **Choices that are costly to reverse.** A venue contract or a registration provider that would take months to replace.
- **Boundary and scope decisions.** “Registration owns changes to participant details. Facilitators request corrections through Registration.”
- **Deliberate deviations from the obvious path.** “We keep a fixed number of seats for partner organizations because they confirm attendance after public registration opens.”
- **Constraints that a reader might miss.** “The venue contract requires final attendance numbers two weeks before the event.”
- **Rejected alternatives when the rejection is non-obvious.** If you considered rolling enrollment and chose fixed cohorts, record why if the reason might be missed later.
