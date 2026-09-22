# JALA Agent Plugins

A collection of portable Agent Plugins for JALA workflows.

## Plugins

### `figma-ui`

Local Figma authoring through [`figma-ui-mcp`](https://github.com/TranHoaiHung/figma-ui-mcp), with skills for:

- Auto Layout and HUG/FILL/FIXED sizing
- reusable components and variants
- variables, tokens, and design systems
- container-first screen generation
- iterative screenshot verification
- design-to-code extraction from local Figma files
- diagrams built from editable Figma nodes
- prototype interactions and scroll behavior

See [`figma-ui/README.md`](figma-ui/README.md) for requirements and installation.

## Repository layout

The root repository is a plugin collection, not itself a plugin. Each top-level plugin directory is independently installable and owns its own `plugin.json`, MCP configuration, and skills. New sibling plugins can be added later without changing the `figma-ui` plugin contract.

```text
jala-agent-plugins/
├── figma-ui/
├── another-plugin/
└── another-plugin-2/
```
