# JALA Agent Plugins

A collection of portable Agent Plugins for JALA workflows.

Figma UI plugin: [GitHub](https://github.com/Atnic/jala-agent-plugins/tree/main/figma-ui).
Gog plugin: [GitHub](https://github.com/Atnic/jala-agent-plugins/tree/main/gog).

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

### `gog`

Google Workspace work through the local [`gog`](https://github.com/openclaw/gogcli)
CLI. This skills-only plugin covers Google services and common cross-service
workflows. Accounts remain managed by `gog` locally; the plugin does not use
MCP or Codex's Connected accounts UI.

See [`gog/README.md`](gog/README.md) for setup and the skill inventory.

## Install from the GitHub marketplace

This repository includes a Codex marketplace catalog at
`.agents/plugins/marketplace.json`. It is a repository marketplace, not a listing in
the public GitHub Marketplace.

### From GitHub

Add the repository as a marketplace, then install the plugin you want:

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin list
codex plugin add gog@jala-agent-plugins
```

Use `codex plugin add figma-ui@jala-agent-plugins` for the Figma UI plugin.

The repository URL must point to the repository itself. Do not use a GitHub `/tree/`
URL. The `--ref main` option pins the marketplace snapshot to the `main` branch.
For a private repository, authenticate GitHub when prompted and make sure the
account has read access.

After installation, restart the Codex desktop app or start a new task so the
installed plugin components are loaded. When a plugin is updated, refresh the
marketplace and reinstall that plugin:

```bash
codex plugin marketplace upgrade jala-agent-plugins
codex plugin add gog@jala-agent-plugins
```

Replace `gog` with `figma-ui` when updating that plugin.

### From a local checkout

```bash
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin add gog@jala-agent-plugins
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

The root repository is a plugin collection, not itself a plugin. Each top-level
plugin directory is independently installable and owns its own `plugin.json`
and skills. Plugins that need MCP also include their own MCP configuration.

```text
jala-agent-plugins/
├── .agents/plugins/marketplace.json
├── figma-ui/
└── gog/
```
