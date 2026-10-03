# gog

`gog` is a portable Agent Plugin for Google Workspace tasks through the locally
installed [gog CLI](https://gogcli.sh/) ([source](https://github.com/openclaw/gogcli)).
It contains agent skills only: no MCP server, hosted app, or OAuth integration
is bundled. Google accounts are connected and selected in `gog`, not in Codex's
Connected accounts section.

The plugin icon uses Gog's [official favicon](https://gogcli.sh/favicon.svg).

This JALA plugin packages 33 skills: the shared `gog` skill, the `gog-setup` onboarding
skill, the `gog-clean` authentication cleanup skill, service skills for
Gmail, Drive, Docs, Sheets, Calendar and other Google services, plus workflow
skills for inbox triage, meeting preparation, attachment handling, Drive
audits, weekly digests, and contact cleanup. The skills are adapted from
[`openclaw/gogcli`](https://github.com/openclaw/gogcli)
under its MIT license; see [LICENSE.gogcli](LICENSE.gogcli).

## Requirements

- An Agent Plugins-compatible host with shell command access.
- `gog` installed on the same machine and available to the host's command path.
- A Google Cloud OAuth client and at least one Google account authorized through
  `gog` for the services you want to use.

The shared skill tells the agent to inspect the installed CLI's help and schema
before use because commands can change.

## Set up `gog`

Ask your agent to **set up Gog** or invoke `$gog-setup`. It installs the CLI
for future chats, asks for your Google email, accepts an uploaded client JSON
or local path, and verifies authorization. Company accounts can reuse the
client provided by IT.

The [setup skill](skills/gog-setup/SKILL.md) owns installation, account routing,
and platform-specific service defaults. macOS/Linux use standard full access;
Windows uses the employee service set, including Forms, to reduce credential
storage size. The skill contains the exact service list and commands.

For manual setup, follow the [official install guide](https://github.com/openclaw/gogcli/blob/main/docs/install.md)
and [quickstart](https://github.com/openclaw/gogcli/blob/main/docs/quickstart.md).
When you need to create or repair an OAuth project, use the
[Google Cloud preparation reference](skills/gog-setup/references/google-cloud.md).
Installation and stored authorization persist across chats under the same OS
user on the machine running Gog.

## Remove local authentication

Ask the agent to clean Gog authentication or invoke `$gog-clean`. It lists local
profiles and clients, clarifies which to remove, and checks which accounts a
client deletion would disconnect. Cleanup removes local authorization; Google
accounts and Workspace data remain intact.

## Install the plugin

### Claude Code

```bash
claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install gog@jala-agent-plugins
```

For a local checkout, add its absolute path as the marketplace source instead.
Start a new Claude Code session or run `/reload-plugins` to load the skills.
The Claude marketplace entry is in
[`../.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json).
The local `gog` installation and account setup above are required for either host.

### Codex

From this repository's GitHub marketplace:

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin add gog@jala-agent-plugins
```

Or add a local checkout as a marketplace and install `gog@jala-agent-plugins`.
Start a new Codex task after installing so its skills are loaded. The marketplace
entry is in [`../.agents/plugins/marketplace.json`](../.agents/plugins/marketplace.json).

## How it works

```text
Agent → gog skills → local gog CLI → Google Workspace APIs
```

The skills favor structured JSON, explicit account selection, live CLI schema
discovery, bounded reads, and inspection of the exact target before writes.
Upstream service skills retain their `agents/openai.yaml` metadata. The
unrelated upstream `crabbox` skill is not included.

This plugin is developed by JALA and is not an official Google or OpenClaw
product.
