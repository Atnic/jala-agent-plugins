# Layout patterns

## Sidebar and main content

```text
Root: HORIZONTAL, fixed viewport size
├── Sidebar: FIXED width, FILL height
└── Main: FILL width, FILL height, VERTICAL
    ├── Header: FILL width, HUG height
    └── Content: FILL width, FILL/HUG height
```

The root owns the horizontal relationship. The Main frame owns the vertical relationship. This is more resilient than positioning every child relative to the canvas.

## Header

Use a horizontal Auto Layout frame with `counterAxisAlignItems: "CENTER"`. Give the title a HUG axis, give a flexible spacer `layoutGrow: 1` only when the alignment contract is clear, and group right-side actions as a separate row. If the header needs a centered title with asymmetric controls, use a deliberate three-column structure rather than hoping `SPACE_BETWEEN` creates visual centering.

## KPI/stat row

Use a horizontal row with consistent `itemSpacing`. Each card can be `layoutSizingHorizontal: "FILL"` when equal-width cards are intended, or HUG when cards should follow content. Keep the card itself vertical Auto Layout with consistent padding and a constrained numeric/value hierarchy.

## Card

Use a vertical frame with padding and item spacing. Add full-width children using `layoutAlign: "STRETCH"` and the intended `layoutSizingHorizontal`. Keep content inside the card's frame; do not place a separate background rectangle beside the card's children.

## Form field

Make the field one component frame containing label, control, helper text, and error state as appropriate. Use a fixed or tokenized control height, HUG label height, and FILL width within the form column. Check long labels and error copy in the screenshot.

## Button

Make the button an Auto Layout component with HUG × HUG sizing by default. Use a fixed height only when the design system requires it. Center icon and label with `counterAxisAlignItems: "CENTER"`; expose size and state variants rather than duplicating rectangles.

## Intentional overlays

Progress bars, badges over avatars, and media overlays are legitimate absolute relationships. Put overlapping children inside a `layoutMode: "NONE"` wrapper and keep that wrapper as one child of the surrounding Auto Layout frame. Do not put overlapping siblings directly inside an Auto Layout parent.

## Responsive intent

Before creating a second breakpoint, identify what should fill, hug, or remain fixed. Use nested containers and component sizing to express that behavior. If the user requests a single static artboard, do not invent responsive variants, but still avoid unnecessary absolute placement.
