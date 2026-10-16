# Model requests

Call `python3 "<client>" execute MODEL METHOD --input request.json`. The input
is a UTF-8 JSON object with `args` (array, default `[]`) and `kwargs` (object,
default `{}`). Use `--input -` to read it from stdin. Use temporary payload files
outside the repository for private record data. The helper returns the raw RPC
result as JSON; binary values are represented as `{"base64": "..."}`.

## Discover and read

Start with the scoped `discover --model MODEL` profile described in
[discovery.md](discovery.md). The individual calls below support focused
follow-up inspection and record queries.

Find model names through `ir.model search_read` (subject to access rules):

```json
{"args": [[["model", "ilike", "purchase"]]], "kwargs": {"fields": ["model", "name"], "limit": 20, "order": "id asc"}}
```

Inspect a candidate model with `MODEL fields_get`:

```json
{"args": [], "kwargs": {"attributes": ["string", "type", "required", "readonly", "relation", "selection"]}}
```

Query contacts with `res.partner search_read`:

```json
{"args": [[["is_company", "=", true]]], "kwargs": {"fields": ["id", "name", "company_id"], "limit": 50, "offset": 0, "order": "id asc"}}
```

Increment `offset` to paginate; stop when a page is shorter than `limit`. Concurrent
changes can shift offset pages: for a stable export prefer an `id > last_id`
domain with `id asc`. Explicitly check task completeness rather than assuming
the first page is all records. `search_count` can count a matching domain, but
count and data may change between calls.

Read known IDs with `MODEL read`:

```json
{"args": [[123]], "kwargs": {"fields": ["id", "name", "company_id"]}}
```

`123` is illustrative; resolve actual IDs before acting. A domain is the first
positional argument for search methods, so an empty domain is `"args": [[]]`.
Odoo domain operators such as `"|"`, `"&"`, and `"!"` use prefix notation.

## Company and value semantics

Pass context inside kwargs on each relevant call:

```json
{"args": [[123]], "kwargs": {"fields": ["name", "company_id"], "context": {"allowed_company_ids": [7], "lang": "en_US", "tz": "Asia/Jakarta"}}}
```

Resolve allowed company IDs from the user's records or known configuration;
the example ID is not JALA configuration. Context cannot grant access. Include
an explicit `company_id` domain when the task calls for company-owned records;
shared records can have `company_id: false`. Creation may also require an explicit
company value. Company-dependent fields follow the context's current company.

Use `false` for unset Odoo fields, not JSON `null`. Many2one reads commonly return
`[id, display_name]` or `false`; write a numeric ID or `false`. One2many and
many2many writes use Odoo command arrays; for example `[[6, 0, [10, 11]]]`
**replaces** the relation set, while `[[4, 10, 0]]` adds a link. Inspect the field
and current links before selecting a command. Datetime field strings use Odoo's
server format and UTC semantics; convert the user's time explicitly.

## Changes and workflow methods

Add `--allow-write` for the following examples. This does not simulate or preview
the operation: it executes it. The client's read-method list is an accident guard;
custom Odoo overrides may have side effects even on a method named `read`.

| Call | Input |
| --- | --- |
| `res.partner create` | `{"args": [{"name": "User-approved contact"}]}` |
| `res.partner write` | `{"args": [[123], {"phone": "+62..."}]}` |
| `res.partner unlink` | `{"args": [[123]]}` |

`create` returns the new ID (or IDs for a supported batch); `write` and `unlink`
normally return true. Read back the new/updated record, or confirm a deleted ID
is absent. `unlink` deletes; use the model's supported archive behavior when the
request is to archive instead. Readonly/computed fields and constraints can
reject values even when their JSON shape is valid.

Public custom methods use the same positional and keyword envelope. Establish
their contract and business effect before invoking them. Workflow methods may
send messages or create accounting effects; keep them within the user's requested
outcome. Split large jobs into reviewable batches and reconcile a failed or
ambiguous batch before resuming. The helper provides no dry run or rollback.

Protocol and field-command reference: [Odoo 16 External API](https://www.odoo.com/documentation/16.0/developer/reference/external_api.html).
