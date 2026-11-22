# GLOSSARY.md Format

## Structure

```md
# {Context Name}

{One or two sentence description of what this context is and why it exists.}

## Language

**Order**:
{A one or two sentence description of the term}
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account
```

## Rules

- **Be opinionated.** When multiple words exist for the same concept, pick the best one and list the others under `_Avoid_`.
- **Keep definitions tight.** One or two sentences max. Define what it IS, not what it does.
- **Only include terms specific to this project's context.** Include terms that have a specific meaning in this project. Skip ordinary terms used in their usual sense.
- **Group terms under subheadings** when natural clusters emerge. If all terms belong to a single cohesive area, a flat list is fine.

## Single vs multi-context projects

**Single context (most projects):** One `GLOSSARY.md` at the project root.

**Multiple contexts:** A `GLOSSARY-MAP.md` at the project root lists the contexts, where they live, and how they relate to each other:

```md
# Glossary Map

## Contexts

- [Ordering](./ordering/GLOSSARY.md): receives and tracks customer orders
- [Billing](./billing/GLOSSARY.md): generates invoices and processes payments
- [Fulfillment](./fulfillment/GLOSSARY.md): manages warehouse picking and shipping

## Relationships

- **Ordering → Fulfillment**: Ordering tells Fulfillment when an order is ready to pick
- **Fulfillment → Billing**: Fulfillment confirms shipment so Billing can issue an invoice
- **Ordering ↔ Billing**: Both use the same customer identifiers and currency
```

The skill infers which structure applies:

- If `GLOSSARY-MAP.md` exists, read it to find contexts
- If only a root `GLOSSARY.md` exists, single context
- If neither exists, create a root `GLOSSARY.md` lazily when the first term is resolved

When multiple contexts exist, infer which one the current topic relates to. If unclear, ask.
