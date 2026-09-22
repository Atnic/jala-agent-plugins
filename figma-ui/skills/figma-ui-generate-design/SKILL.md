---
name: figma-ui-generate-design
description: Build or substantially modify complete Figma screens with container-first Auto Layout, component reuse, design-system discovery, and screenshot-based visual verification through figma-ui-mcp.
---

# figma-ui-generate-design

Use this skill for a complete screen, page, dashboard, flow, or multi-section UI. Also load `figma-ui-use`; this skill describes the design workflow, while `figma-ui-use` defines the actual local MCP runtime and safety rules.

## Outcome

The goal is not merely a successful write. A complete result has:

```text
write succeeded
+ hierarchy is correct
+ Auto Layout expresses the main relationships
+ existing components, styles, and variables were reused where possible
+ screenshot is visually clean
```

## Workflow

Follow this sequence:

```text
DISCOVER
↓
STRUCTURE
↓
CONTAINERS
↓
COMPONENTS
↓
CONTENT
↓
SCREENSHOT
↓
VISUAL REVIEW
↓
REFINE
```

### 1. Discover

Before creating anything, call:

1. `figma_status` and select the correct `sessionId` if needed.
2. `figma_docs` for the quick-start rules, plus `layout`, `api`, `tokens`, or `icons` sections as needed.
3. `figma_rules` to learn the current design system.
4. `figma_read` for the current page, selection, or target frame.

Read existing variables, styles, components, and nearby screens. Match the file's naming, type scale, spacing, radii, and component conventions. Never assume the default tokens in the references apply to an existing file.

### Asset-first and state-first discovery

Before drawing a generic placeholder, inspect the existing file for reusable imagery, screenshots, illustrations, and adjacent screens. Reuse or clone a real asset when the flow depends on it—for example, a receipt preview in a capture flow should use an existing receipt/photo asset when one is available. Use a placeholder only when no suitable asset exists, and make that limitation explicit in the design review.

Also map the user-visible states before building the screen: default, permission or setup, loading, success, failure, and the next action such as retake, confirm, or continue. Copy, controls, and visual feedback must correspond to the current state; do not present fabricated success indicators for an unverified condition.

For every reused component, inspect it in context after instantiation. Validate contrast, icon weight, and touch target size against the surface behind it; replace or override a low-contrast icon rather than preserving a component that becomes unreadable on the new background. Read back the actual font family and weight so a fallback is visible during review.

### 2. Structure

Write a short internal layout plan before the first mutation. Include the root dimensions, major regions, axis, sizing intent, and repeated components. For example:

```text
Root 1440 × 1024
├── Sidebar 240 fixed × fill
└── Main fill × fill
    ├── Header hug
    ├── Stats horizontal, 3 cards fill
    └── Content fill
```

Choose hierarchy before choosing exact copy or decoration. Major regions must be frames; use Auto Layout for their structural relationships.

### 3. Containers

Create the root, major regions, sections, and component shells in order. Configure `layoutMode`, padding, spacing, alignment, and sizing intent before populating children. Avoid creating all rectangles and text nodes first and trying to group them afterward.

Use manual `x`/`y` only for top-level canvas placement or an intentional absolute child. A dashboard should be understandable as a tree, not as a set of unrelated coordinates.

### 4. Components

Inspect and reuse existing components before drawing primitives. For repeated UI:

```text
existing component
→ existing variant
→ new reusable component
→ primitive only when one-off
```

Do not make a rectangle and a text node into a fake button if a Button component is available. If a new component is needed, make it Auto Layout, give it a semantic name, bind reusable properties, and instantiate it for each repeated use.

### 5. Content

Populate containers with realistic content only after the layout can support it. Use existing text styles, variables, icons, and assets. Set text sizing intentionally so labels, paragraphs, and numbers reflow without clipping. Keep content length representative of the real product; placeholder strings that never wrap create false confidence.

### 6. Screenshot and visual review

Call `figma_read` with `operation: "screenshot"` on the root frame. Inspect the result for:

- clipping, truncation, or text overflow;
- unexpected fixed sizing or broken HUG/FILL behavior;
- missing Auto Layout on structural containers;
- misalignment, accidental overlap, or incorrect layer order;
- broken spacing or inconsistent padding;
- inconsistent radius, typography, or color usage;
- hardcoded values that should use variables;
- component misuse or duplicated repeated elements.
- unrealistic placeholders where a relevant existing asset should have been reused;
- fabricated status indicators or missing states in a stateful flow;
- low-contrast icons or controls and mobile touch targets that are too small;
- actual font family/weight differing from the intended type system;
- parent bounds that do not contain their children.

Use the node tree to confirm geometry and hierarchy when a screenshot alone is ambiguous. Fix the smallest existing nodes, then screenshot again. Repeat until the result is clean.

## Editing an existing screen

For a request to improve or restructure an existing frame:

1. Read the selection or named target.
2. Record the existing component and variable bindings that must survive.
3. Plan the smallest hierarchy or property changes.
4. Modify existing nodes rather than recreating the whole screen.
5. Screenshot before and after when the change is appearance-sensitive.

For a structural conversion to Auto Layout, preserve appearance by matching current spacing and sizes first, then let the new hierarchy control future reflow. Do not “clean up” unrelated naming or styling in the same mutation.

## Completion checklist

- The intended Figma session was used.
- Existing design-system assets were inspected and reused where appropriate.
- Root and major regions form an understandable hierarchy.
- Structural relationships use Auto Layout.
- HUG/FILL/FIXED intent is explicit for important children.
- Repeated UI uses component instances.
- The result was screenshot-verified and refined.
- No official hosted Figma MCP tool was substituted for the local runtime.

## References

- [Screen building](references/screen-building.md)
- [Layout patterns](references/layout-patterns.md)
- [Verification](references/verification.md)
