# Prepare a Google Cloud project and OAuth client

Use the email, client, and selected services determined by gog-setup.
The API and scope examples below cover `all-user`; for a selected service list,
filter them to those services using `gog auth services --json`.
For an IT-provided client, use this procedure only when project settings need
repair, with the owning administrator.

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

The user does not need to install `gcloud` on their computer. Run every
`gcloud` command only in the browser-based Cloud Shell; the local terminal is
for `gog` commands.

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
   `all-user`; it does not grant OAuth scopes. Google limits each call to 20
   services, so run both commands:

   ```bash
   gcloud services enable \
     analyticsadmin.googleapis.com analyticsdata.googleapis.com \
     calendar-json.googleapis.com chat.googleapis.com classroom.googleapis.com \
     docs.googleapis.com drive.googleapis.com driveactivity.googleapis.com \
     drivelabels.googleapis.com forms.googleapis.com gmail.googleapis.com \
   ```

   ```bash
   gcloud services enable \
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
6. **Add the OAuth scopes.** On the computer where Gog is installed, generate
   a paste-ready list of the standard user-service scopes (`all-user`):

   ```bash
   gog auth services --json | jq -r '.services[] | select(.user == true) | .scopes[] | select(startswith("https://"))' | sort -u
   ```

   This requires `jq`. The agent can run the command and show its output as a
   one-scope-per-line block for the user to copy. In the Google Auth Platform
   browser tab, open **Data Access → Add or remove scopes**, scroll to
   **Manually add scopes**, paste the entire block, then click **Add to table**
   and **Update**. Broad scopes may need Workspace admin approval or Google's
   OAuth verification, depending on the audience and publishing status.
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
   You can upload the JSON file to the agent or provide its local path. The agent
   uses the attachment's local path, or helps you save it on the machine running
   Gog before registration. Do not commit the file or print its secret contents.
   If reusing an existing `default` client for Gmail, skip client creation and
   use the project that owns that client for the API and Data Access steps.

