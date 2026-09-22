# Screen-building playbook

## Plan the tree

Start with the user-visible regions and their relationships. A typical product screen may look like:

```text
Product Screen
├── Sidebar [fixed width, fills height]
└── Main [fills width and height]
    ├── Header [horizontal, hug height]
    ├── Summary [horizontal, cards fill]
    └── Body [vertical, fills remaining space]
        ├── Toolbar
        └── Results
```

Name nodes by semantic role. The exact names should follow the existing file convention, but prefer `Dashboard Header`, `KPI Card`, `Search Input`, and `Primary Button` over generated names such as `Frame 231`.

## Build in layers

1. Root frame and top-level placement.
2. Major regions and their Auto Layout settings.
3. Sections and repeated item shells.
4. Existing component instances.
5. Text, icons, assets, and state content.
6. Token bindings and final refinements.

This order makes it possible to inspect the hierarchy after each meaningful step and keeps content from driving a fragile layout.

## Realistic content

Use content that exercises the layout:

- short and long labels;
- a two-line description where wrapping is expected;
- representative numeric values;
- empty, loading, error, or disabled states when requested;
- realistic icon sizes and component variants.

Do not use an overly short placeholder for every text node. A screen that only works for “Title” is not verified.

## Large screens and canvas placement

Use top-level `x`/`y` only to place the root frame on the canvas or to implement intentional absolute positioning. Keep the inside of the screen governed by nested Auto Layout. If the design includes multiple artboards, space the roots on the canvas but preserve independent, inspectable trees.

## Incremental writes

Use one write for a coherent hierarchy when practical, then read and screenshot. For a large screen, create a stable skeleton, verify it, and add sections in bounded writes. Re-query IDs between calls because the write sandbox is isolated.
