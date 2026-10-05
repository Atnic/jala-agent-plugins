# Upstream snapshot

- Repository: <https://github.com/mattpocock/skills>
- Source directory: `skills/engineering/`
- Release: `v1.3.1`
- Commit: `24fe0ef7737efae15c87225755e9f6f5965e4888`
- License: MIT; full notice is in [LICENSE.mattpocock](LICENSE.mattpocock)

This plugin copies all 20 upstream Engineering skills and their supporting
files into one Codex `skills/` root. It retains `SKILL.md`, reference material,
scripts, and `agents/openai.yaml` metadata. Claude-specific
`disable-model-invocation` frontmatter is removed from the Codex copies; the
matching Codex invocation policies remain in `agents/openai.yaml`.

Some Engineering skills route to skills in the separate Productivity
collection. Install `mattpocock-skills-productivity` as well to make those
routes available.

To refresh the snapshot, copy the contents of a newer upstream
`skills/engineering/` directory into this plugin's `skills/` directory and
remove Claude-specific `disable-model-invocation` fields from `SKILL.md`
frontmatter. Keep the Codex invocation rules in `agents/openai.yaml`, update the
commit above, and review the skill inventory and upstream license.
