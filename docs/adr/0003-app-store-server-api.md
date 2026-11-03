---
status: accepted
---

# Separate Server API credentials and verified reads

Add read-only App Store Server API support within the App Store Connect plugin using independent named In-App Purchase profiles, preserving the existing reporting credential and CLI. Sharing an implicit issuer/key between APIs caused ambiguous authentication failures; saved credentials therefore remain unverified until a genuine transaction lookup and signed-payload check succeeds. Use Apple's Server Library with bundled Apple trust roots, bounded host/operation transport, and explicit environment selection; customer histories and attempted notification deliveries retain their distinct coverage in exports rather than claiming app-wide completeness.

The main setup entry point presents both connection types in one page, saves each independently, and offers inline purchase verification. A separate credential model does not require separate onboarding; existing targeted commands remain available.
