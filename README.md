# JALA Agent Plugins

A collection of portable Agent Plugins for JALA workflows.

- [9Router JALA](9router-jala/README.md)
- [Figma UI](figma-ui/README.md)
- [Gog](gog/README.md)
- [Mattermost JALA](mattermost-jala/README.md)
- [Matt Pocock Skills: Productivity](mattpocock-skills-productivity/README.md)
- [Odoo JALA Web](odoo-jala-web/README.md)

## Plugins

### `9router-jala`

Use the hosted JALA 9Router gateway for chat, image generation, speech,
embeddings, web search, and URL extraction. This skills-only package bundles the
unchanged upstream entry point and its seven linked capability skills, plus a
JALA wrapper skill, for Codex and Claude Code. It requires Python 3.9+, `keyring`, and a per-user API key entered through a local
HTML setup form, saved in macOS Keychain, Windows Credential Manager, or Linux Secret Service.

See [`9router-jala/README.md`](9router-jala/README.md) for setup, attribution,
and installation of the local unpublished package.

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

### `odoo-jala-web`

Automate browser tasks on JALA’s Odoo 16 instance and learn reusable personal workflows from chat explanations and browser demonstrations.

See [`odoo-jala-web/README.md`](odoo-jala-web/README.md) for browser requirements, personal skill storage, and export behavior.

## Install in Claude Code

This repository also has a Claude Code marketplace at
`.claude-plugin/marketplace.json`. Add the repository, then install the plugins you want:

```bash
claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install 9router-jala@jala-agent-plugins
claude plugin install figma-ui@jala-agent-plugins
claude plugin install gog@jala-agent-plugins
claude plugin install mattermost-jala@jala-agent-plugins
claude plugin install odoo-jala-web@jala-agent-plugins
```

For a local checkout, use `claude plugin marketplace add /absolute/path/to/jala-agent-plugins`
instead. Start a new Claude Code session or run `/reload-plugins` to load the
installed components. Gog still needs the local `gog` CLI and its own account
authorization. Figma UI still needs Figma Desktop and the local bridge described
in its README. Mattermost JALA requires Mattermost OAuth sign-in; see its README
for server administrator prerequisites.
9Router JALA needs Python 3.9+, `keyring`, and a per-user API key; see its README for setup.

Some older Claude manifests omit fixed versions so Git commits provide plugin
updates; newer packages declare a version matching their portable manifest.

## Install in Codex

This repository includes a Codex marketplace catalog at
`.agents/plugins/marketplace.json`. It is a repository marketplace, not a listing in
the public GitHub Marketplace.

### Prerequisites

Use a Codex CLI version that supports `codex plugin`. Check with:

```bash
codex plugin --help
```

### From GitHub

Register the marketplace and inspect the available plugins:

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin marketplace list
codex plugin list --marketplace jala-agent-plugins --available --json
```

Install the plugins you want; each command below installs one plugin:

```bash
codex plugin add 9router-jala@jala-agent-plugins
codex plugin add figma-ui@jala-agent-plugins
codex plugin add gog@jala-agent-plugins
codex plugin add mattermost-jala@jala-agent-plugins
codex plugin add mattpocock-skills-productivity@jala-agent-plugins
codex plugin add odoo-jala-web@jala-agent-plugins
```

The repository URL must point to the repository itself. Do not use a GitHub
`/tree/` URL. `--ref main` selects the Git branch to fetch. For a private
repository, make sure your Git credentials have read access.

GitHub installation uses the published `main` branch. To try a new plugin or
changes that have not been pushed there, use the local checkout instructions.

### From a local checkout

Register the absolute path to this repository, then install the desired plugin:

```bash
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin list --marketplace jala-agent-plugins --available --json
codex plugin add odoo-jala-web@jala-agent-plugins
```

Replace `odoo-jala-web` with any plugin identifier in the GitHub installation
list. If you already registered the GitHub marketplace with the same name,
remove that registration before adding the local source:

```bash
codex plugin marketplace remove jala-agent-plugins
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
```

### Load and verify

After installation, restart the Codex desktop app or start a new task so its
installed components are loaded. Check the CLI's installed plugin list:

```bash
codex plugin list --marketplace jala-agent-plugins --json
```

Complete the selected plugin's requirements:

| Plugin | Requirements |
| --- | --- |
| `9router-jala` | Python 3.9+, `keyring`, and a per-user API key; native saved-key support on macOS/Windows/Linux; see [setup](9router-jala/README.md). |
| `figma-ui` | Figma Desktop and the local bridge; see [setup](figma-ui/README.md). |
| `gog` | Local `gog` CLI and Google account authorization; see [setup](gog/README.md). |
| `mattermost-jala` | Mattermost OAuth sign-in and server prerequisites; see [setup](mattermost-jala/README.md). |
| `mattpocock-skills-productivity` | See the [skill inventory and usage](mattpocock-skills-productivity/README.md). |
| `odoo-jala-web` | An available browser capability and Odoo sign-in; see [setup](odoo-jala-web/README.md). The plugin does not install Browser itself. |

For Odoo JALA Web, start with “Learn this workflow” or invoke
`$odoo-jala-web-learn-workflow`. Generated personal skills are stored separately
from the plugin, using the active harness's personal skill directory when
available, with an export fallback otherwise.

### Update a plugin

For a GitHub marketplace, fetch its latest snapshot and reinstall the plugin:

```bash
codex plugin marketplace upgrade jala-agent-plugins
codex plugin add odoo-jala-web@jala-agent-plugins
```

For a local marketplace, reinstall after editing the checkout:

```bash
codex plugin add odoo-jala-web@jala-agent-plugins
```

Replace `odoo-jala-web` with the plugin you are updating, then restart the app
or start a new task to load the updated components.

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
├── 9router-jala/
├── figma-ui/
├── gog/
├── mattermost-jala/
├── mattpocock-skills-productivity/
└── odoo-jala-web/
```
