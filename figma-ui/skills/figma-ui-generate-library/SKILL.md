---
name: figma-ui-generate-library
description: Create or evolve Figma variables, design tokens, styles, components, variants, and reusable design-system foundations through figma-ui-mcp.
---

# figma-ui-generate-library

Use this skill when creating or maintaining a Figma design system: variables, tokens, styles, components, variants, reusable patterns, or documentation examples. Also load `figma-ui-use` so all discovery, session, and write calls use the local `figma-ui-mcp` runtime.

## Core principle

The design system is the source of truth. Inspect and extend it before creating new values. Existing project conventions always outrank the defaults in these references.

## Workflow

Follow this sequence:

```text
inspect existing system
↓
variables/tokens
↓
styles
↓
components
↓
variants/properties
↓
bindings
↓
documentation/examples
↓
validate
```

### 1. Inspect existing system

Call `figma_status`, then `figma_docs` and `figma_rules`. Use `figma_read` to inspect:

- variables and collections;
- local paint, text, and effect styles;
- local components and component sets;
- representative screens and existing library pages;
- naming conventions and modes.

Do not assume that a missing visual value is truly missing until variables, styles, and components have been searched.

### 2. Variables before components

Create or update variables and semantic tokens before building components that consume them. Use semantic layering where the document supports it:

```text
primitive
↓
semantic
↓
component
```

Example:

```text
blue/500
↓
color/action/primary
↓
Button/Primary background
```

This lets a rebrand or mode change happen at the semantic layer instead of requiring every component to be redrawn.

### Recoverable token bootstrap

Token bootstrap is a staged write, not an all-or-nothing transaction. `setupDesignTokens` may create variables successfully and then fail while creating a text style, especially when a requested font family or weight is unavailable in the connected Figma session.

- After any bootstrap error, read variables and styles before retrying.
- Preserve successful variables and complete only the missing styles or modes with supported low-level operations.
- Verify the actual font family and weight after creating or applying a text style. If the requested weight cannot load, use a verified available weight and report the fallback instead of silently claiming the requested style exists.
- Keep each repair bounded and read it back before proceeding to component work.

### 3. Styles and bindings

Reuse existing text, paint, and effect styles. For new reusable properties, bind the component to variables or styles using the actual helper operations documented by `figma_docs`. Do not leave a temporary literal in a reusable component simply because the first create call accepted it.

### 4. Components and variants

Build components with Auto Layout, semantic names, and a small, intentional property surface. Add variants for real product dimensions such as size, state, or tone. Avoid variant explosion and do not encode unrelated content as a variant.

Instantiate new components in a representative example so that the library is tested in use. Preserve existing component names and properties when evolving a library.

### 5. Documentation and examples

Document token roles, component anatomy, supported properties, and examples in the conventions already used by the file. Keep visual reference pages separate from the actual variable/style source of truth when that is the project's existing pattern.

### 6. Validate

Read variables, styles, component metadata, and representative instances again. Screenshot the library or example frame. Check:

- token values and modes are correct;
- semantic names are consistent;
- components are bound to variables/styles;
- variants are selectable and not duplicated;
- instances reflow without clipping;
- no orphaned or accidental primitives were introduced.

## Safety rules

- Never overwrite an existing variable, style, or component merely because its name is similar; inspect identity and usage first.
- Never impose the default 4/8/12/16/24/32/40/48 spacing scale on a file with an existing spacing system.
- Prefer modifying an existing library node over creating a parallel duplicate.
- Make changes in bounded writes and re-query IDs between calls.
- Do not use official hosted Figma MCP tools or assume their response shapes.
- Do not declare success without a read-back and screenshot of a representative result.
- Do not rerun a failed bootstrap blindly when the bridge may have partially mutated the document.

## References

- [Tokens](references/tokens.md)
- [Variables](references/variables.md)
- [Components](references/components.md)
- [Naming](references/naming.md)
