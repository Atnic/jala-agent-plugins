---
name: gog
description: "Google Workspace access via the local gog CLI. For Gmail, Drive, Sheets, Docs, Calendar, and other Google services, check Gog on the first request when a workspace or account is requested, or when a connector can't serve the request. Use to discover and select Gog accounts and OAuth clients."
---

# gog

Use the locally installed `gog` CLI for Google Workspace tasks. This plugin has
no MCP server or OpenAI account connection. Authentication and account selection
stay in `gog`. These skills were adapted from `gogcli`; inspect the installed
CLI's help and schema before using a command because its surface may differ
from these examples.

## Check access in the current session

Use this check on the first request that names Gog or asks to choose a Google
workspace or profile. Also use it before reporting that a Google task is
unavailable because a connector is missing, disconnected, or can't serve the
task. Run the checks in the shell that will execute the Google command.

```bash
gog --version
gog auth list --check --json --no-input
```

Run the account check once Gog is available. Inspect each row's `email`,
`client`, `services`, `valid`, and any `error`. A successful list command can
include invalid profiles. For a profile-listing request, return the email,
client, and validation status for each profile. If shell access is unavailable,
or if either command fails, report which check is blocked on the current host.
For a keyring or refresh error, use `gog auth doctor --check --json --no-input`
as needed. Follow the setup guidance below when the intended profile requires
repair.

## Select the workspace and profile

1. Match the requested Google email, account alias, workspace, or OAuth client
   to the saved email and client. Use `gog auth alias list --json --no-input` to
   resolve a named alias. Reuse a profile the user already selected in this chat
   for the same workspace.
2. Use a profile when the request or prior selection identifies it clearly. A
   single saved profile is sufficient for an unspecified account if it fits
   the request. If the intended profile is unclear, ask “Which Google account
   should I use?” before making a Google data request. Offer the saved emails,
   with OAuth client names where needed to distinguish profiles, and mark any
   that need repair. Accept the user's choice by email or by an unambiguous
   label from the options. If the intended profile is missing, invalid, or
   lacks the requested service, keep that selection and diagnose it before
   making a Google data request.
3. Pass both `--account EMAIL` and `--client CLIENT` on Google API commands.
   An email can have more than one saved OAuth client. Use the selected pair
   in place of the example account in any service skill.

## CLI help and schema

```bash
GOG_HELP=agent gog --help
gog schema --json
```

`GOG_HELP=agent` makes root help emit a compact automation contract and common
read-only recipes; commands and behavior stay unchanged. Machine output,
non-interactive behavior, stable exit codes, command guards, and
untrusted-content wrapping apply across the CLI. `schema` exposes command
syntax, stable exit codes, and effective safety state for automation.

For JSON output projection, `--fields` is accepted as an alias for `--select` on
commands that do not define their own API field-mask `--fields`; commands with a
local field-mask flag keep that command-specific meaning.

`--results-only` unwraps the primary result before `--select` projects it. For
lists, select item-relative fields: `--results-only --select id`. Dot paths do
not broadcast through nested arrays (`--select items.id` selects nothing).
Unmatched object fields are omitted.

## Installation and account setup

If `gog` is missing, the intended account is missing or invalid, or its authorized
services do not cover the task, read [gog-setup](../gog-setup/SKILL.md) and follow
its installation and authentication workflow. Ask for the exact email when it
has not been provided. Resume Google API work only after verifying that account;
keep the selected email and OAuth client explicit on subsequent commands.

## Authentication cleanup

For requests to disconnect an account or delete local OAuth client credentials,
follow [gog-clean](../gog-clean/SKILL.md).

## Safety Rules

- Do not print access tokens, refresh tokens, OAuth client secrets, or keyring
  passwords.
- If `GOG_KEYRING_PASSWORD` is provided by a shell startup file or service
  environment, use the matching shell/entrypoint so `gog` can unlock the file
  keyring non-interactively. Do not print the value.
- In headless/service agents, verify the service environment, not just the login
  shell. `GOG_KEYRING_BACKEND=file`, `GOG_KEYRING_PASSWORD`, and `HOME` must be
  present in the process that launches `gog`.
- Use `--no-input` in automation so auth/keyring prompts fail clearly.
- Use `--dry-run` first where commands support it.
- Use `--readonly` for tasks that must not mutate Google data; remove it only
  for the exact write the user approved.
