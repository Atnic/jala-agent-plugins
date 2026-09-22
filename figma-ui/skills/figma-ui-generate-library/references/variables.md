# Variables and modes

## Variable-first sequence

1. Read collections, variables, types, and modes.
2. Reuse an existing variable when its semantic role matches.
3. Create a collection or variable only when the role is genuinely new.
4. Add or update modes deliberately.
5. Bind component properties and representative instances.
6. Read back the values and bindings.

The local runtime exposes variable operations through `figma_read` and `figma_write`; the exact argument names are versioned, so call `figma_docs` before authoring.

## Primitive and semantic values

Keep primitive values separate from semantic aliases when the document supports aliasing. For example:

```text
Primitive: blue/500 = #2563EB
Semantic: color/action/primary → blue/500
Component: Button/Primary/fill → color/action/primary
```

Do not bind every component directly to a raw primitive if a semantic role already exists. A component should express intent so themes and modes can evolve safely.

## Modes

When the file supports multiple modes such as light/dark or compact/comfortable:

- inspect existing mode names and values;
- add values consistently across modes;
- avoid creating a mode that only partially covers a component's needs;
- validate both modes with representative screenshots.

## Verification query

After binding, read the variable collection and a representative node. Confirm the variable ID, resolved mode/value, and component property are the expected ones. A literal fill that visually matches today is not proof of a binding.
