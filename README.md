# JALA Agent Plugins

A collection of portable Agent Plugins for JALA workflows.

Figma UI plugin: [GitHub](https://github.com/Atnic/jala-agent-plugins/tree/main/figma-ui).
Gog plugin: [GitHub](https://github.com/Atnic/jala-agent-plugins/tree/main/gog).
Mattermost JALA plugin: [GitHub](https://github.com/Atnic/jala-agent-plugins/tree/main/mattermost-jala).
Matt Pocock Skills: Productivity plugin: [GitHub](https://github.com/Atnic/jala-agent-plugins/tree/main/mattpocock-skills-productivity).

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

### `mattermost-jala`

Searches messages, reads channel and thread history, looks up users and channel
members, creates channels, adds members, and posts or replies in the JALA
Mattermost workspace. The plugin bundles the endpoint and uses Mattermost OAuth
for each user's sign-in; it does not include credentials or duplicate the
server's tool definitions.

See [`mattermost-jala/README.md`](mattermost-jala/README.md) for requirements,
authentication, and installation.

### `mattpocock-skills-productivity`

A Codex plugin packaging the general workflow skills from Matt Pocock's
Productivity collection: planning interviews, handoffs, teaching,
questionnaires, plain-language explanations, and agent-facing writing.

See [`mattpocock-skills-productivity/README.md`](mattpocock-skills-productivity/README.md)
for the included skills, upstream attribution, and installation.

## Install in Claude Code

This repository also has a Claude Code marketplace at
`.claude-plugin/marketplace.json`. Add the repository, then install the plugins you want:

```bash
claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install gog@jala-agent-plugins
claude plugin install figma-ui@jala-agent-plugins
claude plugin install mattermost-jala@jala-agent-plugins
```

For a local checkout, use `claude plugin marketplace add /absolute/path/to/jala-agent-plugins`
instead. Start a new Claude Code session or run `/reload-plugins` to load the
installed components. Gog still needs the local `gog` CLI and its own account
authorization. Figma UI still needs Figma Desktop and the local bridge described
in its README. Mattermost JALA requires Mattermost OAuth sign-in; see its README
for server administrator prerequisites.

The Claude manifests omit fixed versions so Git commits provide plugin updates.

## Install in Codex

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

Use `codex plugin add figma-ui@jala-agent-plugins` for the Figma UI plugin,
`codex plugin add mattermost-jala@jala-agent-plugins` for Mattermost, and
`codex plugin add mattpocock-skills-productivity@jala-agent-plugins` for Matt
Pocock's general workflow skills.

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

Replace `gog` with `figma-ui` or `mattermost-jala` when updating those plugins.
For Matt Pocock Skills, use `mattpocock-skills-productivity`.

### From a local checkout

```bash
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin add gog@jala-agent-plugins
```

Replace `gog` with `figma-ui`, `mattermost-jala`, or
`mattpocock-skills-productivity` to install another plugin from the local
checkout.

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
plugin directory is independently installable, with host manifests and optional
skills or MCP configuration.

```text
jala-agent-plugins/
├── .agents/plugins/marketplace.json
├── .claude-plugin/marketplace.json
├── figma-ui/
├── gog/
├── mattermost-jala/
└── mattpocock-skills-productivity/
```
