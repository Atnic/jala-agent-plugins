# Crisp workspace operations and analytics

Read this branch for operators, availability, inboxes, website settings, campaigns, and analytics. Keep `website_id` explicit for every route.

## Operators and availability

Common read routes:

```text
GET /v1/website/{website_id}/operators/list
GET /v1/website/{website_id}/operators/active
GET /v1/website/{website_id}/availability/status
GET /v1/website/{website_id}/availability/operators
```

Operator access changes require a route supported by the current official API; do not infer write routes from read routes.

## Inboxes

List and inspect inboxes:

```text
GET  /v1/website/{website_id}/inboxes/list/{page_number}
HEAD /v1/website/{website_id}/inbox/{inbox_id}
GET  /v1/website/{website_id}/inbox/{inbox_id}
```

The current public reference documents inbox reads. Verify a supported route before offering inbox creation, modification, or deletion.

## Website settings

```text
GET   /v1/website/{website_id}/settings
PATCH /v1/website/{website_id}/settings
```

Read current settings before a patch, describe the exact fields being changed, and re-read after a successful update. Do not copy a full settings object back when the user asked for a narrow change.

## Campaign templates

The current public API documents campaign templates. Read the current official reference for template list, create, inspect, update, and delete routes and body schemas. Resolve the exact template and apply the base authorization rule to writes.

Campaign dispatch, test, pause, resume, recipient lists, and statistics are not verified in the current public reference. Do not execute guessed routes. Explain the limitation unless an official supported API is established.

## Analytics

Generate analytics with:

```text
POST /v1/website/{website_id}/analytics/generate
```

The body selects the metric, result type, split, and date/range options. Do not invent metric names or date schemas; read the current official route schema before generating a report. Report the requested range and whether the result is a generated aggregate or a raw conversation/profile export.

## Official source

Use the [Crisp REST API workspace, campaign, and analytics reference](https://docs.crisp.chat/references/rest-api/v1/) for current operator scopes, inbox fields, settings schemas, campaign statuses, analytics metrics, and response codes.

Completion: the exact workspace/resource, route, read-before-write requirement, permission, confirmation, and verification plan are resolved.

Apply the base skill’s authorization rule throughout this branch. Existing explicit authorization counts; ask only for missing scope or consent.
