# JALA Agent Plugins

A collection of portable Agent Plugins for JALA workflows.

- [9Router JALA](9router-jala/README.md)
- [App Store Connect](app-store-connect/README.md)
- [Crisp JALA](crisp-jala/README.md)
- [Felix Agent](felix-agent/README.md)
- [Figma UI](figma-ui/README.md)
- [Gog](gog/README.md)
- [Google Play Console](google-play-console/README.md)
- [Matt Pocock Skills: Engineering](mattpocock-skills-engineering/README.md)
- [Matt Pocock Skills: Productivity](mattpocock-skills-productivity/README.md)
- [Mattermost JALA](mattermost-jala/README.md)
- [Metabase JALA](metabase-jala/README.md)
- [Microsoft Office](microsoft-office-addin/README.md)
- [Odoo JALA Web](odoo-jala-web/README.md)
- [Odoo JALA XML-RPC](odoo-jala-xmlrpc/README.md)
- [Scheduler](scheduler/README.md)

## Plugins

### `9router-jala`

Use the hosted JALA 9Router gateway for chat, image generation, speech,
embeddings, web search, and URL extraction. This skills package bundles the
upstream entry point, a Codex provider setup skill, and seven capability skills
with minimal JALA setup adaptations for Codex and Claude Code. It requires Python
3.9+, `keyring`, and a per-user API key entered through a local HTML setup form,
saved in macOS Keychain, Windows Credential Manager, or Linux Secret Service.
The optional `9router-setup` skill also writes provider settings to Codex
`config.toml`, where its API key is stored in plaintext; restart Codex to apply it.

See [`9router-jala/README.md`](9router-jala/README.md) for setup, attribution,
and installation of the local unpublished package.

### `app-store-connect`

Use agent instructions and a Python REST CLI for App Store Connect. The agent looks up current endpoint details in Apple's documentation. The plugin supports team and individual API keys, stores credentials only in the OS secret store, and requires local browser approval for high-impact production changes.

Individual purchase and refund evidence uses a separate, read-only App Store Server API connection with verified signed payloads.

See [`app-store-connect/README.md`](app-store-connect/README.md) for both setup flows, key permissions, report downloads, and CLI usage.

### `crisp-jala`

REST API skills for JALA Crisp conversations, messages, people profiles, visitors,
workspace settings, campaign templates, and analytics. Bundles the base Crisp
skill and JALA credential overlay for Codex and Claude Code. Setup opens Crisp for user login, captures the session credential from an inbox
request, and saves it in the OS secret store. Requires Python 3.9+ and browser
network inspection. Credentials load automatically for subsequent requests.

See [`crisp-jala/README.md`](crisp-jala/README.md) for setup and local installation.

### `felix-agent`

Set up and manage a local Felix Agent deployment, connections, and custom skills. Requires Git, Docker Compose v2, Python 3 for backups, and interactive setup. See [setup](felix-agent/README.md).

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

### `google-play-console`

Manage Play Console apps through one named, typed MCP action per published operation in Android Publisher v3 and Play Developer Reporting v1beta1/v1alpha1. The current catalog contains 195 actions. Use guided workflows for releases, listings, reviews, monetization, access, and analytics. The plugin supports Google user OAuth and optional service accounts, stores credentials only in the OS secret store, and marks edit commits and other high-impact writes for host approval.

See [`google-play-console/README.md`](google-play-console/README.md) for setup, permissions, Codex approval configuration, and catalog updates.

### `mattermost-jala`

Searches messages, reads channel and thread history, looks up users and channel
members, creates channels, adds members, and posts or replies in the JALA
Mattermost workspace. The plugin bundles the endpoint and uses Mattermost OAuth
for each user's sign-in; it does not include credentials or duplicate the
server's tool definitions.

See [`mattermost-jala/README.md`](mattermost-jala/README.md) for requirements,
authentication, and installation.

### `mattpocock-skills-engineering`

A Codex plugin packaging 20 engineering skills from Matt Pocock's collection,
including planning, implementation, testing, issue triage, and code review.

See [`mattpocock-skills-engineering/README.md`](mattpocock-skills-engineering/README.md)
for the skill inventory, setup requirements, upstream attribution, and installation.

### `mattpocock-skills-productivity`

A Codex plugin packaging the general workflow skills from Matt Pocock's
Productivity collection: planning interviews, handoffs, teaching,
questionnaires, plain-language explanations, and agent-facing writing.

