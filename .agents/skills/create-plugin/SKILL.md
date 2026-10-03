---
name: create-plugin
description: Create a plugin in this repository, including its host packaging, marketplace registration, documentation, and validation.
---

# Create plugin

Produce a complete, reviewable plugin in this repository. Keep changes in the working tree; commit, push, install, or publish when requested.

## 1. Establish the package

Inspect repository instructions, working-tree status, catalogs, and comparable plugins. Read repository identity and conventions from their maintained sources. Resolve purpose, identifier, supported hosts, components, tools, and prerequisites; ask only for missing decisions. Handle an existing destination as an explicit update.

**Done:** destination, hosts, components, and dependencies are known; unrelated changes are preserved.

## 2. Author

Read [packaging](references/packaging.md) when selecting manifests, components, and catalog entries. Consult official host documentation when examples leave compatibility uncertain. Use `skill-creator` when available. Create only components and resources needed by the request. Describe required tools accurately: guidance alone does not install execution capabilities.

**Done:** requested components exist, manifests agree, and host packaging and prerequisites are accounted for.

## 3. Brand when applicable

Read [branding](references/branding.md) when preparing or reviewing assets. Use supplied or verified official artwork and inspect the rendered result. Without suitable artwork, omit optional asset fields and report the limitation.

**Done:** declared assets exist and have been inspected; preview limitations are recorded.

## 4. Register and document

Register the plugin once in each selected host's catalog. Preserve existing entries. Write its README and update the root inventory, layout, installation references, and prerequisites. Verify unfamiliar commands against current CLI help or official documentation. Distinguish published Git sources from local unpublished changes.

**Done:** catalog sources resolve to the package and documentation covers every selected host.

## 5. Validate and deliver

Run `python3 <this-skill>/scripts/validate_plugin.py <plugin-directory>` from the repository. Use `--repo-root <root>` for another repository or isolated fixture. Run available skill-format and host checks separately; the structural validator does not parse skill YAML or certify host compatibility. Correct failures within scope.

Report package name, version, checks, runtime limitations, and how to try it.

**Done:** structural checks pass and remaining compatibility or execution uncertainty is explicit.
