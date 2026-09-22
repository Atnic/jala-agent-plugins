# Diagram patterns

## Flowchart and architecture

Use a left-to-right root Auto Layout where possible. Group related nodes in labeled frames, keep edges in a non-layout overlay, and use a consistent start/action/decision/end vocabulary. Architecture diagrams should distinguish compute, data, external systems, and asynchronous transports by shape or tokenized color.

## Sequence diagram

Create an actor column for each participant. Use a vertical lifeline and place message lines in time order. Keep the message label near the line, and use a separate note/card for annotations that would make the edge unreadable.

## State diagram

Use one card per state and labeled line edges for events or guards. Make the initial and terminal states visually distinct. Avoid placing all states in a single Auto Layout row when the transition paths need a two-dimensional layout; use grouped regions and manual top-level placement for the state cards, with a connector overlay.

## ER diagram

Use a component-like entity card with a header and field rows. Mark primary and foreign keys using the existing text/icon conventions. Keep relationship labels near the edge midpoint and include cardinality only when the source data supports it.

## Gantt or timeline

Create a fixed time-axis header and a vertical work-item list. Use tokenized bars and milestone markers. If exact dates are unknown, show relative phases rather than fabricating calendar values.
