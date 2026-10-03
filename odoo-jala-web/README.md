# Odoo JALA Web

Browser workflows for JALA’s **Odoo 16** instance at https://odoo.jala.tech and a teaching flow that creates personal automation skills.

The plugin uses scalable Odoo wordmarks served by this Odoo instance:
`/web/static/img/odoo_logo.svg` and `/web/static/img/odoo_logo_dark.svg`.
Local copies are in `assets/odoo-logo.svg` and `assets/odoo-logo-dark.svg`.
Plugin display assets center the unchanged wordmark on a padded 512×512 canvas,
with a white variant for dark mode.
The original favicon is also preserved in `assets/odoo-jala-favicon.ico`.

## Skills

- `odoo-jala-web-use`: execute Odoo tasks with available personal workflows.
- `odoo-jala-web-learn-workflow`: capture explanations and browser demonstrations, then save a reusable personal skill.

Teaching uses natural readiness cues. The agent inspects discrete browser states; it does not continuously watch the user's actions. Learned skills are saved immediately with observation and testing limits, without requiring a production replay.

## Requirements

An authorized browser tool and the user's Odoo access. Prefer ChatGPT/Codex's in-app Browser; other harnesses need their own supported browser capability. This skills-only plugin does not bundle Browser, credentials, or authentication. Actual availability depends on the host.

## Personal output

Codex skills go to `$CODEX_HOME/skills` or `~/.codex/skills`; Claude Code skills go to `~/.claude/skills`, subject to active configuration. Other hosts use their supported personal storage. Without native installation access, the agent exports the skill and clearly reports that it is not installed.

Generated skills identify `odoo-jala-web` and its version as their origin. Personal skills stay outside the shared plugin and its installed cache. Their procedures do not grant standing authorization to change Odoo records.

## Installation

Use the repository marketplace instructions in [the root README](../README.md) with plugin identifier `odoo-jala-web`. Codex and Claude Code manifests are included. For ChatGPT, use the host's supported plugin import; native personal skill installation is capability-dependent, with export as the fallback.

Example prompts:

- “Use Odoo JALA Web to help me complete this task.”
- “Learn this workflow. I'll explain it and show you the steps.”
- “Update my saved workflow with this changed rule.”
