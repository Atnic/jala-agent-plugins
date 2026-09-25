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

### Create a Google Cloud project and enable APIs

Open [Google Cloud Shell](https://shell.cloud.google.com/) in your browser. It
comes with `gcloud` installed and signed in. You can use an existing project:
select it in the Cloud Console project picker and use its **Project ID** (not
the display name). If creating a project, choose a name such as `Gog CLI`; the
console suggests a Project ID. Use that suggestion or choose a unique ID that
is 6–30 characters, starts with a lowercase letter, and contains only lowercase
letters, numbers, and hyphens. Project IDs are globally unique and permanent
after creation. In the Cloud Console project picker, open the project's
Dashboard to find its Project ID. If you use the commands below, replace
`YOUR_UNIQUE_PROJECT_ID` with that ID. For example, `jala-gog-2026` is a valid
shape if it is available. For a new project, run both commands:

```bash
gcloud projects create YOUR_UNIQUE_PROJECT_ID --name="Gog CLI"
gcloud config set project YOUR_UNIQUE_PROJECT_ID
```

For an existing project, skip `gcloud projects create` and run only:

```bash
gcloud config set project EXISTING_PROJECT_ID
```

Enabling APIs is separate from granting OAuth scopes. To enable every API in
Gog's standard `all-user` service set for this project, run this in Cloud Shell:

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

You can check enabled APIs with `gcloud services list --enabled`. Gog derives
this API list from its selected services; run `gog auth setup --help` if your
installed CLI offers a different service set.

### Configure OAuth branding, audience, and scopes

In the same project, open [Google Auth Platform](https://console.cloud.google.com/auth/overview).
Complete these settings before creating a client:

1. Under **Branding**, fill **App name** (for example, `Gog CLI`), **User
   support email**, and **Developer contact information**, then save. A logo is
   optional. External apps published to production also need a verified
   homepage and privacy policy. See Google's [branding guide](https://support.google.com/cloud/answer/15549049?hl=en).
2. Under **Audience**, choose **Internal** if this project belongs to JALA's
   Google Cloud organization and only JALA Workspace accounts will use it. If
   Internal is unavailable, ask a Workspace/Cloud administrator to create or
   move the project into the organization. Otherwise choose **External**. For
   an External app left in **Testing**, add each account under **Test users**;
   Google says authorizations for user-data scopes in Testing expire after
   seven days. See Google's [audience guide](https://support.google.com/cloud/answer/15549945?hl=en).
3. Under **Data Access**, click **Add or remove scopes**. On the machine where
   Gog is installed, run `gog auth services --markdown` and add the scopes for
   `all-user`, the full default set of Gog user services. Save the scope list.
   Broad scopes may need Workspace admin approval or Google's OAuth
   verification, depending on the audience and publishing status.

### Create and download the OAuth client JSON

1. In Google Auth Platform, open **Clients → Create client**, choose
   **Desktop app**, enter a credential name such as `Gog CLI desktop`, and
   click **Create**. A desktop client needs no redirect URI configuration.
2. In the creation dialog, download the client configuration JSON. If you
   already closed it, open **APIs & Services → Credentials**, select the
   Desktop app client under **OAuth 2.0 Client IDs**, and click **Download
   JSON**. Save it on the computer where Gog is installed, for example in
   `Downloads`. Google's [credential guide](https://developers.google.com/workspace/guides/create-credentials)
   documents the Desktop app client flow and JSON download.
3. Keep this file private. It contains the OAuth client configuration (and may
   contain a client secret); do not commit it or paste its contents into chat.

Project creation and API enablement happen in Cloud Shell. Branding, audience,
scopes, and OAuth client creation happen in Google Auth Platform. Download the
client JSON to the local machine where the Gog CLI and agent run.

### Connect an account on the machine running the agent

Follow the upstream [quickstart](https://github.com/openclaw/gogcli/blob/main/docs/quickstart.md)
to store the downloaded JSON and complete browser consent. Run these commands
on the machine where `gog` is installed for your agent, rather than in Cloud
Shell:

```text
gog auth credentials set "PATH_TO_CLIENT_SECRET_JSON" --client jala-workspace
gog auth add you@example.com --services all-user --client jala-workspace
gog auth list --check
```

Replace `PATH_TO_CLIENT_SECRET_JSON` with the path to the downloaded OAuth
client JSON file on your system. Give each OAuth client a name with `--client`;
this lets you use a different client without replacing the credentials selected
as `default`. Use the same name for `auth credentials set` and `auth add`.

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
