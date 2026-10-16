# Connection

Commands below use `<client>` for the installed absolute path to
`scripts/odoo_rpc.py` in this skill. Global options precede the subcommand.
Windows may use `py -3` instead of `python3`.

## Set up once with the local page

```bash
python3 "<client>" install-runtime
python3 "<client>" setup-web
```

`install-runtime` installs `keyring` and Linux's `SecretStorage` dependency in a
private per-user Python environment. The client reuses that runtime automatically
when the launching interpreter lacks `keyring`. Environment-only API requests
and private-file storage use Python 3.9+'s standard library.

For agent-assisted setup, resolve the client path, install the runtime when
needed, and start `setup-web --no-open` in a long-running shell session. Give the
user the printed loopback link; use the host's browser-opening capability when
available. Keep the server alive while they connect. The user supplies their
Odoo email/login and API key or password directly in the masked local form.
The JALA database is selected automatically as `jala_production`, with no database
field. For an explicitly requested alternate instance, supply `--db` or `ODOO_DB`
before opening the form, or reuse that instance's saved database. The setup server
binds the target URL and database; neither can be changed by a form submission.
A browser/SSO session
does not authenticate XML-RPC. Never ask for the key in chat, fill it yourself,
or read saved credential contents into tool output.

The form tests authentication before saving. A failed test leaves the previous
connection unchanged. The server binds to `127.0.0.1`, validates its Host,
Origin, and session token, and expires after 15 minutes or a successful save.
The page keeps secrets out of URLs and browser storage and clears the field
after success. OS credential-store access or unlock prompts are handled by the
user. Run `status` and `authenticate` after setup to verify readiness, then
`discover` to bootstrap the read-only instance profile. Report any metadata the
account cannot access; see [discovery.md](discovery.md).

## Saved connection

The whole connection is saved under service `tech.jala.odoo.xmlrpc`, account
`connection`, using macOS Keychain, Windows Credential Manager, or Linux Secret
Service. Linux needs session D-Bus and an available Secret Service provider.
If the native store is unavailable, a **private, unencrypted file** is used;
the success message reports this.

Default file/runtime locations:

- macOS/Linux: `~/.config/odoo-jala-xmlrpc/` (directory `700`, credential file `600`).
- Windows: `%LOCALAPPDATA%\odoo-jala-xmlrpc\`, with the credential file restricted
  to the current Windows user.

`ODOO_JALA_CONFIG_DIR` overrides this state/runtime directory. The native-store
service/account stays the same. Details live outside the plugin cache, survive
updates, and are shared by Codex and Claude Code on the same OS user account.
One saved connection is supported. Run `setup-web` again to replace it.

A fallback file takes precedence because it may be newer than a locked native
copy. A verified native save removes the obsolete fallback file. Use `status`
to see readiness and `secret_source` without exposing the secret. Use `forget`
to remove the saved connection locally; it does not revoke the Odoo key or clear
environment overrides. If native removal cannot be confirmed, the fallback file
is removed but the command reports failure so the remaining native copy is
accounted for.

## Optional overrides and troubleshooting

| Setting | Meaning |
| --- | --- |
| `ODOO_URL` | Base URL; defaults to JALA for an independent environment connection, otherwise uses the saved URL or `https://odoo.jala.tech`. |
| `ODOO_DB` | Optional database override; JALA defaults to `jala_production`. |
| `ODOO_USERNAME` | Odoo login. |
| `ODOO_API_KEY` | API key; takes precedence over `ODOO_PASSWORD` and the saved secret. |
| `ODOO_PASSWORD` | Password alternative; takes precedence over the saved secret. |

`--url`, `--db`, and `--username` override their environment and saved settings.
A supplied login and environment API key/password can connect independently of
saved storage. Without target overrides, that connection uses
`https://odoo.jala.tech` and `jala_production`; supply the URL and database to
select an alternate target. An environment secret alone can still override the
key for the saved connection.
JALA uses `jala_production` when no explicit database override is supplied,
including when an older saved JALA connection points to another database.
The saved secret is used only for the same normalized URL, database, and login.
For a changed identity, supply its own environment secret or run setup for that
connection. The CLI accepts `--timeout` in seconds (default 30). HTTPS with normal
certificate verification is required; HTTP is permitted only on loopback.

There is no command-line secret flag and `.env` files are not loaded. An
interactive terminal prompts with hidden input when no matching saved or
environment secret exists; that prompt does not save the secret. With stdin
JSON requests, use saved credentials or the environment. Environment variables
must be present in the executing process; exports in another terminal do not
update an already-running desktop app.

`status` does not contact Odoo. `version` calls `/xmlrpc/2/common` without sending
credentials; an explicitly supplied URL also skips saved connection storage.
`authenticate` calls `authenticate(db, login, secret, {})` and returns
a user ID. Model calls use `/xmlrpc/2/object` and `execute_kw`. An API key replaces
the password in both authenticated calls; the login is still required.

For authentication errors, check the exact database/login, API access, and key
validity with the administrator. For permission errors, check model access,
record rules, and company scope. Keep those protections in place. Failures use
a nonzero exit status and sanitized JSON on stderr; remote tracebacks and keys
are not printed. No RPC is retried automatically. Inspect affected records
before repeating an operation with an uncertain result.

Protocol reference: [Odoo 16 External API](https://www.odoo.com/documentation/16.0/developer/reference/external_api.html).
