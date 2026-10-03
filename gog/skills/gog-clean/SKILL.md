---
name: gog-clean
description: Remove local Gog account profiles or OAuth clients. Use when the user asks to disconnect an account, delete stored client credentials, or reset Gog authentication.
---

# Clean Gog authentication

Remove the requested local authorization from the machine running Gog. Here,
**profile** means an email's stored authorization under a particular OAuth
client; **client** means Gog's locally registered OAuth credentials.

## Inspect and select

Check the installed CLI before planning removal:

```text
gog --version
gog auth remove --help
gog auth credentials remove --help
gog auth list --json --no-input
gog auth credentials list --json --no-input
```

List only account emails, client names, and relevant mappings; keep tokens and
client secrets out of output. Use the same Gog home and keyring environment as
the agent's normal commands. If Gog is unavailable, report that local cleanup
cannot yet be inspected; installation is not required just to answer a question.

Resolve the requested targets against this inventory:

- **Profile only:** select the exact email and client. The same email can have
  authorization under multiple clients; clarify which when unspecified.
- **Client:** select its exact name and identify every associated account.
  Client removal can also delete those accounts' tokens and domain mappings;
  inspect the installed version's behavior and explain the affected targets.
- **Both:** identify the email/client pair and all other accounts sharing that
  client. Use client removal alone when it already performs the requested cleanup.
- **All:** enumerate the accounts and clients affected by a full local reset.

If the user has not specified profile, client, or both, ask which to remove
and present the available targets. If deleting a client would disconnect accounts
outside the user's stated scope, ask whether to include them or remove only the
requested profile. An explicit instruction naming the complete affected scope
is sufficient authorization; do not ask for the same approval again.

## Remove the selected targets

Replace placeholders with verified targets. Preview with `--dry-run` when the
installed command supports it. Perform only the requested removals:

```text
gog auth remove EMAIL --client CLIENT_NAME
gog auth credentials remove CLIENT_NAME
```

Always name the client explicitly, including `default`; omitting it can select
the wrong default. Use `gog auth credentials remove all` only for an explicitly
requested removal of every local client and its associated authorizations.
For automation, use `--force --no-input` only after the full affected scope is
authorized. If inspection or deletion fails, diagnose and report it; avoid a
blanket filesystem or keyring wipe as a fallback.

These operations remove local Gog state. They do not delete the Google account,
the OAuth client in Google Cloud, or Gmail/Drive/Workspace data, and do not imply
server-side revocation of Google's consent grant. Original downloaded/uploaded
JSON files and unrelated service-account configuration are separate targets;
remove them only when explicitly included, using their verified exact paths.
Keep the installed CLI and plugin unless uninstallation is also requested.

## Verify completion

Repeat the account and credential listings. Every selected target must be
absent, and unrelated account/client entries must remain. Check relevant aliases
and mappings through the installed CLI's supported read commands if removal
was expected to clean them. Report partial completion if a target or stale
mapping remains; do not claim a full reset from a single successful command.

Summarize the removed emails/clients and any unresolved local state. If the user
wants to reconnect, route to [gog-setup](../gog-setup/SKILL.md).
