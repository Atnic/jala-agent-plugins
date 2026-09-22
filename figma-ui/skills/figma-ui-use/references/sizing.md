# Sizing: FIXED, HUG, and FILL

Sizing values describe how a node behaves in an Auto Layout relationship. They are not a substitute for thinking about the parent-child contract.

## Intent table

| Intent | Behavior | Typical use |
| --- | --- | --- |
| `FIXED` | Keep the explicit dimension. | Icon containers, sidebars, input heights, or a viewport-sized root. |
| `HUG` | Derive the dimension from content plus padding. | Buttons, badges, labels, cards whose height follows content. |
| `FILL` | Consume available space from the parent. | Main columns, full-width inputs, content regions, and stretchable cards. |

For `figma-ui-mcp`, pass `layoutSizingHorizontal` and `layoutSizingVertical` on the node when the current API supports the axis. The value applies to the node as an Auto Layout child; it is not meaningful as a free-floating absolute node. The legacy frame controls `primaryAxisSizingMode` and `counterAxisSizingMode` still matter for the parent, so use the combination that `figma_docs` describes for the current version.

## Defaults worth starting from

```text
Button       HUG × HUG
Input        FILL × FIXED
Card         FILL × HUG
Sidebar      FIXED × FILL
Main         FILL × FILL/HUG, based on the parent
```

Treat these as defaults only. Existing document variables, component definitions, and layout conventions take precedence.

## Text and reflow

Text is a common source of accidental overflow. For a text block that should wrap:

```js
await figma.create({
  type: "TEXT",
  parentId: section.id,
  content: "A description that may wrap to more than one line.",
  layoutAlign: "STRETCH",
  layoutSizingHorizontal: "FILL",
  lineHeight: 20
});
```

For a label inside a HUG button, use HUG on the label's relevant axis so a longer label can reflow the parent. For a paragraph in a fixed-width content column, fill the available width and let the vertical axis hug the resulting lines.

Do not increase a fixed width arbitrarily to hide overflow. First check the parent sizing mode, the text node's sizing axis, the available width, and the line height.

## Debug checklist

When a node is unexpectedly too small or too large:

1. Read the node and its parent with `figma_read`.
2. Check whether the node is actually a child of an Auto Layout frame.
3. Check both `layoutSizing*` axes.
4. Check parent `primaryAxisSizingMode`/`counterAxisSizingMode`.
5. Check `layoutAlign` and `layoutGrow`.
6. Check padding, item spacing, and text line height.
7. Screenshot after the smallest corrective modification.
