# Visual verification

## Required loop

After every substantial generation or structural conversion:

1. Read the root frame's node tree.
2. Request a screenshot with `figma_read` and `operation: "screenshot"`.
3. Inspect the screenshot at a useful scale.
4. Compare suspicious geometry with the node data.
5. Modify the smallest existing nodes.
6. Screenshot again.

## Review questions

### Structure

- Are the root and major regions named and nested correctly?
- Are structural relationships represented by Auto Layout?
- Are there accidental absolute coordinates inside a flow layout?

### Sizing

- Should this child be `FIXED`, `HUG`, or `FILL` on each axis?
- Is a parent set to HUG while a child needs to stretch?
- Is text constrained enough to wrap?
- Does content fit without relying on accidental overflow?

### Visual quality

- Is anything clipped, overlapped, or hidden under a later background?
- Are spacing, radii, and typography consistent with the discovered system?
- Are icons the right size and aligned to neighboring text?
- Is contrast sufficient for text and controls?

### Reuse and tokens

- Were existing components instantiated instead of redrawn?
- Are repeated colors, spacing, radii, and type roles tokenized?
- Are component variants and properties preserved?

## Do not overcorrect

Fix observed issues, not hypothetical ones. Preserve the user's existing visual language and unrelated nodes. A verification pass should refine the generated result, not trigger a full redesign.
