---
name: figma-ui-design-to-code
description: Implement Figma designs as production code using figma-ui-mcp design context, local assets, CSS inspection, component mapping, and visual verification.
---

# figma-ui-design-to-code

Use this skill when the user wants to implement, port, or code a Figma screen or component. Load `figma-ui-use` first; this skill owns the design-to-code workflow, while `figma-ui-use` owns the local bridge contract.

This is the reverse direction of `figma-ui-generate-design`: read from a connected local Figma file and implement the result in the target codebase. It does not write changes back to Figma unless the user separately asks for that.

## Local runtime mapping

Use the local tools, not the official hosted MCP tools:

| Need | Local operation |
| --- | --- |
| High-fidelity design context | `figma_read` with `operation: "get_design_context"` |
| Visual target | `figma_read` with `operation: "screenshot"` |
| Structural details | `figma_read` with `operation: "get_design"` or `"get_node_detail"` |
| CSS-like inspection | `figma_read` with `operation: "get_css"` |
| Token/style discovery | `figma_read` with `"get_variables"` and `"get_styles"` |
| Component mapping | `figma_read` with `"get_component_map"` and `"get_unmapped_components"` |
| Static assets | `figma_read` with `"export_svg"` or `"export_image"` |

These are the read operations documented by the pinned `figma-ui-mcp` API. `get_design_context` is an implementation-oriented summary, `get_css` is a CSS-like node inspection, `export_svg` returns SVG markup, and `export_image` returns base64 PNG/JPG data. They provide source context; they do not generate or save production application code for you. Confirm important layout and asset details against the screenshot and node reads before implementing.

## Workflow

### 1. Discover the target

Call `figma_status`, select the intended session, then call `figma_docs`, `figma_rules`, and `figma_read` on the target node. If the user supplied a Figma URL, extract the node ID but still verify the node in the connected file. Do not guess from a URL alone.

Request design context and a screenshot for the same root or component. The screenshot is the visual target; the structured response is the source for hierarchy, layout, tokens, components, and asset references.

### 2. Inspect the codebase

Before editing code, inspect the target project's stack, routing, layout system, existing components, tokens, asset conventions, and likely file paths. Find matching code components before writing new markup. Reuse the project's primitives and design tokens rather than copying raw Figma coordinates into ad hoc CSS.

### 3. Build a mapping

Map the design tree to code:

```text
Figma region       → application component
Figma component    → existing code component or explicit new component
Figma variable     → project token
Figma text style   → project typography role
Figma asset        → local asset or dynamic data source
Figma interaction  → existing route/state/event model
```

Use `get_component_map` to find component sets, variants, and suggested mappings. Treat `get_unmapped_components` as a review queue, not permission to replace every component with primitives.

### 4. Implement

Implement the requested scope using the project's native layout primitives. Translate Figma Auto Layout into flex/grid/component layout rather than reproducing absolute `x`/`y` values. Preserve intended fixed dimensions only where the design clearly requires them. Make interactions real when the application context supports them; do not create a static screenshot masquerading as UI.

Use exact static assets when available. Use `export_svg` for vector markup or `export_image` for raster PNG/JPG data; handle the returned format and base64 payload according to the target repository's asset conventions. Preserve intrinsic dimensions and aspect ratio. Do not assume the bridge exports WebP or writes files directly, and do not leave temporary Figma URLs in source code. Keep dynamic, API-supplied images dynamic.

### 5. Verify

Run the target project's normal checks and render the requested screen at the intended viewport. Compare it with the Figma screenshot. Check layout, typography, spacing, colors, radius, borders, shadows, icons, asset geometry, and interactive states. Fix every in-scope mismatch before finishing; do not expand the task to unrelated pre-existing differences.

## Guardrails

- Do not call `get_design_context`, `get_metadata`, or `get_screenshot` as official MCP tools; use `figma_read` operations.
- Do not implement from a sparse tree without correlating it to a screenshot and child-node reads.
- Do not use Figma screenshots as implementation assets.
- Do not override SVG root dimensions broadly with `width: 100%`/`height: 100%` when the asset's intrinsic dimensions carry meaning.
- Do not hardcode colors or spacing when matching project tokens exist.
- Do not rebuild a shared application component only to match one screen.

## References

- [Design context](references/design-context.md)
- [Asset handoff](references/asset-handoff.md)
- [Verification](references/verification.md)
