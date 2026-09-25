---
name: gog
description: "gog CLI: safe Google Workspace automation, JSON, auth, scoped reads/writes."
---

# gog

Use the locally installed `gog` CLI for Google Workspace tasks. This plugin has
no MCP server or OpenAI account connection. Authentication and account selection
stay in `gog`. These skills were adapted from `gogcli`; inspect the installed
CLI's help and schema before using a command because its surface may differ
from these examples.

## Fast Path

```bash
gog --version
gog auth list --check --json --no-input
gog auth doctor --check --json --no-input
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

## First-use onboarding

Before starting a Google Workspace task, check whether the requested account is
authorized with `gog auth list --check --json --no-input`. If it is missing or
invalid, stop before calling Google APIs and guide the user through setup using
the [setup guide](../../README.md). Do not silently use a different account.

- If OAuth client credentials are missing or the user wants a different client,
  ask them to create or select a Google Cloud OAuth **Desktop app** client and
  provide the local path to its downloaded JSON file. Never ask them to paste
  the client secret into chat.
- If the user already has a client JSON file, register it with
  `gog auth credentials set <path> --client <name>`, using a new, explicit name
  when they want to keep existing client credentials available.
- Ask which Google account and services they want to authorize. Request only
  those services; do not choose `all-user` unless the user asks for broad
  access.
- Start `gog auth add <email> --services <services> --client <name>` and let the
  user complete Google's browser consent. Then verify the account and granted
  services with `gog auth list --check --json --no-input` before resuming the
  original task.

If the account is already valid, continue without repeating onboarding.

Pick the account explicitly for API work:

```bash
gog --readonly --account user@example.com gmail search 'newer_than:7d' --json --wrap-untrusted
```

Prefer `--json --wrap-untrusted` for agent parsing when reading Google content.
Human hints and progress should stay on stderr; stdout is for data.

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

## Auth

For first-time setup, Google Cloud project and API enablement, Desktop OAuth
client creation, or broad `all-user` authorization, read the plugin's
[setup guide](../../README.md). It separates Cloud Shell steps from the local
`gog` account connection.

OAuth setup is partly interactive. An agent can inspect and diagnose it, but a
human normally completes browser consent:

```bash
gog auth credentials list
gog auth add user@example.com --services drive
```

For a new account, authorize only the services needed for the user's task.
Before reauthorizing an existing account, inspect its current services with
`gog auth list --check --json --no-input` and preserve existing access unless
the user asks to change it. Constrain each command with the relevant account,
`--readonly` or command allowlists, and other supported safety flags.

Service accounts are Workspace-only and mainly fit Admin, Groups, Keep, and
domain-wide delegation flows; they do not solve consumer `@gmail.com` OAuth.

If an account needs browser consent, run `gog auth add` and let the user complete
Google's consent flow. Then verify the intended account and granted services with
`gog auth list --check --json --no-input`. For auth problems, inspect the
environment in which the agent host launches `gog`; it may differ from an
interactive shell.

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
