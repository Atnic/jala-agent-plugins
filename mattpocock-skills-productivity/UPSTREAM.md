# Upstream snapshot

- Repository: <https://github.com/mattpocock/skills>
- Source directory: `skills/productivity/`
- Commit: `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`
- License: MIT; full notice is in [LICENSE.mattpocock](LICENSE.mattpocock)

This plugin copies the upstream Productivity skills into a single Codex
`skills/` root. The copy keeps each skill's `SKILL.md`, supporting Markdown
files, and `agents/openai.yaml` metadata. It does not use symlinks.
Claude-specific `disable-model-invocation` frontmatter was removed from the
Codex copies; the corresponding Codex invocation rules remain in
`agents/openai.yaml`.

To refresh the snapshot, copy the contents of a newer upstream
`skills/productivity/` directory into this plugin's `skills/` directory and
remove any Claude-specific `disable-model-invocation` fields from the
`SKILL.md` frontmatter again. Keep the Codex invocation rules in
`agents/openai.yaml`. Then update the commit above and review the included
skill inventory and upstream license. The plugin manifests intentionally use
the same plain SemVer version; do not add a cachebuster suffix to only one
manifest.
