# gog

`gog` is a portable Agent Plugin for Google Workspace tasks through the locally
installed [gog CLI](https://gogcli.sh/) ([source](https://github.com/openclaw/gogcli)).
It contains agent skills only: no MCP server, hosted app, or OAuth integration
is bundled. Google accounts are connected and selected in `gog`, not in Codex's
Connected accounts section.

The plugin icon uses Gog's [official favicon](https://gogcli.sh/favicon.svg).

This JALA plugin packages 33 skills: the shared `gog` skill, the `gog-setup` onboarding
skill, the `gog-clean` authentication cleanup skill, service skills for
Gmail, Drive, Docs, Sheets, Calendar and other Google services, plus workflow
skills for inbox triage, meeting preparation, attachment handling, Drive
audits, weekly digests, and contact cleanup. The service skills are based on
[`openclaw/gogcli` v0.48.1](https://github.com/openclaw/gogcli/tree/v0.48.1/.agents/skills)
under its MIT license; see [LICENSE.gogcli](LICENSE.gogcli).

## Requirements

- An Agent Plugins-compatible host with shell command access.
- `gog` installed on the same machine and available to the host's command path.
- A Google Cloud OAuth client and at least one Google account authorized through
  `gog` for the services you want to use.

The shared skill tells the agent to inspect the installed CLI's help and schema
before use because commands can change.

Keep the Gog CLI on the latest stable release for your platform. The CLI and
the Codex plugin are updated separately. See [Update an existing Gog CLI](skills/gog-setup/SKILL.md#update-an-existing-gog-cli)
for upgrade and account verification steps.

## Choose a Google workspace or profile

On the first request, name the account you want, for example, “Use Gog with
`name@example.com` to find my recent Google Drive files.” Add the OAuth client
name if that email is saved under more than one client. You can also ask Gog to
list the Google profiles available in the current chat.

The shared skill checks the CLI and saved authorization on the host running
the chat's shell commands. If the intended profile is unclear, the agent asks
which Google account to use and shows the saved choices, including the OAuth
client name when needed to distinguish profiles. It uses the selected pair for
the Google request and reports any authorization problem for that profile.

## Set up `gog`

Ask your agent to **set up Gog** or invoke `$gog-setup`. It installs the CLI
for future chats, asks for your Google email, accepts an uploaded client JSON
or local path, and verifies authorization. Company accounts can reuse the
client provided by IT.

The [setup skill](skills/gog-setup/SKILL.md) owns installation, account routing,
and platform-specific service defaults. macOS/Linux use standard full access;
Windows uses the employee service set, including Forms and Apps Script, to
reduce credential storage size. The skill contains the exact service list and
commands.

For manual setup, follow the [official install guide](https://github.com/openclaw/gogcli/blob/main/docs/install.md)
and [quickstart](https://github.com/openclaw/gogcli/blob/main/docs/quickstart.md).
When you need to create or repair an OAuth project, use the
[Google Cloud preparation reference](skills/gog-setup/references/google-cloud.md).
Installation and stored authorization persist across chats under the same OS
user on the machine running Gog.

## Remove local authentication

Ask the agent to clean Gog authentication or invoke `$gog-clean`. It lists local
profiles and clients, clarifies which to remove, and checks which accounts a
client deletion would disconnect. Cleanup removes local authorization; Google
accounts and Workspace data remain intact.

## Install the plugin

### Claude Code

```bash
claude plugin marketplace add Atnic/jala-agent-plugins
claude plugin install gog@jala-agent-plugins
```

For a local checkout, add its absolute path as the marketplace source instead.
Start a new Claude Code session or run `/reload-plugins` to load the skills.
The Claude marketplace entry is in
[`../.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json).
The local `gog` installation and account setup above are required for either host.

### Codex

From this repository's GitHub marketplace:

```bash
codex plugin marketplace add https://github.com/Atnic/jala-agent-plugins.git --ref main
codex plugin add gog@jala-agent-plugins
```

Or add a local checkout as a marketplace and install `gog@jala-agent-plugins`.
Start a new Codex task after installing so its skills are loaded. The marketplace
entry is in [`../.agents/plugins/marketplace.json`](../.agents/plugins/marketplace.json).

### Update and verify the Codex plugin

If `jala-agent-plugins` is already configured from GitHub, run these commands
in PowerShell on Windows or in your terminal on macOS or Linux.

```powershell
codex plugin marketplace upgrade jala-agent-plugins
codex plugin add gog@jala-agent-plugins
```

Open a new Codex chat and ask it to show the loaded Gog setup skill path and
the version in that plugin's `.codex-plugin/plugin.json`. Check for version
`0.1.7` or later to confirm the Windows preset includes Apps Script. Run
`gog --version` separately to check the CLI version.

### Add Apps Script to an existing Windows profile

Existing profiles need new Google consent to add Apps Script. In PowerShell,
list the saved profiles and identify the email and OAuth client to reuse.

```powershell
gog auth list --check --json --no-input
```

To test Windows Credential Manager, run `gog auth keyring --json` before
reauthorizing. Expect `"keyring_backend": "auto"` for the default native
backend on Windows. If it reports `file`, the test checks the encrypted file
keyring instead.

If you authorized the standard Windows preset, use the following example and
replace the email and OAuth client with your saved values. For a customized
profile, append `appscript` to its existing service list and keep its scope
options. Use the smaller Windows service set to reduce the credential size.

```powershell
$gogAccount = "name@example.com"
$gogClient = "jala-workspace"
$gogServices = "gmail,calendar,drive,docs,sheets,slides,contacts,tasks,meet,chat,forms,appscript"
gog auth add $gogAccount --client $gogClient --services $gogServices --force-consent
```

### Test Credential Manager and Apps Script on Windows

After consent and the `gog auth add` command both succeed, open a fresh
PowerShell window under the same Windows user. Reuse your email and client
values below, and use the script ID from **Project Settings** in an Apps
Script project your account can access.

```powershell
$gogAccount = "name@example.com"
$gogClient = "jala-workspace"
$gogScriptId = "YOUR_SCRIPT_ID"
gog auth keyring --json
gog auth list --check --json --no-input --client $gogClient
gog --readonly --account $gogAccount --client $gogClient --no-input --json appscript get $gogScriptId
```

- **Credential Manager** passes when the native backend is active and the
  matching email and client show `valid: true` with `appscript` in `services`.
  This confirms the expanded grant was saved and can be refreshed from a
  new shell.
- **Apps Script** passes when `appscript get` returns the project's metadata.
  It reads the project without changing it.

If Gog reports a token storage error during consent, check the keyring backend
and the error before retrying. Windows Credential Manager limits each credential
blob to 2,560 bytes. If the smaller grant still exceeds that limit, see the
[Windows keyring guidance in the setup skill](skills/gog-setup/SKILL.md#select-services-before-consent).
See also [Microsoft's credential size limit](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw).

If authorization passes but the project read fails, check the script ID and
project permissions. Enable the Apps Script API in the OAuth client's Cloud
project and allow access in your Apps Script dashboard settings. For a
company-managed client, ask its project owner to enable the Cloud API. See
[Google's Apps Script API setup](https://developers.google.com/apps-script/api/how-tos/enable).

## How it works

```text
Agent → gog skills → local gog CLI → Google Workspace APIs
```

The skills favor structured JSON, explicit account selection, live CLI schema
discovery, bounded reads, and inspection of the exact target before writes.
Upstream service skills retain their `agents/openai.yaml` metadata. The
unrelated upstream `crabbox` skill is not included.

This plugin is developed by JALA and is not an official Google or OpenClaw
product.
