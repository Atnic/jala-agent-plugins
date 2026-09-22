# Diagram notation

Before writing nodes, establish a small notation table:

| Meaning | Node/edge treatment |
| --- | --- |
| Primary action or service | Filled semantic card |
| Decision or branching condition | Distinct shape or titled card |
| Data store | Data-store shape or clearly labeled card |
| External system | Boundary or muted card |
| Synchronous call | Solid directed line |
| Asynchronous event | Dashed directed line |
| Error or exception | Warning/error token from the local system |

Use the existing file's visual language when one exists. Otherwise keep the palette small and define it in a legend. Labels should name the thing and, when useful, the operation or event; avoid paragraphs inside nodes.

## Layout contract

- Root frame: fixed canvas size appropriate to the diagram.
- Groups: Auto Layout where their children flow in one dimension.
- Nodes: semantic frames with HUG content and bounded widths.
- Long descriptions: separate notes or detail cards with constrained wrapping.
- Connectors: non-layout overlay with explicit line geometry.
