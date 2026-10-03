---
name: 9router-tts
description: Text-to-speech via 9Router /v1/audio/speech using OpenAI / ElevenLabs / Deepgram / Edge TTS / Google TTS / Hyperbolic / Inworld voices. Use when the user requests this capability through 9Router or the configured JALA AI gateway.
---

# 9Router — Text-to-Speech

## Gateway execution

Read [Verified JALA model defaults and live catalog](../9router/references/models.md) before selecting a model. It takes precedence over provider and model examples below. Codex, OpenAI API, and Exa connections are configured for this plugin.

The JALA gateway is **https://9router.jala.tech**. It is already deployed; do not install a server or ask users for a gateway URL. Every request requires the user's API key.

Read [credential setup and request helper](../9router/references/authentication.md) before making requests. Use the bundled `gateway.py` helper to load the key without exposing it to chat or command arguments. If no key is configured, launch `gateway.py setup-web --no-open` and open its local URL for the user to submit their key. Do not inspect the key field or capture the page while they enter it. Never ask them to paste the key into chat. The terminal `setup` fallback must be run by the user. `NINEROUTER_KEY` is an optional environment override. Do not read or display the saved credential file.

The curl/SDK examples below document endpoint shapes. Prefer the helper for execution; it uses the fixed JALA URL and authenticates discovery and inference calls. Substitute IDs and options discovered from this deployment for example models. Do not automatically repeat generation POSTs after an ambiguous timeout. This plugin supplies local scripts and REST guidance, not MCP tools or a host model-provider configuration.


Uses the hosted JALA gateway and a per-user API key. Read [9Router setup](../9router/SKILL.md) for deployment configuration and authentication.

## Discover

```bash
# 1) List models
curl $NINEROUTER_URL/v1/models/tts | jq '.data[].id'
# 2) Per-model metadata (params, voicesUrl if voice-by-id)
curl "$NINEROUTER_URL/v1/models/info?id=el/eleven_multilingual_v2"
# 3) List voices (elevenlabs, edge-tts, deepgram, inworld, local-device). Optional ?lang=vi
curl "$NINEROUTER_URL/v1/audio/voices?provider=edge-tts&lang=vi" | jq '.data[].model'
```

`model` field in `/v1/audio/speech` = voice ID directly (e.g. `edge-tts/vi-VN-HoaiMyNeural`, `el/<voice_id>`, or `openai/gpt-4o-mini-tts/alloy` model/voice).

For JALA execution, use `gateway.py run 9router-tts` with input and optional
voice in the JSON body plus `--output speech.mp3`. The helper translates the
catalog model ID to the model/voice format expected by this gateway.

## Endpoint

`POST $NINEROUTER_URL/v1/audio/speech`

| Field | Required | Notes |
|---|---|---|
| `model` | yes | voice ID from `/v1/models/tts` |
| `input` | yes | text to speak |

Query `?response_format=mp3` (default, raw bytes) or `?response_format=json` (`{audio: base64, format}`).

## Examples

Save MP3:

```bash
curl -X POST "$NINEROUTER_URL/v1/audio/speech" \
  -H "Authorization: Bearer $NINEROUTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/tts-1","input":"Hello world"}' \
  --output speech.mp3
```

JS (save file):

```js
import { writeFile } from "node:fs/promises";
const r = await fetch(`${process.env.NINEROUTER_URL}/v1/audio/speech`, {
  method: "POST",
  headers: { "Authorization": `Bearer ${process.env.NINEROUTER_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({ model: "el/eleven_multilingual_v2", input: "Xin chào" }),
});
await writeFile("speech.mp3", Buffer.from(await r.arrayBuffer()));
```

## Response shape

Default → raw audio bytes (Content-Type `audio/mp3`).

`?response_format=json`:
```json
{ "audio": "SUQzBAAAA...", "format": "mp3" }
```

## Provider quirks (model format)

| Provider | `model` format | Notes |
|---|---|---|
| `openai` | `tts-1/alloy` (model/voice) or just voice | Default model `gpt-4o-mini-tts` |
| `elevenlabs` | `<model_id>/<voice_id>` or `<voice_id>` | Default model `eleven_flash_v2_5`; list voices in Dashboard |
| `openrouter` | `openai/gpt-4o-mini-tts/alloy` | Streamed via chat-completions audio modality |
| `edge-tts` | voice id e.g. `vi-VN-HoaiMyNeural` | **noAuth**; default `vi-VN-HoaiMyNeural` |
| `google-tts` | language code e.g. `en`, `vi` | **noAuth** |
| `local-device` | OS voice name (`say -v ?` / SAPI) | **noAuth**; needs `ffmpeg` |
| `deepgram` | `aura-asteria-en` etc | Token auth |
| `nvidia`, `inworld`, `cartesia`, `playht` | `model/voice` | Provider-specific auth header |
| `coqui`, `tortoise` | speaker / voice id | Localhost noAuth |
| `hyperbolic` | model id | Body = `{text}` only |