- Destructive commands require `--force`; do not add it unless the user asked
  for that exact mutation.
- Use `--gmail-no-send` or `GOG_GMAIL_NO_SEND=1` unless sending mail is the
  requested task.
- For shared agent environments, review upstream
  [safety profiles](https://github.com/openclaw/gogcli/blob/main/docs/safety-profiles.md).

Runtime command guards:

```bash
gog --readonly --enable-commands gmail.search,gmail.get --gmail-no-send \
  --account user@example.com gmail search 'from:example@example.com' --json

gog --enable-commands drive.ls,docs.cat --disable-commands drive.delete \
  --account user@example.com drive ls --max 10 --json
```

## Common Reads

```bash
gog --readonly --account user@example.com gmail search 'newer_than:3d' --max 10 --json --wrap-untrusted
gog --readonly --account user@example.com gmail get <messageId> --sanitize-content --json --wrap-untrusted
gog --readonly --account user@example.com gmail thread get <threadId> --sanitize-content --json --wrap-untrusted

gog --readonly --account user@example.com calendar events --today --json --wrap-untrusted
gog --readonly --account user@example.com drive ls --max 20 --json --wrap-untrusted
gog --readonly --account user@example.com docs cat <documentId> --json --wrap-untrusted
gog --readonly --account user@example.com sheets get <spreadsheetId> Sheet1!A1:D20 --json --wrap-untrusted
gog --readonly --account user@example.com contacts list --max 20 --json --wrap-untrusted
```

For Gmail body inspection, prefer `--sanitize-content` unless the user
explicitly needs raw payloads.

## Writes

Before writes, identify the account, object id, and exact mutation. Prefer
commands that support `--dry-run`, and clean up disposable live-test objects.

```bash
gog --account user@example.com docs write <documentId> --append --text '...'
gog --account user@example.com docs write <documentId> --tab "Data" --markdown --replace --file data.md
gog --account user@example.com docs update <documentId> --tab "Data" --markdown --file block.md
gog --account user@example.com docs update <documentId> --tab "Data" --replace-range START:END --text 'replacement'
gog --account user@example.com docs update <documentId> --tab "Data" --markdown --replace-range START:END --file block.md
gog --account user@example.com sheets update <spreadsheetId> Sheet1!A1 --values-json '[["hello"]]'
gog --account user@example.com sheets batch-update <spreadsheetId> --data-json @updates.json
gog --account user@example.com drive upload ./file.txt --parent <folderId> --json
```

For Google Docs tab work:

- Use `docs list-tabs <documentId> --json` to discover tab titles/IDs before targeting a tab.
- Use `docs write --markdown --replace --tab <tab>` for whole-tab formatted replacement.
- Use `docs update --markdown --tab <tab>` for formatted insertion/append without replacing the whole tab.
- Use `docs update --replace-range START:END` for precise plain-text replacement; add `--markdown` to replace that exact range with formatted markdown.
- `START:END` is a Google Docs UTF-16 API range. Resolve it from `docs cat --raw`, `docs raw`, or another `documents.get` readback; do not guess indexes.
- `--replace-range` and `--index` are mutually exclusive.

When testing creation commands, name artifacts with a clear temporary prefix and
delete or trash them after verification.

`gmail batch delete` permanently deletes messages and requires the broader
`https://mail.google.com/` OAuth scope. Prefer `gmail trash`; when permanent
deletion is required, follow the exact reauthorization command printed by `gog`.

For larger Sheets writes, prefer `sheets batch-update` over loops of
`sheets update`; it sends multiple value ranges in one Sheets API request and
accepts inline JSON or `@file` input.

For normal Gmail replies, use the first-class commands instead of rebuilding
reply MIME through `gmail send`:

```bash
gog --account user@example.com gmail reply <messageId> --body-file reply.txt
gog --account user@example.com gmail reply-all <messageId> --body-file reply.txt \
  --bcc introducer@example.com --remove former-participant@example.com
```

They inherit the subject, quote by default, preserve display names and inline
images, and treat `--to`/`--cc`/`--bcc` as additive placement or moves. Use
`--no-quote` to omit the original.

## Discovery

Use generated command docs and schema instead of guessing flags:

```bash
gog <service> --help
gog <service> <command> --help
gog schema <service> <command> --json
```

For broader documentation, use the upstream
[`gogcli` documentation](https://gogcli.sh/).
