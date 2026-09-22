# Auto Layout with figma-ui-mcp

Auto Layout is the default for structural relationships. Build the parent frame first, configure its layout, then add children without manual coordinates unless an element is intentionally absolute.

## Parent properties

| Property | Meaning | Practical guidance |
| --- | --- | --- |
| `layoutMode` | Main axis of the frame. | Use `HORIZONTAL` for rows and `VERTICAL` for stacks. Use `NONE` only for an intentional absolute wrapper. |
| `paddingTop`, `paddingRight`, `paddingBottom`, `paddingLeft` | Insets between the frame edge and children. | Keep the values consistent with existing tokens. `padding` is convenient when all four sides match. |
| `itemSpacing` | Gap between adjacent children. | Use spacing tokens; do not encode repeated gaps with child `x`/`y`. |
| `primaryAxisAlignItems` | Main-axis distribution. | Use `MIN`, `CENTER`, `MAX`, or `SPACE_BETWEEN` for the actual content need. |
| `counterAxisAlignItems` | Cross-axis alignment. | `CENTER` is the default for icon/text rows; `MIN` plus child stretch is safer for vertical stacks. |
| `primaryAxisSizingMode` | Legacy main-axis sizing mode. | Use `AUTO` when the parent should hug its contents and `FIXED` when it must accept a fixed/fill child axis. |
| `counterAxisSizingMode` | Legacy cross-axis sizing mode. | Pair with child `layoutAlign` and `layoutSizing*` intent; confirm the current behavior in `figma_docs`. |

## Common patterns

```js
// Vertical content stack.
var content = await figma.create({
  type: "FRAME",
  name: "Content",
  layoutMode: "VERTICAL",
  primaryAxisAlignItems: "MIN",
  counterAxisAlignItems: "MIN",
  padding: 24,
  itemSpacing: 16
});

// Full-width child in a vertical stack.
await figma.create({
  type: "FRAME",
  parentId: content.id,
  name: "Main Section",
  layoutAlign: "STRETCH",
  layoutSizingHorizontal: "FILL",
  layoutMode: "VERTICAL",
  itemSpacing: 12
});

// Icon and label row.
var row = await figma.create({
  type: "FRAME",
  layoutMode: "HORIZONTAL",
  primaryAxisAlignItems: "MIN",
  counterAxisAlignItems: "CENTER",
  itemSpacing: 8
});
```

Create a button as one Auto Layout frame with the label inside it. Create a card as a vertical Auto Layout frame with full-width children. For a progress bar or badge overlay, use a non-layout wrapper only where sibling overlap is the intended visual behavior.

## Alignment pitfalls

- Do not use `counterAxisAlignItems: "STRETCH"`; use `MIN` on the parent and `layoutAlign: "STRETCH"` on children that should fill.
- Do not combine `layoutGrow: 1` with `primaryAxisAlignItems: "CENTER"` when visual centering matters. A growing child consumes the available space before centering is applied; use `SPACE_BETWEEN` or explicit padding instead.
- A `layoutAlign: "STRETCH"` text box still needs `textAlign: "CENTER"` if its content should be centered.
- Create the background before overlays and content because later siblings sit above earlier siblings.

## Construction order

1. Create the root frame and set its name and top-level dimensions.
2. Set the root layout and sizing intent.
3. Create major regions such as Sidebar and Main.
4. Configure each region before adding children.
5. Add repeated components through instances.
6. Add leaf text/icons last.
7. Read the node tree and screenshot the root.

This ordering makes the hierarchy inspectable and avoids fragile manual coordinate math.
