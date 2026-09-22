# Tokens and semantic layers

## Discovery before creation

Use `figma_rules` and `figma_read` operations such as `get_variables`, `get_styles`, and `get_local_components` before adding a token. Search by semantic role and by likely primitive value. A token that looks unused may be bound to a component or a hidden library example.

## Suggested baseline

When no design system exists, a modest spacing baseline can start at:

```text
4, 8, 12, 16, 24, 32, 40, 48
```

This is only a fallback. Do not replace an existing system with it.

Token categories commonly worth centralizing:

- color roles and state colors;
- spacing and component padding;
- corner radius;
- typography roles;
- control dimensions where the system relies on them;
- effects such as shadows when supported.

## Semantic naming

Prefer purpose over raw value:

```text
primitive/color/blue/500
semantic/color/action/primary
component/button/primary/background
```

Use the project's established naming convention if it differs. A semantic token should communicate where and why it is used, not merely which hex value it currently contains.

## Bind, then verify

It is acceptable for a create operation to need a temporary literal before the variable binding is applied. The reusable result must end with the intended variable or style binding. Read the component or node afterward and verify the binding rather than trusting the write response.
