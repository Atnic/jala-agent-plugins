---
status: accepted
---

# App Store Connect plugin authentication and scope

The plugin will support individual and team App Store Connect API keys, import the downloaded `.p8` through a loopback setup form, and store the key only in the OS-native secret store; setup will fail closed if that store is unavailable. The plugin uses agent documentation and a Python REST CLI. The agent looks up current endpoint details in Apple's documentation; the CLI handles authentication, requests, and local browser confirmation for high-impact writes. This replaces the broken MCP interface and removes its generated operation catalog and server lifecycle. Apple-generated key permissions remain authoritative: team keys can span all apps, individual keys inherit user access, and the API surface does not include every App Store Connect UI action. A person with the required Apple account role must request access and generate the key; the plugin only imports and verifies it. Signed asset-upload and analytics-report URLs are held in process memory and kept out of model-visible responses. This supports broad API access while avoiding plaintext credential fallbacks and documenting the wider scope of team keys.
