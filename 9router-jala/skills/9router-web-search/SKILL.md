---
name: 9router-web-search
description: Web and X search via 9Router /v1/search using Tavily / Exa / Brave / Serper / SearXNG / Google PSE / Linkup / SearchAPI / You.com / Perplexity / Xquik. Use when the user requests this capability through 9Router or the configured JALA AI gateway.
---

# 9Router — Web Search

## Gateway execution

Read [Verified JALA model defaults and live catalog](../9router/references/models.md) before selecting a model. It takes precedence over provider and model examples below. Codex, OpenAI API, and Exa connections are configured for this plugin.

The JALA gateway is **https://9router.jala.tech**. It is already deployed; do not install a server or ask users for a gateway URL. Every request requires the user's API key.

Read [credential setup and request helper](../9router/references/authentication.md) before making requests. Use the bundled `gateway.py` helper to load the key without exposing it to chat or command arguments. If no key is configured, launch `gateway.py setup-web --no-open` and open its local URL for the user to submit their key. Do not inspect the key field or capture the page while they enter it. Never ask them to paste the key into chat. The terminal `setup` fallback must be run by the user. `NINEROUTER_KEY` is an optional environment override. Do not read or display the saved credential file.

The curl/SDK examples below document endpoint shapes. Prefer the helper for execution; it uses the fixed JALA URL and authenticates discovery and inference calls. Substitute IDs and options discovered from this deployment for example models. Do not automatically repeat generation POSTs after an ambiguous timeout. This plugin supplies local scripts and REST guidance, not MCP tools or a host model-provider configuration.


Uses the hosted JALA gateway and a per-user API key. Read [9Router setup](../9router/SKILL.md) for deployment configuration and authentication.

## Discover

```bash
curl $NINEROUTER_URL/v1/models/web | jq '.data[] | select(.kind=="webSearch") | .id'
# Per-provider params (searchTypes, maxResults, required options like cx for google-pse)
curl "$NINEROUTER_URL/v1/models/info?id=tavily/search"
```

IDs end in `/search` (e.g. `tavily/search`). Combos (`owned_by:"combo"`) chain providers with auto-fallback.

The live catalog ID is `exa/search`; the request endpoint expects
`model: "exa"`. Use the helper `run` command to apply this translation.

## Endpoint

`POST $NINEROUTER_URL/v1/search`

| Field | Required | Notes |
|---|---|---|
| `model` (or `provider`) | yes | from `/v1/models/web` (e.g. `tavily` or `brave`) |
| `query` | yes | search query |
| `max_results` | no | default 5 |
| `search_type` | no | `web` (default) / `news` / `x` for Xquik |
| `country`, `language`, `time_range`, `domain_filter` | no | provider-dependent |

## Examples

```bash
curl -X POST $NINEROUTER_URL/v1/search \
  -H "Authorization: Bearer $NINEROUTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"tavily","query":"9Router open source","max_results":5}'
```

JS:

```js
const r = await fetch(`${process.env.NINEROUTER_URL}/v1/search`, {
  method: "POST",
  headers: { "Authorization": `Bearer ${process.env.NINEROUTER_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({ model: "search-combo", query: "latest LLM benchmarks", max_results: 10 }),
});
console.log(await r.json());
```

X search with Xquik:

```bash
curl -X POST $NINEROUTER_URL/v1/search \
  -H "Authorization: Bearer $NINEROUTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"xquik","query":"from:github release","max_results":10,"provider_options":{"queryType":"Latest"}}'
```

Add the Xquik API key in 9Router's provider settings. Xquik charges 1 credit per returned post. Continue a search by passing `pagination.next_cursor` as `provider_options.cursor`.

Xquik responses include provider pagination and credit usage:

```json
{
  "pagination": { "has_more": true, "next_cursor": "cursor-2" },
  "usage": { "queries_used": 1, "search_cost_usd": null, "provider_credits_used": 10 }
}
```

## Response shape

```json
{
  "provider": "tavily",
  "query": "9Router open source",
  "results": [
    {
      "title": "...", "url": "https://...", "display_url": "github.com/...",
      "snippet": "...", "position": 1, "score": 0.92,
      "published_at": null, "favicon_url": null, "content": null,
      "metadata": { "author": null, "language": null, "source_type": null, "image_url": null },
      "citation": { "provider": "tavily", "retrieved_at": "2026-...", "rank": 1 }
    }
  ],
  "answer": null,
  "usage": { "queries_used": 1, "search_cost_usd": 0.008 },
  "metrics": { "response_time_ms": 850, "upstream_latency_ms": 700, "total_results_available": 12 },
  "errors": []
}
```

## Provider quirks

All accept `query` + `max_results`. Optional fields vary:

| Provider | Supports | Required extras |
|---|---|---|
| `tavily` | country, domain_filter, news topic | — |
| `exa` | domain_filter (incl/excl), news category | — |
| `brave-search` | country, language | — |
| `serper` | country, language, news endpoint | — |
| `perplexity` | country, language, domain_filter | — |
| `linkup` | domain_filter, time_range | `depth: fast/standard/deep` (option) |
| `google-pse` | country, language, time_range, offset | **`cx` required** (providerOptions) |
| `searchapi` | country, language, pagination | — |
| `youcom` | country, language, time_range, domain_filter, full_page | — |
| `searxng` | language, time_range | Self-hosted, **noAuth** |
| `xquik` | X/Twitter search operators, language, cursor pagination | `queryType: Latest/Top`, `cursor` (options) |

Provider IS the model — `"provider":"tavily" ≡ "model":"tavily"`.
