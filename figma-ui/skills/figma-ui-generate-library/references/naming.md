# Naming conventions

Names are part of the design-system API. Follow the existing file convention first; use these defaults only when the file has no convention.

## Semantic node names

Prefer:

```text
Sidebar
Dashboard Header
Primary Button
KPI Card
User Avatar
Search Input
```

Avoid generated or positional names:

```text
Frame 231
Rectangle 88
Group 17
Text 29
```

## Token names

Use a predictable hierarchy, for example:

```text
primitive/color/blue/500
semantic/color/text/primary
component/button/primary/background
space/400
radius/md
type/body/md
```

The exact separator and casing should match the current document. Do not rename existing tokens just to fit this example.

## Component and variant names

Name components by semantic role, then represent state/size/tone as properties or variants. Use component-set conventions already present in the file. Avoid baking content labels into component names unless the label is a true product-specific component.

## Naming validation

Before finishing, scan the new library region for accidental default names, duplicate semantic roles, inconsistent casing, and names that describe implementation rather than intent.
