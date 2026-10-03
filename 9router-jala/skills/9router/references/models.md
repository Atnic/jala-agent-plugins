# Verified JALA skill model mapping

Authenticated catalogs checked on 2026-10-03 at `https://9router.jala.tech`.
OpenAI API (`openai/`), Codex (`cx/`), Exa (`exa/`), and the two declared JALA combos
are included. Other providers are visible in the gateway, but are outside the
requested plugin scope. This is catalog verification, not an inference test.
Availability and quota may change. The helper checks the selected model against
the live capability catalog before sending a generation request.

The harness `config.toml` model does not set the model used by these skills.
[models.json](../../../models.json) defines skill defaults and allowed models.
Use `gateway.py run <skill> --body request.json` to insert the default model and
execute against the correct endpoint. The body does not need a `model` field.
Use `--model <listed-id>` to choose an alternative. `--finance` selects the
finance combo for chat only, when explicitly requested by the user.

| Skill | Default | Catalog |
| --- | --- | --- |
| `9router` | None; setup and discovery only | All catalogs |
| `9router-chat` | `9router-jala` | `/v1/models` |
| `9router-image` | `openai/gpt-image-2.5-sunburst` | `/v1/models/image` |
| `9router-tts` | `openai/gpt-4o-mini-tts` | `/v1/models/tts` |
| `9router-stt` | `openai/gpt-4o-transcribe` | `/v1/models/stt` |
| `9router-embeddings` | `openai/text-embedding-3-large` | `/v1/models/embedding` |
| `9router-web-search` | `exa/search` | `/v1/models/web` |
| `9router-web-fetch` | `exa/fetch` | `/v1/models/web` |

`9router-jala-finance` is an allowed chat alternative. Neither chat combo is a
media, transcription, embedding, or dedicated web model. The catalog reports
search capability for several chat models; this does not prove that a plain
chat request performs web search. The web catalog currently returns
`exa/search` and `exa/fetch`; both are enabled through the JALA Exa connection.
`/v1/models/image-to-text` returned an empty list; vision-capable chat models
remain available through chat requests.

## Default model policy

Choose current models exposed by this deployment. Image uses GPT Image 2.5
Sunburst for demanding quality requirements; use
`--model openai/gpt-image-2.5-flare` when speed is preferred. Both variants were
confirmed by the live model catalog and metadata endpoint. See the
[official image prompting guide](https://developers.openai.com/api/docs/guides/image-prompting).
Speech defaults are the newer GPT-4o-based models listed by this gateway.
Embedding uses `text-embedding-3-large` for quality; `3-small` belongs to the
same generation and remains an explicit lower-cost alternative.

Newer models documented elsewhere are not executable defaults until the JALA
gateway exposes and supports them. Chat continues to use the administrator's
`9router-jala` combo; upgrading its internal seats is a server-side choice.

## Image request defaults

For the default Sunburst model, start with `{"prompt":"Your image description"}`.
The helper adds the configured model and `n: 1`; it does not add `size` or
`response_format`. This minimal request succeeded and returned `data[0].b64_json`.
Save the JSON response, decode the returned base64, and inspect the image.

A previous request specifying both `size: "1536x1024"` and
`response_format: "b64_json"` returned HTTP 400. The original error details and
request logs are unavailable, so neither field is established as unsupported.
Do not add them routinely based on generic upstream examples. When explicitly
requested and verified for the selected model, optional fields can still be
supplied; the helper preserves them and does not silently alter user choices.
No automatic retry or optional-field stripping occurs on rejection.

## Direct execution examples

Create a JSON request file with the task input only. The helper inserts the model:

```bash
python3 "<plugin-root>/scripts/gateway.py" run 9router-chat --body chat.json
python3 "<plugin-root>/scripts/gateway.py" run 9router-chat --finance --body chat.json
python3 "<plugin-root>/scripts/gateway.py" run 9router-image --body image.json --output image-response.json
python3 "<plugin-root>/scripts/gateway.py" run 9router-image --model openai/gpt-image-2.5-flare --body image.json --output flare-response.json
python3 "<plugin-root>/scripts/gateway.py" run 9router-tts --body speech.json --output speech.mp3
python3 "<plugin-root>/scripts/gateway.py" run 9router-stt --body transcription.json --audio-file recording.mp3
python3 "<plugin-root>/scripts/gateway.py" run 9router-embeddings --body embeddings.json
python3 "<plugin-root>/scripts/gateway.py" run 9router-web-search --body search.json
python3 "<plugin-root>/scripts/gateway.py" run 9router-web-fetch --body fetch.json
```

Task-only bodies:

- Chat: `{"messages":[{"role":"user","content":"Hello"}]}`
- Image: `{"prompt":"A shrimp pond at sunrise","n":1}`
- Speech: `{"input":"Hello from JALA"}`
- Transcription: `{"language":"en"}` (may also be `{}`)
- Embeddings: `{"input":"Text to embed"}`
- Web search: `{"query":"shrimp farming","max_results":5}`
- Web fetch: `{"url":"https://example.com","format":"markdown"}`

Image output from this command is a JSON response containing a URL or base64
content, not necessarily image bytes. Inspect and render the resulting artifact.
Codex image alternatives may return SSE rather than the OpenAI JSON shape.
No generation POST is automatically retried.

## Endpoint model translation

Use `run` with the catalog model IDs above. The helper checks the catalog before
sending a request, then maps Exa search/fetch to `model: "exa"`. For OpenAI TTS,
it appends the body `voice` (default `alloy`) to the model ID, for example
`openai/gpt-4o-mini-tts/alloy`. This gateway ignores a separate voice field.
TTS requires `--output`, and transcription requires `--audio-file`.
