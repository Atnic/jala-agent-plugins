# Crisp authentication and transport

Use this reference before the first Crisp request or when a request fails because of credentials, scope, quota, or rate limits.

## Authentication

Crisp API requests use a token keypair with HTTP Basic Auth. Keep both values secret and do not place them in URLs, files, or logs.

```bash
curl --fail-with-body --silent --show-error \
  --user "$CRISP_TOKEN_ID:$CRISP_TOKEN_KEY" \
  -H "Accept: application/json" \
  "$CRISP_API_BASE_URL/v1/website/$CRISP_WEBSITE_ID"
```

`CRISP_WEBSITE_ID` is the exact workspace boundary for every website-scoped route. Never derive it from a display name or domain. URL-encode it and other path/query values when they come from user input.


## Response and retry handling

Crisp responses commonly expose an envelope with `error`, `reason`, and `data`. Report the HTTP status and redacted `reason`; treat `error: true` as failure even if the transport request completed.

The API can return `429 Too Many Requests` or `420 Enhance Your Calm`. Use bounded backoff and respect the route’s limit. `GET` and `HEAD` routes may be served from Crisp’s cache, so a cached read is not proof that a just-written mutation has propagated. Re-read a changed object when verification matters.

Do not blindly retry a message send, campaign dispatch, profile export, or other mutation after an ambiguous timeout. First check whether Crisp returned an identifier or whether a safe read can determine whether the mutation took effect.

## Official sources

- [Crisp REST API reference](https://docs.crisp.chat/references/rest-api/v1/)
- [REST API authentication overview](https://docs.crisp.chat/guides/rest-api/authentication/)
- [Website token authentication](https://docs.crisp.chat/guides/rest-api/authentication/website-token/)
- [Plugin token authentication](https://docs.crisp.chat/guides/rest-api/authentication/plugin-token/)
- [REST API rate limits](https://docs.crisp.chat/guides/rest-api/rate-limits/)

Completion: the exact workspace, Basic Auth, route scope, and retry posture are resolved without exposing credentials.

Apply the base skill’s authorization rule throughout this branch. Existing explicit authorization counts; ask only for missing scope or consent.
