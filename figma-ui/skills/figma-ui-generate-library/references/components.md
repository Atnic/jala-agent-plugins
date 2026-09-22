# Library components

## Component anatomy

A reusable component should own its internal hierarchy:

```text
Component frame [Auto Layout]
├── icon or leading slot
├── label/content
└── trailing slot or state affordance
```

Use the smallest useful public property set. Keep internal spacing and token bindings inside the component so instances do not need manual coordinate fixes.

## Build order

1. Define or confirm variables and styles.
2. Create the Auto Layout component shell.
3. Add content with HUG/FILL/FIXED intent.
4. Bind colors, typography, spacing, and radius.
5. Convert the complete frame to a component.
6. Add variants for meaningful size/state/tone axes.
7. Create a representative instance.
8. Read and screenshot the instance.

## Variant hygiene

Use clear, orthogonal properties such as:

```text
Size = Small | Medium | Large
State = Default | Hover | Disabled
Tone = Neutral | Primary | Danger
```

Do not create a separate variant for every label or content combination. Use bound text and instance properties for content.

## Evolving existing components

Read the component set, its variants, and a representative instance before changing it. Preserve property names and variant values when possible. If a breaking rename is necessary, identify the affected instances and validate them after the change.
