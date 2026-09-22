# Diagram verification

After writing a diagram, verify both the data model and the visual artifact.

## Structural checks

- Every requested entity, actor, state, task, or service exists once.
- Every requested relationship or transition has a visible edge.
- Labels use semantic names and do not contain default layer names.
- Groups and legends explain any non-obvious notation.
- Existing nodes retain their IDs and component bindings when edited.

## Visual checks

- No node or label is clipped.
- Edges do not hide text or cross unrelated groups unnecessarily.
- Direction markers and line styles communicate the intended relationship; inspect their separate vector/shape nodes when the API does not provide arrow/dash properties on lines.
- Spacing and alignment are consistent.
- The diagram fits the root frame and remains readable at a useful zoom.

If a line is ambiguous, read the node geometry and adjust the smallest set of line coordinates. Screenshot again before declaring completion.