See [`mattpocock-skills-productivity/README.md`](mattpocock-skills-productivity/README.md)
for the included skills, upstream attribution, and installation.

### `metabase-jala`

Connect Codex and Claude Code to JALA’s shared Metabase instance through its
built-in MCP server. OAuth calls run as the signed-in Metabase user and follow
that account’s permissions. The plugin exposes content and query tools,
including SQL where the account and database connection allow it; user, group,
and permission administration are outside its scope.

See [`metabase-jala/README.md`](metabase-jala/README.md) for installation,
OAuth sign-in, and Metabase prerequisites.

### `microsoft-office-addin`

Includes chat inside the Office pane with a project folder picker, saved conversations, streamed replies,
activity, and approvals through a local Codex CLI.

Connects Codex to open Excel, Word, and PowerPoint documents through a local
Office.js task pane. The package includes a local HTTPS bridge and stdio MCP
tools for listing connected panes and running a requested JavaScript body in a
selected document.

See [`microsoft-office-addin/README.md`](microsoft-office-addin/README.md) for local setup,
sideloading, supported hosts, and script execution limits.

### `odoo-jala-web`

Automate browser tasks on JALA’s Odoo 16 instance and learn reusable personal workflows from chat explanations and browser demonstrations.

See [`odoo-jala-web/README.md`](odoo-jala-web/README.md) for browser requirements, personal skill storage, and export behavior.

### `odoo-jala-xmlrpc`

Query JALA Odoo records and inspect fields through a read-only XML-RPC Python
client. Record changes and workflow actions are disabled. Discover visible installed addons
and schemas, with a source-backed guide to JALA's custom Finance workflows.
Requires Python 3.9+, an Odoo
login, and an API key or password entered through a local setup page; the JALA
database defaults to `jala_production`. Saved connections load automatically; native credential storage uses
`keyring`, with a private-file fallback when unavailable.

See [`odoo-jala-xmlrpc/README.md`](odoo-jala-xmlrpc/README.md) for authentication,
request examples, and installation.

### `scheduler`

Schedule, list, edit, or stop a prompt in an existing ChatGPT/Codex desktop or
Claude session. Desktop uses the available same-chat automation tool directly;
Claude uses guarded hooks and a latest-only catch-up runner. No provider setup
is required. Prerequisites and catch-up guarantees depend on the backend; see
[setup and verified coverage](scheduler/README.md).

## Install in Claude Code

This repository also has a Claude Code marketplace at
`.claude-plugin/marketplace.json`. Add the repository, then install the plugins you want:

```bash
claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install 9router-jala@jala-agent-plugins
claude plugin install app-store-connect@jala-agent-plugins
claude plugin install crisp-jala@jala-agent-plugins
claude plugin install felix-agent@jala-agent-plugins
claude plugin install figma-ui@jala-agent-plugins
claude plugin install gog@jala-agent-plugins
claude plugin install google-play-console@jala-agent-plugins
claude plugin install mattermost-jala@jala-agent-plugins
claude plugin install metabase-jala@jala-agent-plugins
claude plugin install odoo-jala-web@jala-agent-plugins
claude plugin install odoo-jala-xmlrpc@jala-agent-plugins
claude plugin install scheduler@jala-agent-plugins
```

