# Metadata, assets, and submissions

## Metadata

Use `asc_find_actions` to locate the specific app version, localization, screenshot set, preview, in-app purchase, subscription, or other metadata resource. Read the current resource and its relationships before editing. Use the operation-specific schema for each write and check the API result.

## Binary assets

Apple's asset upload flow uses a reservation action, signed upload operations, a local binary transfer, a commit action, and a later status check. The reservation and commit are App Store Connect API operations; the signed part-upload URLs are temporary Apple storage credentials. The MCP server keeps them in memory and hides them from action results. After the reservation action returns an asset ID, call `asc_transfer_reserved_asset` with that ID and the absolute local file path. The helper checks file size and upload ranges, sends the exact byte parts to Apple's returned hosts without the App Store Connect JWT, and returns the MD5 checksum required by the commit schema. Then call the matching typed commit action and fetch the asset until its delivery state is `COMPLETE`.

Keep the asset ID and file path tied to the user's requested work. If the server restarts or the reservation expires, create a new reservation. If any part fails, the helper keeps completed-part state in memory so it can retry only incomplete parts while the reservation remains valid.

## App review and release

Before submitting, inspect the target app version and required related resources (including build and compliance information). Use Apple's typed actions to prepare the submission, then the submission action. Submission and release-state changes open a local approval page. Approval authorizes only the exact request shown there; it does not imply Apple approval or authorize a later release request.
