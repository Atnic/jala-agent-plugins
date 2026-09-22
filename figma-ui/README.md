# figma-ui

`figma-ui` is a portable Agent Plugin for creating, inspecting, editing, and maintaining Figma documents through the local/open-source [`figma-ui-mcp`](https://github.com/TranHoaiHung/figma-ui-mcp) bridge.

It supplies three complementary skills:

- `figma-ui-use` — the runtime and safety foundation for real `figma-ui-mcp` calls.
- `figma-ui-generate-design` — container-first generation and iterative visual QA for complete screens.
- `figma-ui-generate-library` — variables, tokens, components, variants, and reusable design-system foundations.
- `figma-ui-design-to-code` — high-fidelity local design context, assets, CSS, and component mapping for implementation.
- `figma-ui-generate-diagram` — editable diagrams assembled from frames, text, vectors, and lines in an existing Figma file.
- `figma-ui-use-motion` — supported prototype reactions, transitions, and scroll behavior.

This plugin does not use Figma's hosted MCP, Figma REST API, Figma API credentials, or the official `use_figma` runtime.

## Requirements

- An Agent Plugins-compatible host.
- Figma Desktop.
- The Figma UI MCP Bridge plugin installed in Figma Desktop, imported from the upstream [`figma-ui-mcp`](https://github.com/TranHoaiHung/figma-ui-mcp) project.
- Node.js 18 or newer, for `npx`.

The bridge plugin must be open and connected to the Figma file that the agent should edit. The plugin does not create or install the Figma Desktop bridge for you.

## Architecture

```text
Agent
  ↓
figma-ui skills
  ↓
figma-ui-mcp@2.5.26 (stdio via npx)
  ↓
localhost bridge
  ↓
Figma UI MCP Bridge plugin
  ↓
Figma Desktop document
```

The MCP configuration pins `figma-ui-mcp` to `2.5.26`, the current stable package checked for this release. The first run may download that package through npm.

## Installation

1. Install and open Figma Desktop.
2. Install/import the Figma UI MCP Bridge plugin from the upstream project.
3. Open the target Figma file and run the bridge plugin so it reports a connection.
4. Install this plugin using your Agent Plugins host, selecting the `figma-ui/` directory as the plugin root.
5. Confirm that the host loads `figma-ui/mcp.json` and the three child skills.

No environment variables, Figma tokens, or API secrets are required.

## Coverage of Figma's official skills

This plugin adapts the parts of Figma's skill set that the local bridge actually exposes:

| Local skill | Covered capability |
| --- | --- |
| `figma-ui-use` | Local read/write runtime, Auto Layout, tokens, components, and verification |
| `figma-ui-generate-design` | Complete screens, views, and multi-section layouts |
| `figma-ui-generate-library` | Variables, styles, components, variants, and bindings |
| `figma-ui-design-to-code` | `get_design_context`, CSS, SVG/image export, and component mapping |
| `figma-ui-generate-diagram` | Manual diagrams using editable Figma nodes and lines |
| `figma-ui-use-motion` | Prototype reactions, Smart Animate transitions, and scroll behavior |

The following official workflows are intentionally not included because `figma-ui-mcp@2.5.26` does not provide their required backend: new-file creation, FigJam-specific authoring, Slides authoring, Code Connect publishing, generative-plugin authoring, shader authoring, and motion keyframe/timeline APIs. Do not invoke their official tool names as substitutes.

## Example prompts

```text
Create a dashboard using the existing Figma design system.

Improve the selected frame while preserving existing components.

Convert this screen to nested Auto Layout without changing its appearance.

Create a reusable Button component with size/state variants.

Audit this screen for hardcoded colors and replace them with existing variables.
```

## Troubleshooting

### `figma_status` reports no connection

Open Figma Desktop, open the target file, run the Figma UI MCP Bridge plugin, and verify that localhost access is allowed. Then call `figma_status` again. If several files are connected, choose the intended `sessionId` and pass it to every subsequent read/write call.

### A write fails or returns an unfamiliar operation error

Call `figma_docs` before retrying. Load the focused `layout`, `api`, `tokens`, or `icons` section as needed. The write sandbox is isolated per call, so redeclare helpers and re-query node IDs instead of relying on variables from an earlier call.

### The result looks wrong even though the write succeeded

Call `figma_read` with `operation: "screenshot"` on the root frame, inspect the node tree, and refine the existing nodes. Check Auto Layout, sizing modes, text wrapping, layer order, token bindings, and component usage. A successful write is not visual verification.

### Text is clipped or overflows

Use a constrained Auto Layout parent, set the text node's intended `layoutSizingHorizontal`/`layoutSizingVertical` behavior, and use `layoutAlign: "STRETCH"` when the text should wrap. Do not solve overflow by adding arbitrary fixed width.

## Security and local-only behavior

The plugin communicates with the local `figma-ui-mcp` process and its localhost bridge. It does not request a Figma API token or send document content to Figma's hosted MCP. `npx` resolves the pinned public npm package; review or vendor that dependency according to your organization's supply-chain policy.

## Source and licensing review

This release contains original skill prose and examples. It does not redistribute source code or substantial text from the upstream runtime, Figma's official MCP guide, or community skills. No repository license is declared yet, and no `NOTICE.md` is required for the current release on that basis.

The runtime dependency [`figma-ui-mcp@2.5.26`](https://www.npmjs.com/package/figma-ui-mcp) is MIT-licensed by TranHoaiHung. The official Figma guide and community material were used as conceptual references only; this plugin does not depend on Figma's official hosted MCP.
