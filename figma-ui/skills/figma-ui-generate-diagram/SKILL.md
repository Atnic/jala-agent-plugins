---
name: figma-ui-generate-diagram
description: Create or update editable flowcharts, architecture diagrams, sequence diagrams, state diagrams, ER diagrams, and timelines in an existing Figma file through figma-ui-mcp.
---

# figma-ui-generate-diagram

Use this skill when the user wants a diagram in Figma. Load `figma-ui-use` first. This is a local-bridge adaptation of diagram guidance: it assembles editable Figma frames, text, vectors, and lines through `figma_write`. It does not call an official `generate_diagram` tool, create a FigJam file, or render Mermaid automatically.

## Scope and supported forms

The skill can build or update:

- flowcharts, decision trees, and process flows;
- architecture diagrams with services, queues, stores, and integrations;
- sequence diagrams for actors and time-ordered messages;
- ER diagrams for entities, fields, keys, and relationships;
- state diagrams and state machines;
- Gantt charts and timelines.

The diagram is placed in the currently connected Figma file. This skill composes diagrams from generic Figma nodes; the bridge does not provide diagram-specific layout or FigJam-native connector routing. Plan and position edges explicitly. Do not promise automatic edge attachment or Mermaid fidelity.

## Workflow

### 1. Discover

Call `figma_status`, select the target session, then call `figma_docs`, `figma_rules`, and `figma_read` for the current page or selected diagram. Reuse the document's tokens, typography, components, and naming conventions.

If the subject matter is ambiguous, ask for the missing entities, actors, steps, or relationships before drawing. Do not invent edges merely to make the diagram look complete.

### 2. Choose a diagram grammar

Route the request to one of the supported forms. Define node types, edge meaning, direction, grouping, and label rules before creating nodes. For example:

```text
Architecture: left → right; services as cards; stores as distinct shapes
Sequence: actors as columns; messages as ordered horizontal lines
State: states as cards; transitions as labeled arrows
ERD: entities as stacked-field cards; relations as labeled lines
Gantt: time axis; work items as rows; milestones as markers
```

Use semantic IDs and names. Keep labels short enough to fit their intended boxes; use a detail panel or notes section for long explanations.

### 3. Build containers first

Create the root diagram frame, title/legend, swimlanes or groups, and node shells before adding leaf text. Use Auto Layout for repeated cards and lists. Keep connectors in a dedicated non-layout overlay layer so lines can cross between groups without disrupting flow layout.

### 4. Create nodes, then edges

Create all stable nodes first and record their IDs. Add labels and fields, then create lines after node geometry is known. The documented `LINE` create shape exposes position, width/height, stroke, and stroke weight; it does not document connector routing, arrowhead, or dashed-line properties. Do not pass guessed arrow/dash fields. If direction or edge type matters, check the current `figma_docs` API; when no such property is documented, draw direction markers as separate supported `VECTOR`/shape nodes or communicate the distinction with labels and the legend. For custom paths, use only the documented vector path operations and syntax.

### 5. Read and refine

Read the resulting tree and screenshot the root. Check that every requested node and edge exists, labels are readable, lines do not cross important text, groups are aligned, and the diagram has enough whitespace. Modify existing nodes or line positions instead of rebuilding the entire diagram.

## Diagram-specific guardrails

- Never use emoji as node labels or icons.
- Never invent entities, states, services, or edges absent from the source context.
- Keep the semantic layer separate from connector geometry.
- Do not put crossing or overlapping connector lines inside an Auto Layout parent.
- Draw connectors after nodes so their coordinates are based on final node geometry.
- Treat all edges as manually positioned geometry; re-check endpoints after node movement or resizing.
- Do not assume line nodes attach to nodes, route around obstacles, or render arrowheads/dashes automatically.
- Use an explicit legend when colors or line styles carry meaning.
- For an existing diagram, preserve node identity and update only the requested content.
- Do not call `generate_diagram`, `create_new_file`, `get_figjam`, or `use_figma` as substitutes for the local runtime.

## References

- [Diagram patterns](references/diagram-patterns.md)
- [Notation](references/notation.md)
- [Verification](references/verification.md)
