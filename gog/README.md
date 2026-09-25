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
comes with `gcloud` installed and signed in. Create a project, or skip the first
command if you already have one, then select its unique project ID:

```bash
gcloud projects create YOUR_UNIQUE_PROJECT_ID --name="Gog CLI"
gcloud config set project YOUR_UNIQUE_PROJECT_ID
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

### Create the OAuth client ID and secret

In the same project, open [Google Auth platform](https://console.cloud.google.com/auth/overview):

1. Configure **Branding** and **Audience**. Choose **Internal** for an eligible
   Workspace organization or **External** for a personal Google Account. If the
   app is External and in Testing, add your account under **Audience → Test users**.
   [Testing refresh tokens for user-data scopes expire after seven days](https://support.google.com/cloud/answer/15549945).
2. Under **Data Access**, add the scopes for the services you intend to use.
   For the broad `all-user` setup below, use `gog auth services --markdown` to
   inspect Gog's supported user scopes. Broad access can include sensitive or
   restricted scopes that require Google review for wider use.
3. Under **Clients**, choose **Create client → Desktop app**, then download its
   JSON file. That file contains the client ID and client secret. Keep it out of
   this repository.

The Desktop OAuth client is created in the Cloud Console; the Cloud Shell
commands above create/select the project and enable its APIs.

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
