# Model requests

Call `python3 "<client>" execute MODEL METHOD --input request.json`. The input
is a UTF-8 JSON object with `args` (array, default `[]`) and `kwargs` (object,
default `{}`). Use `--input -` to read it from stdin. Use temporary payload files
outside the repository for private record data. The helper returns the raw RPC
result as JSON; binary values are represented as `{"base64": "..."}`. This release
is read-only; the helper accepts only the methods listed below.

Allowed methods: `search`, `search_read`, `search_count`, `read`, `fields_get`,
`name_get`, `name_search`, `read_group`, and `check_access_rights`.

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
shared records can have `company_id: false`. Company-dependent fields follow the
context's current company.

Use `false` for unset Odoo fields, not JSON `null`. Many2one reads commonly return
`[id, display_name]` or `false`. One2many and many2many reads return related IDs;
inspect those records with another allowed read when needed. Datetime field strings use Odoo's
server format and UTC semantics; convert the user's time explicitly.

## Read-only scope

`create`, `write`, `unlink`, posting, approval, payment, sending, and all methods
outside the read list are rejected before authentication. There is no
`--allow-write` override. Custom reports are also blocked unless they use a listed
read method. If a request needs an unsupported method, explain the limitation and
continue supported reads; keep this release's read-only constraint in place.

The filter restricts method names, not Odoo's implementation of them. Custom
overrides may have side effects on a method named `read`; a read-only Odoo account
provides server-side access restrictions. Current role and record rules still apply.

Protocol reference: [Odoo 16 External API](https://www.odoo.com/documentation/16.0/developer/reference/external_api.html).