For a local checkout, use `claude plugin marketplace add /absolute/path/to/jala-agent-plugins`
instead. Start a new Claude Code session or run `/reload-plugins` to load the
installed components. Gog still needs the local `gog` CLI and its own account
authorization. Figma UI still needs Figma Desktop and the local bridge described
in its README. Mattermost JALA requires Mattermost OAuth sign-in; see its README
for server administrator prerequisites.
9Router JALA needs Python 3.9+, `keyring`, and a per-user API key; see its README for setup.
Odoo JALA XML-RPC needs Python 3.9+ and local Odoo connection setup; its helper installs native credential-store dependencies. See its README for setup and fallback storage details.

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
codex plugin add app-store-connect@jala-agent-plugins
codex plugin add crisp-jala@jala-agent-plugins
codex plugin add felix-agent@jala-agent-plugins
codex plugin add figma-ui@jala-agent-plugins
codex plugin add gog@jala-agent-plugins
codex plugin add google-play-console@jala-agent-plugins
codex plugin add mattermost-jala@jala-agent-plugins
codex plugin add mattpocock-skills-engineering@jala-agent-plugins
codex plugin add mattpocock-skills-productivity@jala-agent-plugins
codex plugin add metabase-jala@jala-agent-plugins
codex plugin add microsoft-office-addin@jala-agent-plugins
codex plugin add odoo-jala-web@jala-agent-plugins
codex plugin add odoo-jala-xmlrpc@jala-agent-plugins
codex plugin add scheduler@jala-agent-plugins
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
| `app-store-connect` | Python 3.9+, `pip` and network access for the first runtime install, App Store Connect API access and a team or individual `.p8` key; individual transaction reads additionally require an In-App Purchase key with matching issuer and app identifiers, plus Keychain, Windows Credential Manager, or Linux Secret Service; see [setup](app-store-connect/README.md). |
| `crisp-jala` | Python 3.9+, native OS secret store, and browser network inspection for login-session capture; see [setup](crisp-jala/README.md). |
| `felix-agent` | Docker Engine or Desktop with Compose v2, Git, Python 3 for backups, and interactive Felix setup. See [setup](felix-agent/README.md). |
| `figma-ui` | Figma Desktop and the local bridge; see [setup](figma-ui/README.md). |
| `gog` | Local `gog` CLI and Google account authorization; see [setup](gog/README.md). |
| `google-play-console` | Python 3.9+, `pip` and network access for the first runtime install, a Google Cloud Desktop OAuth client JSON file or optional service-account JSON, Play Console API permissions, and Keychain, Windows Credential Manager, or Linux Secret Service; see [setup](google-play-console/README.md). |
| `mattermost-jala` | Mattermost OAuth sign-in and server prerequisites; see [setup](mattermost-jala/README.md). |
| `mattpocock-skills-engineering` | Set up the target repository and issue tracker; see the [skill inventory and setup](mattpocock-skills-engineering/README.md). |
| `mattpocock-skills-productivity` | See the [skill inventory and usage](mattpocock-skills-productivity/README.md). |
| `metabase-jala` | Network access, a Metabase MCP-enabled JALA instance, and per-user Metabase OAuth sign-in; see [setup](metabase-jala/README.md). |
| `microsoft-office-addin` | Local Codex session and Node.js 20.19.0+; ask Codex to set up the localhost certificate and Office add-in pane on macOS, Windows, or Office on the web on Linux. See [setup](microsoft-office-addin/README.md). |
| `odoo-jala-web` | An available browser capability and Odoo sign-in; see [setup](odoo-jala-web/README.md). The plugin does not install Browser itself. |
| `odoo-jala-xmlrpc` | Python 3.9+, shell execution, and a connection saved through its local setup page; native credential storage uses `keyring`, with private-file fallback. See [setup](odoo-jala-xmlrpc/README.md). No MCP server. |
| `scheduler` | Desktop: same-chat automation tool. Claude: native CLI/CronCreate, Python 3.11+ runtime and live hooks. See [backend requirements](scheduler/README.md). |

For Odoo JALA Web, start with “Learn this workflow” or invoke
`$odoo-jala-web-learn-workflow`. Generated personal skills are stored separately
from the plugin, using the active harness's personal skill directory when
available, with an export fallback otherwise.

### Update a plugin

MCP server identifiers now use underscores. Plugin installation identifiers
remain the same. The affected server identifiers are:

| Previous server key | Current server key |
| --- | --- |
| `figma-ui-mcp` | `figma_ui_mcp` |
| `google-play-console` | `google_play_console` |
| `mattermost-jala` | `mattermost_jala` |
| `metabase-jala` | `metabase_jala` |
| `microsoft-office-addin` | `microsoft_office_addin` |

After updating or reinstalling an affected plugin, restart the host and start
a fresh session to check tool availability. Update any server-specific config
to use the new key, including Google Play's
[per-tool approval entries](google-play-console/codex-high-impact-approvals.toml).
Mattermost and Metabase OAuth connections are managed by the host; sign in
again if prompted after the key change. App Store Connect and Google Play use
their existing plugin-managed native credential stores, whose identifiers
are unchanged. Tool availability after this rename still needs runtime
verification in the host.

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
├── app-store-connect/
├── crisp-jala/
├── felix-agent/
├── figma-ui/
├── gog/
├── google-play-console/
├── mattermost-jala/
├── mattpocock-skills-engineering/
├── mattpocock-skills-productivity/
├── metabase-jala/
├── microsoft-office-addin/
├── odoo-jala-web/
├── odoo-jala-xmlrpc/
└── scheduler/
```
