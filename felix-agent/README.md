# Felix Agent local management

A skills-only plugin for Codex and Claude Code that sets up and manages [Felix Agent](https://felix-agent.farid-inawan.dev/) locally with its [official Docker Compose starter](https://github.com/frdteknikelektro/felix-agent-starter). It helps inspect and troubleshoot deployments, configure connections, upgrade or migrate, inspect built-in skills, and create or update custom Felix skills. It does not modify built-in skills or import skills from the agent host.

Requires Git, Docker Desktop or Engine with Compose v2, and Python 3 for backups. Browser setup is preferred; the user enters credentials in Felix's setup, not in chat. The setup console's one-time link is a secret and should remain in the user's terminal. Terminal setup is a fallback. Codex Full Access is recommended when required; Claude Code has different permission controls. The plugin does not change host permissions.

New installations use `~/felix-agent` on macOS/Linux and `%USERPROFILE%\felix-agent` on Windows. For existing installations elsewhere, the skill offers a migration plan and preserves the original until verified. Before an upgrade or migration it stops Felix and creates a verified archive of `.env` only in `~/.felix-agent-backups`, retaining the latest per installation. Archives contain secrets; on Windows the user must ensure inherited ACLs protect the backup directory. Workspace data is not backed up; the Felix starter recommends backing up the complete workspace before upgrades. Archive integrity does not prove a successful restore.

The API channel uses contact identities that do not confer Owner permissions. Owner-only operations use the Owner Console where supported. A2A and task delegation are outside this plugin's scope. Supported operations depend on the deployed Felix release and host tools; the skill reports limitations instead of claiming unavailable functionality.

Register this repository as a local marketplace using the [root instructions](../README.md#from-a-local-checkout), then install `felix-agent@jala-agent-plugins` in Codex. For Claude Code, use the [Claude installation instructions](../README.md#install-in-claude-code) and install the same identifier. Local registration is required until this package is published to the GitHub branch. Start a new session and ask “Set up Felix Agent locally” or invoke `felix-agent-setup`.

Structural and skill validation do not establish host or Felix runtime compatibility. Browser setup, migration, upgrades, and Windows/Claude Code flows have not been verified end to end.
