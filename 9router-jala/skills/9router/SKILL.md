---
name: 9router
description: Entry point for 9Router — local/remote AI gateway with OpenAI-compatible REST for chat, image, TTS, embeddings, web search, web fetch. Use when the user mentions 9Router, NINEROUTER_URL, or wants AI without writing provider boilerplate. This skill covers setup + indexes capability skills; read the relevant bundled capability skill below when needed.
---

# 9Router

Local/remote AI gateway exposing OpenAI-compatible REST. One key, many providers, auto-fallback.

## Setup

The JALA gateway is already deployed at `https://9router.jala.tech`; do not
install a server or ask for a gateway URL. API keys are supplied by the JALA admin.

Before executing any capability, read [credentials and helper](references/authentication.md)
and [JALA model defaults](references/models.md). Use the bundled
`gateway.py run <skill> --body request.json` to apply the fixed URL, saved key,
configured models, live catalog checks, and TTS/Exa translations. Resolve the
helper at `<plugin-root>/scripts/gateway.py` from this skill's installation path.
If no key is configured, launch `setup-web --no-open` and open its local URL
for the user; never inspect the key field or ask for the key in chat.

The JALA defaults and helper take precedence over generic setup, provider, and
model examples in capability skills. `NINEROUTER_URL` below means the hosted
JALA URL. Use `gateway.py request` for discovery. Do not automatically repeat
generation POSTs after an ambiguous failure.

## Discover models

```bash
curl $NINEROUTER_URL/v1/models                  # chat/LLM (default)
curl $NINEROUTER_URL/v1/models/image            # image-gen
curl $NINEROUTER_URL/v1/models/tts              # text-to-speech
curl $NINEROUTER_URL/v1/models/embedding        # embeddings
curl $NINEROUTER_URL/v1/models/web              # web search + fetch (entries have `kind` field)
curl $NINEROUTER_URL/v1/models/stt              # speech-to-text
curl $NINEROUTER_URL/v1/models/image-to-text    # vision
```

Use `data[].id` as `model` field in requests. Combos appear with `owned_by:"combo"`.

Response shape:
```json
{ "object": "list", "data": [
  { "id": "openai/gpt-5", "object": "model", "owned_by": "openai", "created": 1735000000 },
  { "id": "tavily/search", "object": "model", "kind": "webSearch", "owned_by": "tavily", "created": 1735000000 }
]}
```

## Capability skills

When the user needs a specific capability, read its bundled skill for endpoint
shapes and response handling, retaining the JALA setup and model defaults above:

| Capability | Bundled skill |
|---|---|
| Chat / code-gen | [9router-chat](../9router-chat/SKILL.md) |
| Image generation | [9router-image](../9router-image/SKILL.md) |
| Text-to-speech | [9router-tts](../9router-tts/SKILL.md) |
| Speech-to-text | [9router-stt](../9router-stt/SKILL.md) |
| Embeddings | [9router-embeddings](../9router-embeddings/SKILL.md) |
| Web search | [9router-web-search](../9router-web-search/SKILL.md) |
| Web fetch (URL → markdown) | [9router-web-fetch](../9router-web-fetch/SKILL.md) |

## Errors

- 401 → run `gateway.py setup-web` with an admin-provided key
- 400 `Invalid model format` → check `model` exists in `/v1/models/<kind>`
- 503 `All accounts unavailable` → wait `retry-after` or add another provider account
