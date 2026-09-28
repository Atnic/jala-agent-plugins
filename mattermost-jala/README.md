# Mattermost JALA

Search messages, read channel and thread history, look up teams, users, and
channel members, create channels, add users to channels, and post or reply in
JALA Mattermost. The MCP server enforces each signed-in user's Mattermost
permissions.

This is an MCP-only plugin. It adds no `SKILL.md`; tool definitions and actions
come directly from the Mattermost MCP server.

## Requirements

- A Mattermost account on `mattermost.jala.tech`.
- The external Mattermost MCP HTTP endpoint enabled by a Mattermost
  administrator.
- OAuth 2.0 enabled in Mattermost. Dynamic client registration (DCR) should be
  enabled for automatic client setup; otherwise an administrator must register
  an OAuth client for the host.

The plugin includes the fixed JALA MCP endpoint. It stores no Mattermost
credentials. After installation, sign in through the host's MCP OAuth flow.

## Install in Claude Code

From the repository marketplace:

```bash
claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install mattermost-jala@jala-agent-plugins
```

For a local checkout, replace the repository argument with its absolute path.
Approve the MCP server connection, then sign in to Mattermost when prompted.

## Install in Codex

From the repository marketplace:

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin add mattermost-jala@jala-agent-plugins
```

For a local checkout:

```bash
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin add mattermost-jala@jala-agent-plugins
```

Restart Codex or start a new task after installation, then complete Mattermost
OAuth sign-in when prompted.

## Configuration and permissions

The Codex portable MCP configuration is in `mcp.json`; Claude Code uses
`.mcp.json`. Both point to the JALA Mattermost MCP endpoint. The MCP server
controls its tool catalog and applies Mattermost permissions to each user.
The plugin does not filter the MCP tool catalog: hosts receive the tools
provided by Mattermost. The available actions and the signed-in user's access
are governed by Mattermost's server configuration and permissions.

No access token, personal access token, or client secret belongs in this
plugin. If OAuth sign-in is unavailable, ask a Mattermost administrator to
check the external MCP, OAuth service provider, and dynamic client registration
settings.
