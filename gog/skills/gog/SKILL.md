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

## When the requested account is not authorized

After the auth check above, if the requested account is missing or invalid, stop
before calling Google APIs. Guide the user through the [setup guide](../../README.md);
do not silently switch to another account.

- Determine the OAuth client from the requested email domain before guiding
  setup. For an address ending in `@gmail.com`, select the `default` client
  slot. For a company domain, use a distinct named client (for example,
  `jala-workspace`) and never fall back to `default`, even if it is configured
  or has other authorized accounts. Do not assume a custom domain is a company
  Workspace domain if unclear; ask. Follow an explicit client choice when it
  preserves this separation.
- Check available client names with
  `gog auth credentials list --json --no-input` and accounts with
  `gog auth list --check --json --no-input`.
- For Gmail, if the `default` client credentials exist, reuse them and do not
  create another project or client. Still confirm that the Google Cloud project
  belonging to `default` has the complete API list enabled; Branding and
  Audience are configured; Data Access includes `all-user`; and, for an
  External app in Testing, the requested account is a test user. Stored
  credentials do not prove these settings are ready. If any are missing or
  cannot be verified, show the corresponding README steps and use the existing
  client's project. If its project is unknown, ask the user to identify it
  before changing project settings. If `default` credentials do not exist,
  guide setup and register a Desktop client under `default`.
- For a company-domain account, never reuse `default`. Reuse an existing named
  client if available; otherwise guide setup for a separate named client.
  Confirm that the named client's project has the complete API list enabled,
  Branding and Audience configured, Data Access including `all-user`, and the
  requested account on Test users when the app is External + Testing. Then use
  the same `--client` value when registering credentials and authorizing the
  account.
- When project APIs, consent-screen settings, or scopes need setup, or a new
  project/client is required, read the complete setup in the
  [README](../../README.md). Present the needed steps as a concise numbered
  checklist. Keep the README as the source of truth; do not copy setup details
  into this skill.
  Explain when to reuse an existing client and project and skip project/client
  creation while still enabling the full API list and adding `all-user` under
  Data Access. For a new project/client, include every preparation step and
  command: choose/create a project and identify its Project ID; select/create
  it in Cloud Shell; enable the complete API list; configure Branding and
  Audience (including test-user setup when needed); add `all-user` scopes using
  `gog auth services --markdown`; create a Desktop OAuth client and download or
  recover its JSON; then register the file, authorize the requested account,
  complete browser consent, and verify access on the local machine with Gog.
  Include clickable links to Google Cloud Shell and Google Auth Platform.
  Tell the user to open those pages in a browser, sign in with an account that
  can access the project, select the correct project, and follow the exact UI
  path in the README (Cloud project picker/Dashboard; Branding; Audience; Data
  Access; Clients → Create client → Desktop app). Label browser steps, Cloud
  Shell commands, and local-terminal commands separately. Do not ask for the
  JSON path until prerequisites and download steps have been explained.
- If the OAuth client is missing or the user wants a different one, ask them to
  create or choose a Google Cloud OAuth **Desktop app** client and provide its
  downloaded JSON file's local path. Never ask them to paste its client secret
  into chat.
- Register the JSON with `gog auth credentials set <path> --client <name>`.
  Use `default` only for `@gmail.com`; use a distinct named client for company
  domains so their credentials and tokens remain separate.
- For complete plugin access, request `all-user` by default; use a narrower
  service list if the user asks for limited access. Explain that `all-user`
  covers Gog's standard user services, while AdSense and Photos Picker require
  explicit opt-in and Admin, Groups, and Keep require Workspace service-account
  setup.
- OAuth scope is independent of the current API operation's safety mode. Do not
  replace `all-user` with `gmail` just because the task is about Gmail, and do
  not describe authorization as "read-only Gmail access" unless the user asked
  for limited Gmail-only scope. `--readonly` controls API mutations after
  authorization; it does not narrow OAuth scopes.
- Run `gog auth add <email> --services all-user --client <name>` and let the
  user complete Google's browser consent. Tell them Gog will open a browser;
  they must select/sign in to the exact requested account (especially the
  company account for a named client), review the consent screen, approve the
  requested scopes, then return to the terminal and verify with
  `gog auth list --check --json --no-input`. If they chose a narrower scope,
  use that service list instead. Resume the task only after verification.

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

For first-time setup, follow the [setup guide](../../README.md), which explains
project creation, API enablement, OAuth branding/audience, scope configuration,
Desktop client creation, and JSON download. It separates Cloud Shell steps from
the local `gog` account connection.

OAuth setup is partly interactive. An agent can inspect and diagnose it, but a
human normally completes browser consent:

```bash
gog auth credentials set "PATH_TO_CLIENT_JSON" --client CLIENT_NAME
gog auth add user@example.com --services all-user --client CLIENT_NAME
```

Set `CLIENT_NAME` by the target email domain: `default` for `@gmail.com`, or a
distinct name for a company domain. For full plugin access, use `all-user`; only
use a narrower service list when the user asks for limited access. Do not
reduce OAuth services to match only the current task. Before reauthorizing an
existing account, inspect its current services with
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
