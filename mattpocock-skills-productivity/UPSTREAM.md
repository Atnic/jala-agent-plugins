# Upstream snapshot

- Repository: <https://github.com/mattpocock/skills>
- Source directory: `skills/productivity/`
- Release: `v1.3.2`
- Commit: `d1478fcb140db0b93c0c8df17bcfd311844749d0`
- License: MIT; full notice is in [LICENSE.mattpocock](LICENSE.mattpocock)

This plugin copies the upstream Productivity skills into a single Codex
`skills/` root. The copy keeps each skill's `SKILL.md`, supporting Markdown
files, and `agents/openai.yaml` metadata. It does not use symlinks.
Claude-specific `disable-model-invocation` frontmatter was removed from the
Codex copies; the corresponding Codex invocation rules remain in
`agents/openai.yaml`.

JALA adapts `grill-with-docs`, `domain-modeling`, `research`,
`to-spec`, `wayfinder`, `to-tickets`, and `retro` from the Engineering collection at `v1.3.2` (commit `d1478fcb140db0b93c0c8df17bcfd311844749d0`).
These skills use general project language and are maintained locally alongside the
upstream Productivity snapshot.

To refresh the snapshot, copy the contents of a newer upstream
`skills/productivity/` directory into this plugin's `skills/` directory,
preserving the local adaptations listed above. Remove any Claude-specific `disable-model-invocation` fields from the
`SKILL.md` frontmatter again. Keep the Codex invocation rules in
`agents/openai.yaml`. Then update the commit above and review the included
skill inventory and upstream license. The plugin manifests intentionally use
the same plain SemVer version; do not add a cachebuster suffix to only one
manifest.
