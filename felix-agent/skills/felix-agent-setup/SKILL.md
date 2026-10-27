---
name: felix-agent-setup
description: Set up, manage, troubleshoot, upgrade, or migrate a local Felix Agent installation; configure its connections or inspect and create Felix custom skills.
---

# Felix Agent local management

Use this skill for local Felix Agent on macOS, Linux, or Windows, in Codex or Claude Code. It requires shell, Git, Docker and Compose; browser access is needed for the preferred setup. This skill does not install these capabilities. For Codex, remind the user that Full Access is recommended if it is not enabled or cannot be established; continue if existing permissions suffice. Claude Code has different permissions: explain the required filesystem, Docker and network access without equating its bypass mode with Codex Full Access. Never change host permission settings yourself.

Find the existing installation before creating another. The standard location is `~/felix-agent` on macOS/Linux and `%USERPROFILE%\felix-agent` on Windows. Check that path and identify running Felix Compose projects via Docker metadata without printing environment variables. If several candidates exist, ask which to use. Never overwrite an existing path or silently move an installation. For an installation elsewhere, offer a migration; follow [lifecycle](references/lifecycle.md) before moving it. If the user declines, use it in place.

For first-time setup, follow [setup](references/setup.md). For status, troubleshooting, upgrades, backups and migration, follow [lifecycle](references/lifecycle.md). For connections, the API channel and Felix skills, follow [capabilities](references/capabilities.md). Read the official starter README and relevant upstream documentation for the installed release before applying a procedure; do not assume the latest source matches the installed image.

Keep `.env`, workspace contents, authentication tokens and raw logs out of chat and tool output. Have the user enter secrets directly into Felix's own local interface. Do not weaken Felix authorization, silently change its network exposure, or claim an action succeeded without checking its result.
