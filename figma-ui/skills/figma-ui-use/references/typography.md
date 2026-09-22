# Typography and text reflow

Typography is part of the design system, not a collection of arbitrary values added while drawing.

## Discovery first

Before setting `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, or letter spacing:

1. Call `figma_rules`.
2. Read available text styles with `figma_read` and `operation: "get_styles"`.
3. Reuse a matching text style or token.
4. If no style exists, choose a deliberate type scale and document the new semantic role.

Avoid hardcoding a different font family or weight for every text node. Prefer the document's existing type styles and use the bridge's `applyTextStyle` or equivalent operation where supported.

## Text box behavior

- Use `textAlign` to control the content inside a text box.
- Use `layoutAlign` and `layoutSizing*` to control the text box inside an Auto Layout parent.
- Give centered text both a constrained width and `textAlign: "CENTER"`.
- Use `layoutAlign: "STRETCH"` for paragraphs and multi-line descriptions that should wrap within a parent.
- Give large display numerics an explicit line height close to their font size.
- Check text overflow and baseline alignment in the screenshot, not only in the write response.

Font availability is session-specific. After creating or applying a text style, read the style or a representative text node back and verify the actual family and weight. If Figma falls back because a requested font or weight cannot be loaded, use a verified available value, document the fallback, and re-check wrapping and hierarchy; never infer success from the requested property alone.

## Icon and text rows

Use a horizontal Auto Layout row with `counterAxisAlignItems: "CENTER"` for an icon next to a label. Use the documented icon helper instead of emoji. If an icon intentionally aligns to the first line of a multi-line paragraph, use `MIN` and calculate a small top inset from the line height rather than guessing a global offset.
