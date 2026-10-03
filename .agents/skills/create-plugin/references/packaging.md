# Packaging

Read the current catalogs and a plugin with comparable components instead of copying a frozen manifest template. Retrieve repository identity from Git. Consult official host documentation for unsupported or uncertain fields.

## Components and hosts

Every package has root `plugin.json`. Skills live under `skills/<skill-name>/SKILL.md`; use lowercase hyphenated names and YAML frontmatter containing `name` and `description`. Keep supporting material behind pointers that state when to read it.

Package Codex compatibility under `.codex-plugin/plugin.json` and Claude Code compatibility under `.claude-plugin/plugin.json` only for selected hosts. Match their names and versions to the portable manifest. A Codex skills package declares its skills directory. Host support requires the appropriate component configuration, not merely a manifest.

MCP-only packages are valid. Use root `.mcp.json` or an explicit `mcpServers` file/inline configuration supported by the host. Include only identified servers and actual transport configuration. Keep secrets outside the package; document authentication and installation prerequisites. The validator checks configuration structure and paths, not connectivity.

New packages start at `0.1.0`. For updates, inspect that plugin's release history and conventions; keep versions consistent wherever they are specified. Some legacy Claude manifests omit versions: inspect compatibility requirements before changing that convention.

## Registration

A present compatibility manifest declares that host as selected. Register Codex packages in the repository's Codex catalog and Claude packages in its Claude catalog. Read their current locations and formats from the root README and catalog files. Each selected catalog needs one matching entry with a source resolving to the package root. Preserve unrelated registrations and policies.

Author/display metadata comes from the request and repository conventions. Optional visual assets and capabilities must describe the actual package. Review README prerequisites and installation instructions alongside the manifests.

## Structural validator

The validator supports conventional `skills/`, a declared `skills` path, root `.mcp.json`, and explicit `mcpServers` paths or inline server maps. Local paths stay within the plugin; catalog sources stay within the repository. Remote catalog sources are outside this local creation workflow. Unsupported declarations should be resolved against official host documentation rather than worked around merely to pass validation.

A pass establishes local consistency only. Run available skill YAML validators and host schema checks separately, and report any unavailable checks.
