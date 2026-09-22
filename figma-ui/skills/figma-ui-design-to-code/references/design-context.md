# Local design context

## Read sequence

For a screen or component, use this sequence with the same `sessionId`:

```text
figma_status
→ figma_docs
→ figma_rules
→ figma_read get_design_context
→ figma_read screenshot
→ figma_read get_component_map
→ figma_read get_node_detail for ambiguous nodes
```

Use `get_design_context` for the implementation-oriented summary, `get_design` for the full hierarchy, and `get_node_detail` for a single node's fills, bound variables, style references, instance overrides, and CSS-like properties.

## Read efficiently

- Start at the requested root, not the entire page.
- Use a shallow tree to understand regions, then read ambiguous children.
- Use `includeHidden: true` only when hidden content is in scope.
- Use `get_css` as a cross-check, not as a complete application layout.
- Read variables and styles once per design-system context, then reuse the mapping.

## Sparse or ambiguous results

If the design context does not contain enough detail to implement a visible region:

1. Screenshot the root.
2. Identify the missing child IDs from the tree.
3. Read those children with `get_design_context` or `get_node_detail`.
4. Reconcile the result with the screenshot.

Do not fill missing details from memory or invent component behavior.
