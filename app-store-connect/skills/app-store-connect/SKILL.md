---
name: app-store-connect
description: Use App Store Connect for reports or to manage apps, metadata, reviews, TestFlight, subscriptions, provisioning, users, or any other resource exposed by Apple's REST API.
---

# App Store Connect

Use the App Store Connect MCP server's individually named, typed actions. The action catalog is generated from Apple's published OpenAPI specification; it covers each documented HTTP operation with its own input schema. It does not expose a free-form method/path caller.

## Run an operation

1. Call `asc_connection_status`. If no key is connected, use the `app-store-connect-setup` skill or call `asc_setup` to open the local import form.
2. Use `asc_find_actions` to find the action by resource or workflow. Each result includes its MCP tool name, operation ID, method, path, and any high-impact category. The tool catalog is paginated; use the exact named action for the endpoint.
3. Read the action schema and provide its `path`, `query`, and `body` values in the documented shape. Follow Apple's JSON:API relationships and pagination links. Never guess a resource ID or relationship.
4. Check the returned HTTP status and response before reporting completion. The server does not retry writes. After a timeout or connection error, inspect the resource before repeating a write.

The imported API key is the authority boundary. Team keys can act across all team apps within the assigned role. Individual keys follow the associated user's role and app access, and Apple excludes Sales and Finance reports and provisioning endpoints from individual keys. A key that lacks permission will receive Apple's authorization error.

## Confirm high-impact changes

The server requires a person to approve a local browser page before it sends a request that deletes or revokes a resource, changes submission or release state, changes pricing or availability, or changes user access. The page shows the action and request details. If approval is cancelled, the browser cannot open, or the page times out, the server sends no request. Routine reversible edits run only after the user's direct instruction.

App Store Connect changes affect production data. Treat each action as an operation on the live account. A successful submission request does not mean Apple has approved the app; report the returned state.

## Workflow references

- For sales, finance, analytics, and performance data, read [reports](references/reports.md).
- For reviews and TestFlight, read [reviews and TestFlight](references/reviews-testflight.md).
- For metadata, asset uploads, and app submissions, read [metadata and submissions](references/metadata-submissions.md).

The API does not represent every action in the App Store Connect website. For example, creating an app and uploading a build are outside these REST operations; Apple directs app creation to the website and build uploads to Xcode or Transporter. Use this plugin for the API surface Apple publishes.
