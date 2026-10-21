# Crisp safe request examples

Use these only after the base skill has resolved `website_id`, permission, target, and confirmation requirements. Keep secrets and sensitive payloads out of logs and replies.

## Inspect a workspace

```bash
curl --fail-with-body --silent --show-error \
  --user "$CRISP_TOKEN_ID:$CRISP_TOKEN_KEY" \
  -H "Accept: application/json" \
  "$CRISP_API_BASE_URL/v1/website/$CRISP_WEBSITE_ID"
```

## List the first conversation page

```bash
curl --fail-with-body --silent --show-error \
  --user "$CRISP_TOKEN_ID:$CRISP_TOKEN_KEY" \
  -H "Accept: application/json" \
  "$CRISP_API_BASE_URL/v1/website/$CRISP_WEBSITE_ID/conversations/1?per_page=20"
```

## Read messages for one session

```bash
curl --fail-with-body --silent --show-error \
  --user "$CRISP_TOKEN_ID:$CRISP_TOKEN_KEY" \
  -H "Accept: application/json" \
  "$CRISP_API_BASE_URL/v1/website/$CRISP_WEBSITE_ID/conversation/$SESSION_ID/messages"
```

## Send a confirmed text message

After establishing user authorization covering the exact workspace, session, sender, origin, and content summary:

```bash
curl --fail-with-body --silent --show-error \
  --user "$CRISP_TOKEN_ID:$CRISP_TOKEN_KEY" \
  -H "Content-Type: application/json" \
  "$CRISP_API_BASE_URL/v1/website/$CRISP_WEBSITE_ID/conversation/$SESSION_ID/message" \
  --data '{"type":"text","from":"operator","origin":"chat","content":"CONFIRMED_MESSAGE_TEXT"}'
```

Replace placeholders only with the exact user-approved values. Treat the response as send acceptance, not proof of delivery.

## Update conversation state

After establishing user authorization covering the exact workspace, session, current known state, and target state:

```bash
curl --fail-with-body --silent --show-error \
  --user "$CRISP_TOKEN_ID:$CRISP_TOKEN_KEY" \
  -H "Content-Type: application/json" \
  "$CRISP_API_BASE_URL/v1/website/$CRISP_WEBSITE_ID/conversation/$SESSION_ID/state" \
  --request PATCH \
  --data '{"state":"resolved"}'
```

## Official source

Use the [Crisp REST API reference](https://docs.crisp.chat/references/rest-api/v1/) when a placeholder’s route, schema, scope, or response behavior is not already established here.

Completion: the example is adapted to the exact target and all send/write/destructive gates have been satisfied.

Apply the base skill’s authorization rule throughout this branch. Existing explicit authorization counts; ask only for missing scope or consent.
