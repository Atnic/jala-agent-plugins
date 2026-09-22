# Prototype patterns

## Navigate on click

Use an existing interactive control and an existing destination frame. Read the control's reactions, then add or update only the intended `ON_CLICK` action with a documented `NAVIGATE` target and transition. Verify the destination ID is in the same connected document.

## Overlay and swap

Use `OVERLAY` for menus, dialogs, and transient panels when the product flow calls for a layered destination. Use `SWAP` for stateful frames or component-driven transitions when the target is a sibling state. Prefer component properties for local state and frame navigation for page-level state.

## Hover and press

Use `ON_HOVER` or `ON_PRESS` only when the interaction is meaningful in the prototype. Keep the action set small and ensure the resting state remains legible. If the design system defines hover/pressed variants, reuse them.

## Transition discipline

Use the public transition shape documented by `figma_docs`. Prefer the design system's established duration and easing. Do not invent private enum names or assume every transition type is supported by the local bridge.
