---
name: 9router
description: Connect to and discover the hosted JALA 9Router gateway and route requests to its bundled capability skills. Use when the user mentions 9Router, NINEROUTER_URL, or asks to use the JALA AI gateway.
---

# 9Router

## Gateway execution

Read [Verified JALA model defaults and live catalog](../9router/references/models.md) before selecting a model. It takes precedence over provider and model examples below. Codex, OpenAI API, and Exa connections are configured for this plugin.

The JALA gateway is **https://9router.jala.tech**. It is already deployed; do not install a server or ask users for a gateway URL. Every request requires the user's API key.

Read [credential setup and request helper](../9router/references/authentication.md) before making requests. Use the bundled `gateway.py` helper to load the key without exposing it to chat or command arguments. If no key is configured, launch `gateway.py setup-web --no-open` and open its local URL for the user to submit their key. Do not inspect the key field or capture the page while they enter it. Never ask them to paste the key into chat. The terminal `setup` fallback must be run by the user. `NINEROUTER_KEY` is an optional environment override. Do not read or display the saved credential file.

The curl/SDK examples below document endpoint shapes. Prefer the helper for execution; it uses the fixed JALA URL and authenticates discovery and inference calls. Substitute IDs and options discovered from this deployment for example models. Do not automatically repeat generation POSTs after an ambiguous timeout. This plugin supplies local scripts and REST guidance, not MCP tools or a host model-provider configuration.


Local/remote AI gateway exposing OpenAI-compatible REST. One key, many providers, auto-fallback.

## Setup

Use the [credential setup guide](references/authentication.md). The gateway URL
is fixed to `https://9router.jala.tech`; the helper attaches the user's saved key.
The `NINEROUTER_URL` variable in upstream examples means this hosted base URL.
Use `gateway.py request /v1/models` to verify authenticated access.

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

When the user needs a specific capability, read the bundled skill below:

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

- 401 → set/refresh `NINEROUTER_KEY` (Dashboard → Keys)
- 400 `Invalid model format` → check `model` exists in `/v1/models/<kind>`
- 503 `All accounts unavailable` → wait `retry-after` or add another provider account
