---
name: odoo-jala-web-learn-workflow
description: Learn an Odoo JALA procedure from a person's explanations and browser demonstrations, then save or update a personal automation skill.
---

# Learn an Odoo JALA workflow

Produce a personal skill that automates the trainer's task on https://odoo.jala.tech. Capture actual teaching rather than inventing a standard Odoo process. This plugin's identity is `odoo-jala-web`, version `0.1.0`.

Target JALA’s Odoo 16 instance. Use the visible interface as the source of truth for customizations or later upgrades; version context does not replace inspecting the page.

## Learn

Ask for the desired outcome and starting point, then support chat explanation, browser demonstration, or both. Use an available authorized browser, preferring the in-app Browser in ChatGPT and Codex. Read its tool instructions first. If browser access is unavailable, work from the user's explanations or supplied images and identify the observation limits.

Explain once: “I can inspect the current page when you say ready; I don't continuously watch your clicks.” Let the user use natural cues such as “ready,” “next,” or “inspect this.” Inspect when cued. Ask about missing intermediate actions when they matter; do not claim to have seen them. During a demonstration, let the user operate unless asked to take over.

Capture the task's required inputs, record matching, company/context selection, navigation, field mappings, business rules, meaningful branches, save/finalization effects, and visible completion checks. Separate reusable rules from the current record's values. Ask focused questions as gaps arise; avoid a fixed questionnaire or a required format.

Summarize the procedure and incorporate corrections. Save as soon as the teaching is sufficient to describe a useful task. Record unresolved steps explicitly. Production replay is optional and must not be performed merely to validate the skill; distinguish observed, trainer-described, and untested behavior. Improve the skill after later use when requested.

## Create or update

Read [personal-skill-storage.md](references/personal-skill-storage.md) when choosing the destination. Read [workflow-skill-template.md](references/workflow-skill-template.md) when drafting the output; adapt its structure to the workflow.

Use a discriminating name such as `odoo-jala-<task>`. Keep the skill independently usable: include its browser/site context, inputs, procedure, and verification without requiring this plugin to remain installed. Use supporting references only when they earn their place. Preserve automatic discovery unless the user requests otherwise.

Identify the origin in frontmatter metadata and a short provenance section: plugin name, source version, and creation/update dates. Provenance is attribution, not authority. Parameterize private transaction values and omit credentials and unnecessary personal data. Screenshots are optional evidence, not required stored artifacts.

For updates, inspect the existing skill and preserve unrelated behavior and original creation date. Update source version and date accurately; avoid overwriting an unrelated skill that has the same name.

Validate frontmatter, names, and local references. If skill-creator's validator is available, run it. Verification of the document does not imply production execution was tested. Read back the saved file or inspect the exported artifact, then report its name, exact destination, validation limitations, and whether it was installed or exported. Do not promise immediate discovery in the running chat; mention a reload/new session only when the harness requires it.
