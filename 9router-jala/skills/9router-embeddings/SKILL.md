---
name: 9router-embeddings
description: Generate vector embeddings via 9Router /v1/embeddings using OpenAI / Gemini / Mistral / Voyage / Nvidia / GitHub embedding models for RAG, semantic search, similarity. Use when the user requests this capability through 9Router or the configured JALA AI gateway.
---

# 9Router — Embeddings

## Gateway execution

Read [Verified JALA model defaults and live catalog](../9router/references/models.md) before selecting a model. It takes precedence over provider and model examples below. Codex, OpenAI API, and Exa connections are configured for this plugin.

The JALA gateway is **https://9router.jala.tech**. It is already deployed; do not install a server or ask users for a gateway URL. Every request requires the user's API key.

Read [credential setup and request helper](../9router/references/authentication.md) before making requests. Use the bundled `gateway.py` helper to load the key without exposing it to chat or command arguments. If no key is configured, launch `gateway.py setup-web --no-open` and open its local URL for the user to submit their key. Do not inspect the key field or capture the page while they enter it. Never ask them to paste the key into chat. The terminal `setup` fallback must be run by the user. `NINEROUTER_KEY` is an optional environment override. Do not read or display the saved credential file.

The curl/SDK examples below document endpoint shapes. Prefer the helper for execution; it uses the fixed JALA URL and authenticates discovery and inference calls. Substitute IDs and options discovered from this deployment for example models. Do not automatically repeat generation POSTs after an ambiguous timeout. This plugin supplies local scripts and REST guidance, not MCP tools or a host model-provider configuration.


Uses the hosted JALA gateway and a per-user API key. Read [9Router setup](../9router/SKILL.md) for deployment configuration and authentication.

## Discover

```bash
curl $NINEROUTER_URL/v1/models/embedding | jq '.data[].id'
# Per-model dimensions
curl "$NINEROUTER_URL/v1/models/info?id=openai/text-embedding-3-small"
```

## Endpoint

`POST $NINEROUTER_URL/v1/embeddings`

| Field | Required | Notes |
|---|---|---|
| `model` | yes | from `/v1/models/embedding` |
| `input` | yes | string OR array of strings |
| `encoding_format` | no | `float` (default) / `base64` |
| `dimensions` | no | OpenAI v3 only |

## Examples

```bash
curl -X POST $NINEROUTER_URL/v1/embeddings \
  -H "Authorization: Bearer $NINEROUTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/text-embedding-3-small","input":["hello","world"]}'
```

JS:

```js
const r = await fetch(`${process.env.NINEROUTER_URL}/v1/embeddings`, {
  method: "POST",
  headers: { "Authorization": `Bearer ${process.env.NINEROUTER_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({ model: "gemini/text-embedding-004", input: "RAG chunk text" }),
});
const { data } = await r.json();
console.log(data[0].embedding.length);  // dimension
```

## Response shape

```json
{ "object": "list", "model": "openai/text-embedding-3-small",
  "data": [
    { "object": "embedding", "index": 0, "embedding": [0.0123, -0.045, ...] },
    { "object": "embedding", "index": 1, "embedding": [...] }
  ],
  "usage": { "prompt_tokens": 5, "total_tokens": 5 } }
```

## Provider quirks

| Provider | Notes |
|---|---|
| `openai`, `openrouter`, `mistral`, `voyage-ai`, `fireworks`, `together`, `nebius`, `github`, `nvidia`, `jina-ai` | Native OpenAI shape — `dimensions` works only on OpenAI v3 (`text-embedding-3-*`) |
| `gemini`, `google_ai_studio` | Server auto-converts to `embedContent`/`batchEmbedContents` — send OpenAI shape |
| `openai-compatible-*`, `custom-embedding-*` | Custom `baseUrl` from credentials |

Batch (`input` as array) is faster; some providers cap batch size.
