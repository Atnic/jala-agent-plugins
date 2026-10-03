# Odoo JALA Web — design interview

## Agreed direction

- Plugin display name: Odoo JALA Web; proposed identifier: `odoo-jala-web`.
- Target: https://odoo.jala.tech through ChatGPT's in-app browser.
- Teaching combines chat explanations and browser demonstrations.
- Make observation boundaries explicit: the agent inspects discrete browser states, and must not imply it continuously watches the trainer's actions.
- Learned skills are intended for the person teaching them, rather than shared plugin distribution.
- The teaching output is a flexible task-specific automation skill, saved to the current harness's normal personal skill location when writable. For Codex, follow skill-creator's `$CODEX_HOME/skills` or `~/.codex/skills` convention. Determine other harness locations from their supported conventions before writing.
- Generated skills must identify Odoo JALA Web as their origin, and remain outside installed plugin caches and shared plugin source.
- Save immediately without requiring production replay. Record what was observed, trainer-confirmed, and untested; refine through later use.
- Teaching uses simple readiness prompts, such as “ready” or “inspect this,” with explicit inspection rather than assumed continuous observation.
- Capture the full procedure and distinguish preparation from finalization. Each execution needs authorization from the current request; the saved skill is not standing authorization.

## Final decisions

- Install in the active harness's personal skill store when supported; export a portable skill otherwise, clearly distinguishing export from installation.
- Two general skills: `odoo-jala-web-use` and `odoo-jala-web-learn-workflow`.
- Keep plugin skills and examples department-neutral.
- User confirmed this scope on 2026-10-03; implementation may proceed.
