# Crisp people profiles and visitors

Read this branch for people discovery, profile mutations, profile metadata, profile export, and current visitor inspection.

## People profiles

List profiles with page-number pagination:

```text
GET /v1/website/{website_id}/people/profiles/{page_number}
```

`per_page` is documented as `20`–`50` and defaults to `20`. Use `sort_field`, `sort_order`, `search_operator`, `search_filter`, `search_text`, and ISO 8601 creation-date bounds deliberately. Start with a narrow page to avoid unnecessary PII exposure.

Inspect a profile:

```text
GET /v1/website/{website_id}/people/profile/{people_id}
```

Create a profile only with an exact user-approved target and the required body shape. Crisp documents `email` and `person.nickname` as required for the create route:

```text
POST /v1/website/{website_id}/people/profile
```

```json
{
  "email": "person@example.com",
  "person": { "nickname": "Person" }
}
```

The same resource path supports full replacement and partial update:

```text
PUT   /v1/website/{website_id}/people/profile/{people_id}
PATCH /v1/website/{website_id}/people/profile/{people_id}
DELETE /v1/website/{website_id}/people/profile/{people_id}
```

Profile creation, replacement, partial update, and deletion require explicit user authorization naming the exact `website_id`, `people_id` or creation target, fields to change, and resulting scope. Delete requires explicit authorization covering the deletion effect immediately before the call.

## People data and activity

Use these routes for data owned by a profile:

| Operation | Method and path |
| --- | --- |
| List profile conversations | `GET /v1/website/{website_id}/people/conversations/{people_id}/list/{page_number}` |
| List profile events | `GET /v1/website/{website_id}/people/events/{people_id}/list/{page_number}` |
| Get profile data | `GET /v1/website/{website_id}/people/data/{people_id}` |
| Replace profile data | `PUT /v1/website/{website_id}/people/data/{people_id}` |
| Update profile data | `PATCH /v1/website/{website_id}/people/data/{people_id}` |
| Get subscription status | `GET /v1/website/{website_id}/people/subscription/{people_id}` |
| Update subscription status | `PATCH /v1/website/{website_id}/people/subscription/{people_id}` |

Treat custom data, subscription status, contact details, and event history as sensitive. Confirm every mutation and re-read when the API exposes a corresponding GET route.

## Export profiles

A profile-export route is not present in the public reference checked on 2026-10-21. Before exporting, establish a documented API and its delivery behavior or explain the limitation. Do not call a guessed export endpoint or claim a local download.

## Visitors

List visitors currently on the workspace:

```text
GET /v1/website/{website_id}/visitors/list/{page_number}
```

Other visitor routes include counting visitors, pinpointing visitors on a map, resolving a session identifier from a token, and clearing blocked visitors in a rule. Resolve the exact visitor/session or rule before using a mutation. Never infer a visitor identity from partial data.

## Official source

Use the [Crisp REST API people and visitor reference](https://docs.crisp.chat/references/rest-api/v1/) for current profile fields, filter encoding, visitor route parameters, route scopes, and response codes.

Completion: the exact workspace and person/visitor scope, PII handling, route, mutation confirmation, and export delivery behavior are resolved.

Apply the base skill’s authorization rule throughout this branch. Existing explicit authorization counts; ask only for missing scope or consent.
