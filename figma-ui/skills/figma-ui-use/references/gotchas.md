# figma-ui-mcp gotchas

These are runtime-specific guardrails. Re-check `figma_docs` when the pinned runtime changes.

## Isolated writes

Every `figma_write` call runs in a fresh JavaScript sandbox. Variables, constants, and helper functions do not persist. Redeclare them and re-query IDs at the top of each call.

## Reads are separate

The write sandbox is not a general document query API. Use `figma_read` for node trees, selections, hidden layers, variables, styles, components, and screenshots. Do not attempt unsupported `figma.getChildren()`, `figma.getNodeChildren()`, or `figma.read()` calls inside a write.

## Layer order

Children created later render above earlier children. Create background, then overlay, then controls, then content. If the screenshot shows content hidden under a background, inspect sibling order before changing coordinates.

## Auto Layout limitations

- Overlapping rectangles such as progress-bar tracks and fills need a non-layout wrapper.
- `counterAxisAlignItems: "STRETCH"` is not a supported replacement for child stretch; use `MIN` on the parent and `layoutAlign: "STRETCH"` on the child.
- A growing child can defeat visual centering when the parent uses `primaryAxisAlignItems: "CENTER"`; choose `SPACE_BETWEEN` or adjust the hierarchy.
- A child with HUG sizing can conflict with a parent that expects it to stretch. Read both sides before changing a width.

## Tokens and colors

The runtime may need a temporary literal at creation time before a variable is bound. That is not permission to leave hardcoded colors in reusable UI. Create, bind, and verify the variable. Never use the same foreground and background color for text that must be visible.

## Images and icons

Follow `figma_docs` for icon names and helpers. Do not use emoji as icons. Add background images before foreground content and inspect the screenshot for crop, scale, and layer-order problems.

## Recovery loop

When a call fails, preserve the document state, read the relevant node, and retry the smallest operation. Do not issue a blind full-screen rewrite. If the bridge disconnects, check `figma_status` and the Figma Desktop plugin before changing design code.
