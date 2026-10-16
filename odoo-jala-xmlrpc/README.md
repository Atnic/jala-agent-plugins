# Odoo JALA XML-RPC

Version: `0.1.0`. Query models and perform authorized record and workflow changes
on JALA's Odoo instance through XML-RPC. Supports Codex and Claude Code with one
skill and a Python client. The existing [Odoo JALA Web](../odoo-jala-web/README.md)
plugin remains available for browser tasks and teaching personal workflows.

## Requirements and authentication

- Python 3.9+ and a host that can run local Python commands.
- Network access to `https://odoo.jala.tech` (the default instance).
- Odoo login and an API key or account password with access to the required
  models and records. JALA's database defaults to `jala_production`.
  Browser sign-in is separate.

Ask “Set up my Odoo connection.” The agent provides a command with the installed
client's absolute path. Install the native credential-store dependencies once,
then launch the local setup page:

```bash
python3 "<plugin-root>/skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py" install-runtime
python3 "<plugin-root>/skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py" setup-web
```

The page follows JALA's Odoo login styling, with the JALA logo, email field,
API key/password field, blue Connect button, and dark footer with copyright and
the white Odoo logo. There are no navigation menus or other links.
The database is selected automatically as `jala_production`,
without a database field. The page verifies authentication, then saves the
connection locally. Future sessions load
it automatically across Codex and Claude Code; no environment variables are
needed. Setup is launched explicitly and does not run during plugin installation.
Use `setup-web --no-open` to print a local link without opening a browser.
Opening `skills/odoo-jala-xmlrpc/assets/setup.html` directly provides a local
preview with both logos. Connecting and saving credentials requires the live
`setup-web` link; the direct-file preview disables submission.

Native storage uses macOS Keychain, Windows Credential Manager, or Linux Secret
Service through `keyring`. The private runtime is reused automatically when the
launching Python lacks `keyring`. Linux needs a running session D-Bus and Secret
Service provider. If native storage is unavailable, setup saves a **private,
unencrypted local file**, reported in the setup result. On macOS/Linux
it is `~/.config/odoo-jala-xmlrpc/connection.json`, with directory mode `700` and
file mode `600`. On Windows it is under `%LOCALAPPDATA%\odoo-jala-xmlrpc`, with
access restricted to the current user. Saved details remain outside the plugin
cache and survive plugin updates. The optional `ODOO_JALA_CONFIG_DIR` changes the
local state/runtime directory, not the OS credential-store entry.

The setup server listens only on loopback and requires a temporary session token.
New submissions expire after 15 minutes; an already-accepted connection check
finishes before the helper reports its result. The page masks the key, clears it after
success, and does not use browser storage. Never put secrets in chat or command
arguments. Run `setup-web` again to replace the saved connection, or `forget` to
remove the local connection without revoking the key in Odoo. If native storage
is inaccessible, `forget` removes the fallback file but reports that native
removal could not be confirmed.

Environment variables remain optional overrides: `ODOO_URL`, `ODOO_DB`,
`ODOO_USERNAME`, and `ODOO_API_KEY` (preferred) or `ODOO_PASSWORD`. A saved secret
is used only when the selected server, database, and login match its saved
identity. A normal interactive terminal can still prompt for an unsaved secret.
API calls and private-file storage work with the standard library alone; native
storage uses the bundled requirements installed by `install-runtime`. See the
[connection guide](skills/odoo-jala-xmlrpc/references/connection.md) for precedence
and authentication troubleshooting. The helper does not load `.env` files.

For the default JALA instance, the database is `jala_production`. An optional
`ODOO_URL` overrides the instance for explicitly requested alternate targets;
supply `--db` or `ODOO_DB` for a different database. The setup server binds the
chosen database before opening the form, and the form cannot change it.
HTTPS and normal certificate verification are required; loopback HTTP is allowed
for local testing. The repository identifies JALA's instance as Odoo 16; inspect
the actual version and custom fields before relying on them.

## Use

Invoke `$odoo-jala-xmlrpc` in Codex or
`/odoo-jala-xmlrpc:odoo-jala-xmlrpc` in Claude Code. Example requests:

- “Use Odoo XML-RPC to find purchase orders for this supplier.”
- “Set up my Odoo connection.”
- “Inspect the fields available on this JALA model.”
- “Discover the installed addons and explain JALA's purchase approval workflow.”
- “Update this contact's phone number and verify the result.”

The client is installed inside the skill; resolve `<plugin-root>` to the actual
checkout or installed plugin directory:

```bash
python3 "<plugin-root>/skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py" status
python3 "<plugin-root>/skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py" version
python3 "<plugin-root>/skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py" authenticate
python3 "<plugin-root>/skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py" discover --model account.move --model purchase.order
```

