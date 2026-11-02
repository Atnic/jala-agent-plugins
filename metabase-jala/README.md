# Metabase JALA

Connect Codex and Claude Code to the shared JALA Metabase instance at
`https://metabase.jala.tech` through Metabase’s built-in remote MCP server.
This connection-only package uses the built-in server and ships without
additional JALA workflow instructions.

**Version:** `0.1.2`

## What it can do

The MCP server provides the content, data browsing, and query tools that the
signed-in user and the instance administrator have enabled. This includes
working with questions, dashboards, and collections, and running queries,
including SQL where authorized. Available tools can change with the Metabase
version and group-level MCP tool settings.

Tool calls use the signed-in Metabase account. Metabase permissions and
instance-level MCP tool access determine which content and query tools are
available. SQL capability also depends on the permissions of the database
connection used by Metabase. Metabase’s SQL tool can overwrite or delete data
or saved content when that connection role permits it. User and group
administration, memberships, and permission changes are outside this version’s
supported scope.
Write calls follow the normal approval flow in Codex or Claude Code.

## Requirements

- The JALA Metabase instance must have its MCP server enabled under
  **Admin → AI → MCP**. Metabase’s AI features must also be enabled.
- MCP tools can be restricted by Metabase group. If a needed tool is missing,
  ask the administrator to review **Admin → AI → Usage controls → MCP tools access**.
- Users need network access to Metabase and an account with the required
  permissions.

Metabase documents the MCP endpoint and OAuth sign-in in its
[MCP server guide](https://www.metabase.com/docs/latest/ai/mcp), with the tool
catalog and group-level tool settings in its
[MCP tools guide](https://www.metabase.com/docs/latest/ai/mcp-tools).

## Install

### Codex

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin add metabase-jala@jala-agent-plugins
```

### Claude Code

```bash
claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install metabase-jala@jala-agent-plugins
```

For an unpublished local checkout, follow the repository’s
[local marketplace instructions](../README.md#install-in-codex).

## Connect to Metabase

1. Enable the plugin in Codex or Claude Code.
2. When the host opens the Metabase sign-in flow, sign in with your JALA
   Metabase account and approve the connection.
3. Start a new task or session if the MCP tools do not appear immediately.

Metabase provides OAuth discovery and client registration. The plugin does not
store passwords, API keys, or OAuth tokens. Each person signs in separately;
Metabase evaluates their permissions on tool calls.

## Verify the connection

- In Claude Code, run `/mcp` and check that `metabase_jala` is connected.
- In Codex, restart the app or start a new task after installation, then ask it
  to find a question or list accessible dashboards.
- If the server connects but a tool is missing, ask the Metabase administrator
  to check **Admin → AI → Usage controls → MCP tools access** and the user’s
  Metabase permissions.

## References

- [Metabase MCP server](https://www.metabase.com/docs/latest/ai/mcp)
- [Metabase MCP server tools](https://www.metabase.com/docs/latest/ai/mcp-tools)
- [Codex plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Claude Code plugin MCP servers](https://code.claude.com/docs/en/mcp#plugin-provided-mcp-servers)

## Logo

The padded light and dark icons use Metabase’s official dotted mark from the
[Metabase v0.63.15.2 source](https://github.com/metabase/metabase/blob/v0.63.15.2/resources/frontend_client/app/assets/img/logo.svg).
The unmodified source is kept at `assets/metabase-logo-original.svg`.
