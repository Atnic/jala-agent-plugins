# Components and reuse

Repeated UI should be a component, not duplicated primitive geometry.

## Reuse priority

1. Existing local component.
2. Existing component variant or property combination.
3. Existing style or variable binding.
4. New reusable component.
5. Primitive nodes for one-off content.

Inspect first with `figma_read` operations such as `get_local_components`, `get_component_map`, and `get_design`. Use `figma_rules` to understand names and semantic roles.

## Creating a component

When no suitable component exists:

1. Build its container with Auto Layout.
2. Give it a semantic, project-consistent name.
3. Add text and icon children with deliberate sizing behavior.
4. Bind reusable visual properties to variables or styles.
5. Convert the complete frame with the bridge's component operation.
6. Add variants only when state, size, or intent is a real product dimension.
7. Instantiate it for every repeated use.

A button should be one component frame containing its label/icon, not a rectangle and a text sibling that happen to overlap. A card should own its internal layout and expose only the properties that consumers need to change.

## Variants and overrides

Use semantic property names such as `Size=Small`, `State=Disabled`, or `Tone=Primary` when they match the document's convention. Prefer component properties or bound text over destructive edits to instances. If the requested visual cannot be achieved by an existing variant, explain the smallest reusable extension before creating it.

## Verification

After creating or instantiating a component:

- read the component and instance nodes;
- verify names, variant properties, and variable bindings;
- verify that the instance responds to content changes without clipping;
- screenshot a representative instance in context.
