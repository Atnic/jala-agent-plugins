# Personal skill storage

Identify the active harness from trusted session context and available tools. Use its documented personal skill location. Filesystem access in an execution environment alone does not prove access to the user's permanent skill store.

- **Codex:** use `$CODEX_HOME/skills/<skill-name>/` when CODEX_HOME is set; otherwise `~/.codex/skills/<skill-name>/`. Follow available skill-creator instructions.
- **Claude Code:** use `~/.claude/skills/<skill-name>/` for personal skills, subject to active harness configuration. For another Claude surface, establish its supported destination rather than assuming Claude Code storage exists.
- **Other harnesses:** use a known supported personal destination. Ask for a destination only if native installation is possible but its location is unresolved.
- **No writable personal store:** create a downloadable folder or ZIP containing `<skill-name>/SKILL.md` and any references. Use an available artifact/export capability. If none exists, provide the complete file content and save instructions, and state that no file was installed.

Keep generated skills outside plugin caches, this plugin's source, and shared repository skill folders. Create the destination without replacing unrelated files. If a matching personal skill exists, inspect it and update only within the requested scope.

After a native write, read the file back and report its resolved absolute path. For exports, link the actual artifact and say “exported, not installed.” A sandbox artifact or download is not native installation.
