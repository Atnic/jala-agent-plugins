# Scroll behavior

## When to add scrolling

A frame should scroll only when its content intentionally exceeds a bounded viewport. Before writing:

1. Read the frame's width, height, children, and current `clipsContent` value.
2. Confirm whether overflow is horizontal, vertical, or both.
3. Confirm that the parent layout and child sizing allow content to exceed the viewport.
4. Set the smallest matching `overflowDirection` with `setScrollBehavior`.
5. Read the node back and screenshot the resting state.

## Common patterns

```text
Mobile screen
└── Content viewport [VERTICAL scroll, clips content]
    └── Content stack [HUG height]
```

```text
Data table
└── Table viewport [HORIZONTAL or BOTH, clips content]
    └── Table content [FIXED/minimum width]
```

Do not set scrolling on a parent that should expand with content. Avoid clipping a shadow, focus ring, or overlay that intentionally extends beyond a frame.
