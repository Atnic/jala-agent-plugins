---
name: gog-setup
description: Install gog persistently on macOS, Linux, or Windows and connect a Google account. Use for first-time setup, missing gog, missing account authorization, or OAuth/keyring setup failures.
---

# Set up Gog

Get the local CLI and the requested Google account working from the agent host,
including future chats under the same OS user. The plugin supplies skills;
Google authentication lives in Gog, outside Codex Connected accounts.

## Identify the account and environment

Ask for the exact Google email before choosing an OAuth client or authorizing.
Reuse an email already supplied by the user. Detect the host OS, architecture,
and shell; use commands appropriate to that shell. For a custom domain, ask
whether it is a company Workspace account if that is unclear.

- Personal Gmail (`@gmail.com`): use the `default` client slot.
- Company Workspace: use a distinct named client, such as `jala-workspace`.
  Ask whether IT already supplied a Desktop OAuth client JSON or configured a
  named client. If supplied, accept an uploaded JSON file or its local file path; skip new
  project/client creation. Keep company credentials separate from `default`.
- Other personal/custom-domain accounts: clarify the account type and client
  choice instead of inferring ownership from the domain alone.

Accept a client JSON attachment or a local path. For an attachment, use its
available local file path when running `gog auth credentials set`; if it is not
accessible on the machine running Gog, help the user save it there first. Avoid
printing its secret contents or committing the file. Gog stores the registered
credentials and tokens locally for future chats. Use an explicit `--client`
consistently when registering and authorizing.

## Install for future chats

Check `gog --version` from the agent's command runner. If missing, carry out the
installation within the user's setup request; do not merely suggest installing
and abandon setup. Check the current [official install guide](https://github.com/openclaw/gogcli/blob/main/docs/install.md)
and [official releases](https://github.com/openclaw/gogcli/releases/latest) for
compatibility and asset names before downloading.

- **macOS:** if Homebrew is available, run
  `brew install openclaw/tap/gogcli`. Current prebuilt macOS binaries require
  macOS 15 or later; check upstream requirements for the chosen version.
- **Linux:** use the same Homebrew command when Homebrew is available.
  Otherwise download the matching official `linux_amd64` or `linux_arm64`
  release tarball, verify it against the release's `checksums.txt`, extract
  `gog`, and install the executable in a persistent user directory such as
  `~/.local/bin` (create it if needed).
- **Windows:** download the matching official `windows_amd64` or
  `windows_arm64` ZIP, verify its checksum, extract `gog.exe`, and place it in
  a persistent user directory such as `%LOCALAPPDATA%\Programs\gogcli`.
  Add that directory to the **user** PATH using Windows Environment Variables
  or a PowerShell update that preserves existing entries. Set the current
  process PATH as well for immediate verification.

Official macOS release tarballs or the upstream source-build procedure are
fallbacks when Homebrew is unavailable. A source build must also install its
output into a persistent executable directory. Do not leave the only binary
in a temporary download directory, this repository, or a thread workspace.

Use an existing persistent PATH directory where possible. Otherwise configure
the user's persistent PATH for their actual shell/host, preserving existing
entries. A shell-local `export PATH=...` alone does not finish setup. A desktop
agent may need a restart to inherit PATH changes; report this when necessary
and verify again from the agent after restart. Avoid installing an entire
package manager when an official release archive suffices.

## Select services before consent

Inspect `gog auth add --help`, `gog auth services`, and `gog auth keyring` on the
installed version. Select the service set before preparing Cloud APIs and
Data Access, and explain the access requested.

- **macOS:** default to `all-user` for full standard plugin access.
- **Linux:** default to `all-user`; check keyring availability. For headless
  hosts, follow upstream encrypted-file-keyring instructions and arrange
  secret injection into the actual agent process across sessions.
- **Windows:** default to
  `gmail,calendar,drive,docs,sheets,slides,contacts,tasks,meet,chat,forms`,
  or a smaller set if requested. This covers the employee service set including
  Forms; other services need additional setup.
  Native Windows Credential Manager has a size limit that can make broad
  authorization fail; do not default to `all-user` or claim it always fails.
  For broader access, offer a deliberately selected service set or upstream's
  encrypted file keyring before attempting `all-user`. A file keyring requires
  a password supplied securely to every agent session; a one-thread environment
  variable is insufficient. Keep native keyring storage unless the user chooses
  to change it. Never put the password in chat, checked-in files, or plaintext
  shell profiles. If storage fails, inspect the actual error and backend rather
  than treating every OAuth failure as a size issue.

Microsoft documents a [2,560-byte credential blob limit](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw).
This is a byte limit, not a 2,000-character OAuth scope limit. Repeated `auth add`
calls must not be presented as a guaranteed way to split credentials or retain
all earlier services; verify the final authorized service set.

Honor explicitly requested narrower access on every OS. `all-user` covers
standard user services; AdSense and Photos Picker are opt-in, while Admin,
Groups, and Keep need separate Workspace service-account setup.

## Reuse credentials or prepare an OAuth client

Run `gog auth credentials list --json --no-input` and
`gog auth list --check --json --no-input` to inspect existing state. Reuse a
matching client and valid account rather than recreating them. Before
reauthorizing an existing account, inspect its granted services and preserve
existing access unless the user asks to change it.

For an existing or IT-provided client, attempt the requested authorization
without requiring employees to administer its Cloud project. If APIs, consent,
test-user membership, or Workspace policy block it, use the owning project
and involve its administrator. Do not create a second project as a workaround.

When a Desktop client must be created, or project settings need repair, read
[the Google Cloud preparation reference](references/google-cloud.md).
Give a concise checklist of the applicable steps: choose/create the project;
enable APIs for the selected services; configure Branding, Audience and test
users; add the selected scopes under Data Access; create/download a Desktop
client JSON. Link the named browser pages. Run `gcloud` only in browser-based
Cloud Shell; the user does not need local `gcloud`. Run Gog on the agent host.
For Windows use PowerShell/Python to produce the scope list if `jq` is missing.
Filter the reference's full scope/API examples to the chosen services when using
limited access. Do not require unrelated APIs or `all-user` consent on Windows.

## Register, authorize, and verify

`SELECTED_SERVICES` is a placeholder for the service choice above, not a literal
value or a required environment variable. Replace it with:

- macOS/Linux: `all-user`.
- Windows: `gmail,calendar,drive,docs,sheets,slides,contacts,tasks,meet,chat,forms`.
- An explicitly chosen alternative: the agreed comma-separated service list.

Replace `EMAIL`, `CLIENT_NAME`, and `PATH_TO_CLIENT_SECRET_JSON` with the actual
email, chosen client, and local JSON path; quote paths for the current shell. Only register credentials
when the chosen client is not already configured:

```text
gog auth credentials set "PATH_TO_CLIENT_SECRET_JSON" --client CLIENT_NAME
gog auth add EMAIL --services SELECTED_SERVICES --client CLIENT_NAME
gog auth list --check --json --no-input
gog auth doctor --check --json --no-input
```

Explain that Gog opens browser consent and the user must choose the exact
requested account, review access, approve, and return to the terminal. Verify
that the intended email, client, and services are present and usable. Diagnose
failures before resuming the original task; never silently use another account.

Finish with the installed binary location, email/client, granted services, and
any required host restart or secret-injection step. State that installation and
Gog's per-user stored authorization are reusable in future chats on this host;
verify from a fresh host session where possible. Keep `--account EMAIL` explicit
on later API commands. Do not store credentials in chat-specific configuration.
