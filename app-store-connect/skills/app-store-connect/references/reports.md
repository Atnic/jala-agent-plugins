# Reports and metrics

Find the specific action with `asc_find_actions`, using terms such as `salesReports`, `financeReports`, `analyticsReports`, or `powerMetrics`. These are separate Apple resources with different filters, report frequencies, and output formats.

For a report request, follow Apple's [Sales and Finance](https://developer.apple.com/documentation/appstoreconnectapi/sales-and-finance) and [Analytics Reports](https://developer.apple.com/documentation/appstoreconnectapi/downloading-analytics-reports) documentation for report availability and data definitions.

1. Confirm whether the user needs sales/trends, payments/financial, analytics, or performance data and select the matching API action.
2. Read the generated tool schema. Supply its required filters and report type exactly as documented; do not substitute an app's display name for its Apple ID.
3. Team keys can access Sales and Finance when their role permits it. Individual keys cannot access Sales and Finance. If Apple returns an authorization error, report the key-type/role limitation; do not attempt another credential source.
4. Analytics access also follows roles: Apple requires an Admin key to request a report type for the first time; after that, Sales and Reports or Finance roles can download the report. Sales and Reports does not grant access to the Finance Reports endpoint.
5. Binary report responses are saved under `~/Downloads/App Store Connect/` by default. Pass the action's optional absolute `outputFile` to choose another new filename. Existing files are never overwritten.
6. Read the downloaded file locally with a gzip- and tabular-data-aware parser. Summarize which period, territory, app, and report type the data covers. Preserve Apple's units and distinguish proceeds, downloads, subscriptions, and financial amounts; avoid dumping the full report into chat.

Analytics reports use a request → report → instance → segment workflow. When reading segment details, request Apple's `url`, `sizeInBytes`, and `checksum` fields; the server keeps the short-lived signed URL locally and replaces it with a reference to `asc_download_analytics_segment`. Download each segment promptly with that tool. The helper checks Apple's size and checksum when available and saves the compressed report locally without sending the App Store Connect JWT to report storage.

Do not imply that a missing report means zero sales. The endpoint's filters, availability delay, account role, and selected frequency can all affect the result.