On Windows use `py -3` if needed. `status` checks configuration locally;
`version` contacts the server without credentials and skips saved connection
storage when a URL is supplied; `authenticate` returns the
authenticated user ID. The client does not install an MCP server or browser tool.

`discover` builds a private, account/company-scoped profile of visible installed
addons, dependencies, models, navigation, and requested model schemas/access
checks. Requested schemas are refreshed on every invocation; the base inventory
can be reused for 24 hours. Use `--refresh` after deployments or permission
changes, and `--company-id` to select an allowed company. Inaccessible or
truncated sections are reported explicitly. See the
[discovery guide](skills/odoo-jala-xmlrpc/references/discovery.md).

The skill includes a [JALA workflow map](skills/odoo-jala-xmlrpc/references/jala-source-map.md)
and a source-location index from the supplied `jala-odoo-custom-addons` repository:
104 selected addon manifests, including 63 `jala_` names, at revision
`2c1d9359124bbaee20c067c8cea455b4aed1d4b8`. These help connect Finance requests to
approval, expense settlement, budget, and accounting implementations. Discovery
matches installed names to source candidates; it does not prove the deployed
source revision. Schema inspection alone cannot establish workflow side effects,
so the skill directs the agent to inspect relevant implementations before using
custom business methods.

For a model call, write a JSON request such as:

```json
{"args": [[["is_company", "=", true]]], "kwargs": {"fields": ["id", "name"], "limit": 20, "order": "id asc"}}
```

Then execute it:

```bash
python3 "<plugin-root>/skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py" execute res.partner search_read --input request.json
```

Successful calls output JSON; failures output JSON on stderr and exit nonzero.
Use `--input -` for stdin. Create, update, delete, and unclassified methods need
`--allow-write` as an invocation guard. They execute immediately and remain subject
to Odoo access rules and the user's authorized scope. The client has no dry run
or rollback and makes no automatic retries. After an ambiguous result, inspect
record state before repeating a change. See the
[request guide](skills/odoo-jala-xmlrpc/references/requests.md) for discovery,
pagination, company context, relational fields, and writes.

## Try the local package

To try changes before they reach the GitHub marketplace's `main` branch,
register this checkout and install the package:

```bash
codex plugin marketplace add /absolute/path/to/jala-agent-plugins
codex plugin add odoo-jala-xmlrpc@jala-agent-plugins
```

For Claude Code:

```bash
claude plugin marketplace add /absolute/path/to/jala-agent-plugins
claude plugin install odoo-jala-xmlrpc@jala-agent-plugins
```

If that marketplace name already points to GitHub, follow the
[root local checkout instructions](../README.md#from-a-local-checkout) to resolve
the existing registration. Restart Codex or start a new task; for Claude Code,
start a new session or use `/reload-plugins`. Installation does not configure
the Odoo account. After publication, the same selectors work with the GitHub
marketplace described in the root README.

## Assets and validation

The Odoo wordmark assets are reused from `odoo-jala-web`, whose originals were
sourced from JALA's instance at `/web/static/img/odoo_logo.svg` and
`/web/static/img/odoo_logo_dark.svg`. Originals are kept in `assets/odoo-logo*.svg`;
display wrappers preserve the paths and proportions on a padded square canvas.
The setup page's JALA logo is copied from the public
[Odoo JALA login page](https://odoo.jala.tech/web/login), served there as
`/web/image/website/1/logo/My%20Website?unique=0f1209a`; its original JPEG is
bundled at `skills/odoo-jala-xmlrpc/assets/jala-logo.jpg`.
The footer reuses the original white Odoo wordmark, bundled inside the skill at
`assets/odoo-logo-dark.svg` for local serving.
Light and dark SVG render previews were inspected at 48, 128, and 512 pixels;
the installed host's icon display has not been tested.

The protocol follows the [official Odoo 16 External API documentation](https://www.odoo.com/documentation/16.0/developer/reference/external_api.html).
Local tests use an isolated XML-RPC server to check authentication, model calls,
write guards, saved credentials, the local setup form, failures, and no retry
after a lost response. Discovery tests cover scoped profiles, partial metadata
access, bounded pagination, cache freshness, and source matching.
Native credential-store behavior uses fake backends in
tests. They do not verify live OS credential-store integrations, JALA's endpoint,
credentials, access rules, custom model behavior, or host UI.
The setup page was checked in a browser at desktop and 390-pixel widths with
dummy credentials, including rejection, automatic database selection, and the
success state.

```bash
python3 -m unittest discover -s odoo-jala-xmlrpc/tests -v
python3 .agents/skills/create-plugin/scripts/validate_plugin.py odoo-jala-xmlrpc
```
