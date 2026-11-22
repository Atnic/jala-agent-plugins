---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the project. Use when the user wants a topic researched, facts gathered from original documents, or reading legwork delegated to a background agent.
---

Spin up a **background agent** to do the research, so you keep working while it reads. Start it with a fresh context window. If you are already the assigned research agent or background agents are unavailable, do the research directly.

Its job:

1. Investigate the question against **primary sources** (official documents, original data, published policies, first-party records), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it to the destination supplied by the caller or where the project already keeps research notes. If neither is available, use `docs/research/<topic>.md` and report the path.
