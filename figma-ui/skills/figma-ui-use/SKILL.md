---
name: figma-ui-use
description: Use figma-ui-mcp safely for non-trivial Figma reads and writes, with mandatory discovery, Auto Layout, token, component, editing, and screenshot-verification practices.
---

# figma-ui-use

This is the low-level foundation for all substantial Figma work through this plugin. Load and follow it whenever an agent reads, creates, or modifies more than a trivial Figma node. The higher-level design and library skills depend on this runtime contract.

## Runtime boundary

This plugin targets the local/open-source `figma-ui-mcp` server. Its primary tools are:

| Tool | Use it for |
| --- | --- |
| `figma_status` | Confirm the localhost bridge and connected Figma sessions. |
| `figma_docs` | Load the actual `figma-ui-mcp` API and design rules before writing. |
| `figma_rules` | Read the current document's variables, styles, typography, and component rule sheet. |
| `figma_read` | Inspect selections, node trees, variables, styles, components, and screenshots. |
| `figma_write` | Execute the bridge's supported JavaScript operations to create or modify nodes. |

Do not assume that another Figma integration is present. In particular, do not blindly call `use_figma`, `get_metadata`, `get_screenshot`, `search_design_system`, or `get_libraries`. Those names belong to other runtimes and are not aliases for this server. Use the five tools above unless the current host independently exposes another integration and the user explicitly asks for it.

`figma_write` is not a generic REST mutation endpoint. It executes the `figma-ui-mcp` sandbox API, commonly using operations such as `figma.create`, `figma.modify`, `figma.createComponent`, `figma.instantiate`, `figma.setupDesignTokens`, and variable/style helpers. Always load `figma_docs` for the current operation signatures instead of translating another MCP API mechanically.

The current bridge also exposes prototype and interaction helpers such as `setReactions`, `getReactions`, `removeReactions`, `setScrollBehavior`, component-property operations, and component swapping. Load `figma-ui-use-motion` for those workflows. This is not the same as Figma's official motion skill: the local runtime does not expose manual keyframe tracks, animation styles, or timeline APIs.

## Mandatory lifecycle

For substantial work, follow this order:

1. Call `figma_status`.
2. Call `figma_docs` with no section for the quick-start rules; load focused sections such as `layout`, `api`, `tokens`, or `icons` when needed.
3. Call `figma_rules` before choosing visual constants or creating a library.
4. Call `figma_read` to inspect the current page, selection, or target node.
5. Plan the node hierarchy and Auto Layout relationships before writing.
6. Call `figma_write` to create or modify the smallest useful set of nodes.
7. Call `figma_read` with `operation: "screenshot"` on the root frame.
8. Inspect the screenshot and the resulting node tree.
9. Modify existing nodes to correct problems; do not rebuild a whole screen to change one element.
10. Screenshot again until structure and appearance are both correct.

Do not declare completion after step 6. A successful write only proves that the bridge accepted the request.

## Session and read discipline

If `figma_status` reports multiple connected files, ask which file is the target when the context is ambiguous. Once selected, pass its `sessionId` to every subsequent `figma_read` and `figma_write` call. Do not rely on whichever Figma tab was polled most recently.

Use `figma_read` for facts about the document. Useful operations include `get_selection`, `get_page_nodes`, `get_design`, `get_node_detail`, `get_variables`, `get_styles`, `get_local_components`, `get_component_map`, `search_nodes`, and `screenshot`. If a user refers to “this frame”, “the selected frame”, or a hidden layer, read the selection or include hidden nodes before acting.

Each `figma_write` execution is an isolated JavaScript sandbox. Redeclare constants and helper functions in every call. Re-query node IDs with `figma_read` between calls rather than assuming an ID or variable from a previous write still exists. The sandbox cannot replace document reads; use `figma_read` instead of attempting unsupported `figma.getChildren()`, `figma.getNodeChildren()`, or `figma.read()` calls inside write code.

## Container-first construction

