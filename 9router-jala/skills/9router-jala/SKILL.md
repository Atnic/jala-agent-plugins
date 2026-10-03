---
name: 9router-jala
description: Set up credentials, discover models, and execute chat, image, audio, embeddings, or Exa web requests through the hosted JALA 9Router gateway. Use when the user asks to use JALA 9Router or configure its admin-provided API key.
---

# JALA 9Router

## Setup and execution

The gateway is already deployed at `https://9router.jala.tech`. Users receive
API keys from the JALA administrator. This plugin calls the gateway; it does
not deploy a server or change the harness model configuration.

1. Read [credentials and request helper](references/authentication.md) for
   runtime prerequisites, setup, or authentication failures. Resolve the plugin
   root from this skill's location; it contains `scripts/gateway.py`.
2. If no key is configured, launch `gateway.py setup-web --no-open` and open
   its printed local URL for the user. Keep the server running while the user
   enters the key. Do not inspect or capture the key field or ask for the key
   in chat. Users operate the hidden terminal `setup` fallback themselves.
3. Read [JALA models and execution examples](references/models.md) to select
   the configured capability/default. Use `gateway.py run <skill> --body
   request.json`, with the options that capability requires. The helper loads
   credentials internally and validates the live model catalog before inference.
4. Read the relevant bundled upstream skill below for endpoint shapes and
   response handling. For JALA requests, use this wrapper's hosted URL,
   credential helper, and model mapping when upstream examples describe other
   deployments or providers. Prefer bundled files over fetching changing master
   URLs. Provider examples do not establish availability on JALA.
5. Save or present the response as appropriate. Inspect JSON media responses
   for URLs/base64 rather than assuming they are media bytes. Report an
   ambiguous failure without automatically repeating generation POSTs.

TTS requires `--output`; the helper translates its catalog model plus `voice`
(default `alloy`) into the model/voice format accepted by this gateway. STT
requires `--audio-file`. Exa search and fetch catalog IDs are translated to
`model: "exa"`. The default chat combo is `9router-jala`; `--finance` selects
`9router-jala-finance`. These request models are separate from the harness.

## Bundled upstream references

These eight files are unchanged copies from the commit in
[upstream.json](../../upstream.json). Keep JALA-specific changes in this wrapper,
its references, and the helper.

| Capability | Upstream skill |
| --- | --- |
| Gateway and discovery | [9router](../9router/SKILL.md) |
| Chat / code generation | [9router-chat](../9router-chat/SKILL.md) |
| Embeddings | [9router-embeddings](../9router-embeddings/SKILL.md) |
| Images | [9router-image](../9router-image/SKILL.md) |
| Speech transcription | [9router-stt](../9router-stt/SKILL.md) |
| Text-to-speech | [9router-tts](../9router-tts/SKILL.md) |
| Web fetch | [9router-web-fetch](../9router-web-fetch/SKILL.md) |
| Web search | [9router-web-search](../9router-web-search/SKILL.md) |
