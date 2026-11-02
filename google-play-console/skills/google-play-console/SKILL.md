---
name: google-play-console
description: Use Google Play Console to inspect or manage apps, releases, listings, reviews, monetization, users, and analytics.
---

# Google Play Console

Use the Google Play Console MCP server's individually named, typed actions. The catalog is generated from Google's official API Discovery documents: Android Publisher v3 and Play Developer Reporting v1beta1 plus v1alpha1. It contains one tool for each published operation in those documents, not a free-form method/path caller. The separate Custom App Publishing, Play Games Services, and EMM APIs are outside this plugin.

## Connect and select an account

1. Call `gpc_connection_status` and `gpc_list_profiles`.
2. If no profile is connected, use `google-play-console-setup` or call `gpc_setup` to open the local setup page.
3. Every API action requires the exact named `profile`. For writes, use the profile the user selected; never infer or silently switch identities.
4. Google permissions attached to the OAuth user or service account are the access boundary. A team service account may be granted broad app access in Play Console.

## Find and call actions

Use `gpc_find_actions` with the app, resource, or API operation name. The catalog is paginated; use its exact tool name and input schema. Provide documented `path`, `query`, `headers`, and `body` fields. Follow returned pagination tokens and resource identifiers instead of guessing them. Beta workflows should prefer Developer Reporting v1beta1; v1alpha1 actions are preview APIs.

The server does not retry API writes after network errors or timeouts. Inspect the current Google Play resource state before repeating a write. A successful staged edit commit means Google accepted that edit, not that a review or rollout is complete.

## Write approvals

Direct API operations for edits and routine reversible changes run after the user's direct instruction. Every Android Publisher edit commit requires host approval. The catalog also marks deletes, refunds/cancellations, user or grant changes, app-signing changes, release-state changes, pricing/availability, and subscription or product state changes as high impact.

Claude Code is asked to require interactive approval for those tools. Codex cannot force that approval from the MCP server; configure `approval_mode = "prompt"` for each listed tool using [codex-high-impact-approvals.toml](../../codex-high-impact-approvals.toml). Review the operation name, profile, app, and request body before approving.

For analytics, use the typed Developer Reporting v1beta1 actions where available. These API actions remain part of the plugin; monthly Play Console sales and financial CSV exports are outside its scope.
For release edits and staged commits, read [publishing](references/publishing.md).
For reviews and public replies, read [reviews](references/reviews.md).

## Scope boundary

The plugin covers the API operations in its bundled official Discovery catalog. Some actions available in the Play Console UI are not exposed by these APIs and remain UI-only.
