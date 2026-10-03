# Learned skill template

Adapt this template; keep only sections useful to the taught task. Replace every placeholder before saving. Use ISO dates from the session's current date and quote YAML strings as needed.

```markdown
---
name: odoo-jala-<task>
description: <Task performed and when this skill applies.>
metadata:
  source-plugin: odoo-jala-web
  source-plugin-version: "0.1.0"
  created-at: "YYYY-MM-DD"
  updated-at: "YYYY-MM-DD"
---

# <Task>

## Context and inputs

Site: https://odoo.jala.tech (JALA’s Odoo 16 instance; inspect the live UI for differences). Use an available authorized browser, preferring
ChatGPT/Codex's in-app Browser. Read the active browser tool instructions.
<Starting state, company/record scope, parameters, matching rules, and prerequisites.>

## Procedure

<Taught navigation, mappings, rules, branches, and visible checkpoints.>
<Base actions on inspected current page state; resolve discrepancies before continuing.>
<Preparation and finalization boundaries. The current request supplies authorization;
the skill itself grants no permission. Follow browser confirmation/handoff requirements.>
<Inspect the result before retrying an uncertain write to avoid duplicates.>

## Completion

<Observable success checks and what to report.>

## Provenance and confidence

Created by Odoo JALA Web (`odoo-jala-web`), source version 0.1.0.
<Creation/update dates. Observed steps, trainer-described steps, untested behavior,
and unresolved details. Saving this skill does not establish production verification.>
```

Include enough browser guidance to operate independently. Discrete inspection does not imply continuous observation. Replace current transaction data with inputs; preserve reusable business rules. If information is missing, state the gap and when to ask instead of guessing. Add reference files only for substantial task-specific material.
