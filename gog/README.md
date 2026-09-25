# gog

`gog` is a portable Agent Plugin for Google Workspace tasks through the locally
installed [gog CLI](https://gogcli.sh/) ([source](https://github.com/openclaw/gogcli)).
It contains agent skills only: no MCP server, hosted app, or OAuth integration
is bundled. Google accounts are connected and selected in `gog`, not in Codex's
Connected accounts section.

The plugin icon uses Gog's [official favicon](https://gogcli.sh/favicon.svg).

This JALA plugin packages 31 skills: the shared `gog` skill, service skills for
Gmail, Drive, Docs, Sheets, Calendar and other Google services, plus workflow
skills for inbox triage, meeting preparation, attachment handling, Drive
audits, weekly digests, and contact cleanup. The skills are adapted from
[`openclaw/gogcli`](https://github.com/openclaw/gogcli)
under its MIT license; see [LICENSE.gogcli](LICENSE.gogcli).

## Requirements

- An Agent Plugins-compatible host with shell command access.
- `gog` installed on the same machine and available to the host's command path.
- A Google Cloud OAuth client and at least one Google account authorized through
  `gog` for the services you want to use.

The shared skill tells the agent to inspect the installed CLI's help and schema
before use because commands can change.

## Set up `gog`

Install `gog` using the upstream [install guide](https://github.com/openclaw/gogcli/blob/main/docs/install.md),
which covers macOS, Linux, Windows, containers, and source builds. Make sure
the host running the agent can find `gog` on its command path, then check it:

```text
gog --version
```

### Prepare a Google Cloud project and OAuth client

First choose a client for the account you are connecting. For an address ending
in `@gmail.com`, use Gog's `default` OAuth client slot. If a default client is
already configured, reuse it. If it is not configured on this machine, create
or choose a Desktop OAuth client and register it under `default`. For a company
domain such as `@jala.tech`, use a separate named client such as
`jala-workspace`; do not store or authorize it as `default`. This keeps the
company credentials separate from personal Gmail credentials. If an address
uses a custom domain and you are unsure whether it is a company Workspace
account, ask before choosing a client. Follow the user's explicit client choice
if they give one, except that company-domain accounts must remain on a distinct
named client rather than `default`.

An existing client credential only identifies which OAuth client Gog uses; it
does not confirm that the client's Google Cloud project has every API enabled
or that its consent configuration is ready for `all-user`. When reusing a
client for full plugin access, check the APIs, Branding, Audience, Data Access,
and any required test-user entry below in the project that owns that client.
Do not create a second project or client just because the requested account is
not authorized yet. If the existing client's project is unknown, ask the user
to identify it before changing project settings.

For project and OAuth setup, use a browser and the named pages below. Sign in
with a Google account that can access or create the project.

- Open [Google Cloud Shell](https://shell.cloud.google.com/) in a browser tab;
  it comes with `gcloud` installed and signed in. For an existing project, open
  the [Google Cloud Console](https://console.cloud.google.com/), click the
  project picker in the top bar, select the project, and open **Dashboard** to
  find its **Project ID**. For a new project, create it with the Cloud Shell
  command in step 2 or use [Create a project](https://console.cloud.google.com/projectcreate).
- In another browser tab, open [Google Auth Platform](https://console.cloud.google.com/auth/overview).
  Use the project picker at the top to select the same project. In the left
  navigation, open **Branding**, **Audience**, **Data Access**, and finally
  **Clients** as directed below.
- Run the final `gog` commands in a terminal on the computer where Gog and the
  agent are installed, not in Cloud Shell.

1. **Choose a project.** Select an existing project in the Cloud Console
   project picker and use its **Project ID**, not its display name. Find it on
   the project's Dashboard. Or create a project: enter `Gog CLI` as the name
   and use Google's suggested Project ID, or choose one that is globally
   unique. It must be 6–30 characters, start with a lowercase letter, and
   contain only lowercase letters, numbers, and hyphens. A Project ID is
   permanent after creation. Replace `YOUR_UNIQUE_PROJECT_ID` below with the
   chosen ID. See Google's [project guide](https://docs.cloud.google.com/resource-manager/docs/creating-managing-projects).
2. **Set the active project in Cloud Shell.** If you already created the
   project in the Console, or are using any existing project, run:

   ```bash
   gcloud config set project EXISTING_PROJECT_ID
   ```

   If you are creating the project in Cloud Shell instead, run both commands:

   ```bash
   gcloud projects create YOUR_UNIQUE_PROJECT_ID --name="Gog CLI"
   gcloud config set project YOUR_UNIQUE_PROJECT_ID
   ```

3. **Enable Gog's standard APIs in Cloud Shell.** This enables the APIs for
   `all-user`; it does not grant OAuth scopes. Run:

   ```bash
   gcloud services enable \
     analyticsadmin.googleapis.com analyticsdata.googleapis.com \
     calendar-json.googleapis.com chat.googleapis.com classroom.googleapis.com \
     docs.googleapis.com drive.googleapis.com driveactivity.googleapis.com \
     drivelabels.googleapis.com forms.googleapis.com gmail.googleapis.com \
     googleads.googleapis.com meet.googleapis.com people.googleapis.com \
     photoslibrary.googleapis.com script.googleapis.com \
     searchconsole.googleapis.com sheets.googleapis.com slides.googleapis.com \
     tasks.googleapis.com youtube.googleapis.com
   ```

   Check enabled APIs with `gcloud services list --enabled`. Gog derives this
   list from its selected services; run `gog auth setup --help` if your
   installed CLI offers a different service set.
4. **Configure Branding in Google Auth Platform.** Under **Branding**, set
   **App name** (for example, `Gog CLI`), **User support email**, and
   **Developer contact information**, then save. A logo is optional. External
   apps published to production also need a verified homepage and privacy
   policy. See Google's [branding guide](https://support.google.com/cloud/answer/15549049?hl=en).
5. **Choose the Audience.** Choose **Internal** if the project belongs to
   JALA's Google Cloud organization and only JALA Workspace accounts will use
   it. If Internal is unavailable, ask a Workspace/Cloud administrator to
   create or move the project into the organization. Otherwise choose
   **External**. If an External app is in **Testing**, add each account under
   **Test users**; authorizations for user-data scopes in Testing expire after
   seven days. See Google's [audience guide](https://support.google.com/cloud/answer/15549945?hl=en).
6. **Add the OAuth scopes.** Under **Data Access → Add or remove scopes**, add
   Gog's `all-user` scopes, the full default set of standard Gog user services.
   On the computer where Gog is installed, run `gog auth services --markdown`
   to display the scope list. Save the scope list in Google Auth Platform.
   Broad scopes may need Workspace admin approval or Google's OAuth
   verification, depending on the audience and publishing status.
7. **Create and download a Desktop client JSON only if needed.** For a
   company-domain account, create a separate named Desktop client if there is
   not already a named client to reuse. For `@gmail.com`, create one only if
   the `default` client is not already configured. In the browser, confirm
   Google Auth Platform has the right project selected. Click **Clients** in the
   left navigation, then **Create client**. Choose **Desktop app**, enter a name
   such as `Gog CLI desktop`, and click **Create**. Download the JSON in the
   creation dialog. If you closed it, open **APIs & Services → Credentials**,
   select the Desktop app under **OAuth 2.0 Client IDs**, and click **Download
   JSON**. Save it on the computer where Gog runs. A Desktop client needs no
   redirect URI configuration. See Google's
   [credential guide](https://developers.google.com/workspace/guides/create-credentials).
   Keep the file private; do not commit it or paste its contents into chat.
   If reusing an existing `default` client for Gmail, skip client creation and
   use the project that owns that client for the API and Data Access steps.

### Connect an account on the machine running the agent

Follow the upstream [quickstart](https://github.com/openclaw/gogcli/blob/main/docs/quickstart.md)
to store the downloaded JSON and complete browser consent. Run these commands
on the machine where `gog` is installed for your agent:

```text
# Run this only if CLIENT_NAME is not already listed by gog auth credentials list:
gog auth credentials set "PATH_TO_CLIENT_SECRET_JSON" --client CLIENT_NAME
gog auth add you@example.com --services all-user --client CLIENT_NAME
gog auth list --check --json --no-input
```

Replace `PATH_TO_CLIENT_SECRET_JSON` with the path to the downloaded OAuth
client JSON file on your system. Set `CLIENT_NAME` to `default` for a
`@gmail.com` account, or to a distinct name such as `jala-workspace` for a
company-domain account. Use the same name for `auth credentials set` and
`auth add`; always pass it explicitly so one account's client is not selected
for the other. If `gog auth credentials list` already shows `CLIENT_NAME`, skip
`auth credentials set` and run only the `auth add` and verification commands.

`gog auth add` opens Google's sign-in and consent page in a browser. Select the
exact account you are connecting (switch accounts if the browser shows a
different signed-in user), review the requested access, approve it, and return
to the terminal. Confirm the intended email and services in the verification
output before asking Gog to access that account.

`all-user` requests every standard Gog user OAuth service, including Gmail,
Calendar, Drive, Docs, Sheets, and the other services in the API list above.
This is the full default scope for the plugin. It does not include every Gog
service: AdSense and Photos Picker require explicit opt-in, while Admin, Groups,
and Keep require a Workspace service account and domain-wide delegation. For
narrower access, replace `all-user` with a comma-separated service list, such as
`gmail,calendar,drive`. Inspect `gog auth add --help` and `gog auth services` for
the supported options.

For multiple accounts, authorize each one with `gog auth add` and select the
intended account per command with `gog --account you@example.com ...`.

The plugin never contains OAuth credentials or tokens. `gog` stores and uses
them according to its own authentication configuration.

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