Build hierarchy before leaf content:

```text
root
→ major regions
→ sections
→ reusable components
→ text, icons, and other leaf content
```

For example:

```text
Dashboard
├── Sidebar [fixed width]
└── Main [fills width]
    ├── Header
    ├── KPI Row
    │   ├── KPI Card
    │   ├── KPI Card
    │   └── KPI Card
    └── Content
```

Use frames with Auto Layout for major structural relationships. Manual `x`/`y` is appropriate for top-level canvas placement and genuinely absolute children, not as the default layout engine for every leaf.

## Auto Layout is a first-class constraint

When a relationship is structural, prefer a frame with `layoutMode`, padding, spacing, and alignment over manual coordinates. Think in terms of:

- `layoutMode`: `HORIZONTAL`, `VERTICAL`, or `NONE` for a genuinely absolute wrapper.
- `paddingTop`, `paddingRight`, `paddingBottom`, `paddingLeft` (or `padding`) for container insets.
- `itemSpacing` for sibling rhythm.
- `primaryAxisAlignItems` for the main axis.
- `counterAxisAlignItems` for the cross axis.
- `layoutSizingHorizontal` and `layoutSizingVertical`: `FIXED`, `HUG`, or `FILL` for child sizing intent.
- `layoutAlign: "STRETCH"` and `layoutGrow: 1` when a child should fill or grow within its parent.

Default sizing intent:

| Element | Horizontal | Vertical |
| --- | --- | --- |
| Button | `HUG` | `HUG` |
| Input | `FILL` | `FIXED` or `HUG` |
| Card | `FILL` | `HUG` |
| Sidebar | `FIXED` | `FILL` |
| Main content | `FILL` | `FILL` or `HUG`, based on its parent |

These are behavior choices, not arbitrary dimensions. Use the bridge's actual properties and confirm edge cases in `figma_docs`. See the references for layout and sizing patterns.

## Design-system and component priority

Before hardcoding a color, type style, radius, spacing value, or repeated element:

1. Call `figma_rules`.
2. Inspect variables with `figma_read`.
3. Inspect styles.
4. Inspect local components and variants.
5. Reuse the existing asset.
6. Create a reusable component only when no suitable one exists.
7. Use primitive nodes only for genuinely one-off content.

Do not use a rectangle plus a text node as a fake button when a Button component exists. Instantiate the component, select its variant, and override supported properties. Prefer variables/tokens for color, spacing, radius, typography, and other repeated visual properties. Existing project conventions always outrank defaults in these skills.

## Editing existing designs

When the user asks to improve, restyle, or convert an existing screen:

- read the selection or target node first;
- preserve existing components, names, and variable bindings where possible;
- modify the smallest existing nodes that satisfy the request;
- keep the visual result stable when the request is structural-only;
- screenshot before and after the change.

Do not delete and recreate an entire screen to change a label, color binding, padding, or one component instance.

## Bridge-specific guardrails

- Draw background layers first; later siblings render above earlier siblings.
- Use `counterAxisAlignItems: "MIN"` plus child `layoutAlign: "STRETCH"` when children should fill a cross axis; do not use unsupported `counterAxisAlignItems: "STRETCH"`.
- Keep overlapping progress-bar fills inside a non-layout wrapper rather than an Auto Layout frame.
- Use `textAlign` for text content alignment and `layoutAlign` for the text box's relationship to its parent.
- Constrain wrapping text with a fill/stretching parent; do not increase arbitrary fixed widths to hide overflow.
- Use the icon helpers documented by `figma_docs`; do not use emoji as UI icons.
- Never assume helper variables persist across `figma_write` calls.
- Use `setReactions`/`getReactions`/`removeReactions` for supported prototype links; do not invent unsupported timeline or keyframe calls.

## References

- [Auto Layout](references/auto-layout.md)
- [Sizing](references/sizing.md)
- [Typography](references/typography.md)
- [Components](references/components.md)
- [Gotchas](references/gotchas.md)
