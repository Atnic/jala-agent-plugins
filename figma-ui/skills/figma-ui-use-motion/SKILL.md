---
name: figma-ui-use-motion
description: Add, inspect, and maintain the prototype interactions, transitions, and scroll behavior supported by figma-ui-mcp without inventing unsupported keyframe or timeline APIs.
---

# figma-ui-use-motion

Use this skill alongside `figma-ui-use` when the user asks to make a Figma prototype interactive. The local bridge supports prototype reactions and scrolling; it does not expose Figma's official manual keyframe, animation-style, or timeline APIs.

## Supported local surface

Use `figma_write` with the documented helpers:

- `setReactions` — set click, hover, or press reactions and their actions/transitions;
- `getReactions` — inspect the current reactions on a node;
- `removeReactions` — remove reactions from a node;
- `setScrollBehavior` — configure `NONE`, `HORIZONTAL`, `VERTICAL`, or `BOTH` overflow and clipping;
- component-property and component-variant helpers when the interaction changes a component state.

These are prototype interactions, not timeline animation. Do not call `manualKeyframeTracks`, `applyManualKeyframeTrack`, `animationStyles`, `timelines`, `export_video`, or other official motion APIs that are not provided by `figma-ui-mcp`.

## Workflow

1. Call `figma_status` and select the target session.
2. Call `figma_docs` and load the `api`/`layout` sections as needed.
3. Call `figma_rules` and `figma_read` to inspect the selected node, target frames, existing components, and existing reactions.
4. Plan the interaction graph: trigger, action, destination/state, transition, and scroll container.
5. Use `figma_write` to modify only the intended nodes.
6. Read reactions back with `getReactions` and inspect the resting design with `figma_read` screenshots.
7. Verify each target frame and state; refine existing nodes rather than rebuilding screens.

## Interaction planning

Prefer a small, explicit interaction graph:

```text
Trigger: ON_CLICK / ON_HOVER / ON_PRESS
→ Action: NAVIGATE / OVERLAY / SWAP
→ Destination: existing frame or component state
→ Transition: documented transition, duration, and easing
```

Reuse existing destination frames, component variants, and state properties. If a hover or press state exists as a component variant, drive that state through the supported component-property API instead of drawing a duplicate control.

## Safe mutation

`setReactions` can replace the reaction set on a node. Always read the current reactions first and preserve unrelated interactions. When removing a reaction, target the smallest node and confirm that the requested link is gone without deleting other links.

For scroll behavior, inspect the container's size and child overflow before setting `clipsContent`. Use the smallest overflow direction that matches the design; do not turn every frame into a scroll container.

## Verification limits

`figma_read` screenshots show a resting visual state. They do not prove that a click, hover, overlay, or transition behaves correctly in the Figma prototype player. Verify the reaction payload, destination IDs, action types, and transition fields through read-back, then ask the user to preview the prototype when interactive playback is required.

## References

- [Prototype patterns](references/prototype-patterns.md)
- [Scroll behavior](references/scroll-behavior.md)
- [Verification](references/verification.md)
