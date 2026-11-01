---
status: accepted
---

# App Store Connect plugin authentication and scope

The plugin will support individual and team App Store Connect API keys, import the downloaded `.p8` through a loopback setup form, and store the key only in the OS-native secret store; setup will fail closed if that store is unavailable. It will expose every operation in Apple's published App Store Connect OpenAPI specification as a named, typed action, with guided workflows composed from those actions; it will not offer a free-form method/path caller or a read-only allowlist, and it will require local browser confirmation for high-impact writes. Apple-generated key permissions remain authoritative: team keys can span all apps, individual keys inherit user access, and the API surface does not include every App Store Connect UI action. A person with the required Apple account role must request access and generate the key; the plugin only imports and verifies it. Signed asset-upload and analytics-report URLs are held in process memory and kept out of model-visible responses. This supports broad API access while avoiding plaintext credential fallbacks and documenting the wider scope of team keys.
