# JALA Agent Plugins

A collection of portable Agent Plugins for JALA workflows.

Figma UI plugin: [GitHub](https://github.com/Atnic/jala-agent-plugins/tree/main/figma-ui).

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
- prototype interactions and scroll behavior when exposed by the connected bridge, with static-state fallbacks when they are unavailable

See [`figma-ui/README.md`](figma-ui/README.md) for requirements and installation.

## Install from the GitHub marketplace

This repository includes a Codex marketplace catalog at
`.agents/plugins/marketplace.json`. It is a repository marketplace, not a listing in
the public GitHub Marketplace.

### From GitHub

Add the repository as a marketplace, then install the plugin:

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin list
codex plugin add figma-ui@jala-agent-plugins
```

The repository URL must point to the repository itself. Do not use a GitHub `/tree/`
URL. The `--ref main` option pins the marketplace snapshot to the `main` branch.
For a private repository, authenticate GitHub when prompted and make sure the
account has read access.

After installation, restart the Codex desktop app or start a new task so the plugin's
skills and MCP server are loaded. When the plugin is updated, refresh the marketplace
and reinstall the plugin:

```bash
codex plugin marketplace upgrade jala-agent-plugins
codex plugin add figma-ui@jala-agent-plugins
```

### From a local checkout

```bash
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin add figma-ui@jala-agent-plugins
```

### Workspace import

Workspace administrators can import the same marketplace from
`Workspace settings → Plugins → Add → Import marketplace`:

- Repository: `https://github.com/Atnic/jala-agent-plugins`
- Path: `.agents/plugins`
- Branch: `main`

The importing GitHub account must be able to read the repository. Workspace
marketplaces sync daily, and administrators can also trigger a manual sync.

## Repository layout

The root repository is a plugin collection, not itself a plugin. Each top-level plugin directory is independently installable and owns its own `plugin.json`, MCP configuration, and skills. New sibling plugins can be added later without changing the `figma-ui` plugin contract.

```text
jala-agent-plugins/
├── .agents/plugins/marketplace.json
├── figma-ui/
├── another-plugin/
└── another-plugin-2/
```
