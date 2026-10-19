# Microsoft Office for Codex

Connects Codex to the current workbook or document through an Office task pane.
The local MCP server serves the task pane over HTTPS, lists connected panes,
and routes a requested script to an explicitly selected document. The pane runs
that script in its Office.js context and returns JSON data or a structured error.

The add-in manifest currently targets Excel, Word, and PowerPoint. Outlook uses
a different add-in manifest and is not included in this package yet.

## Requirements

- Codex desktop or CLI running a local task. This plugin requires a local stdio
  MCP process and cannot run in a cloud-only session.
- Node.js 20 or newer and npm.
- Microsoft Word, Excel, or PowerPoint with Office Add-ins enabled.
- A trusted localhost development certificate. Ask Codex to **set up Microsoft
  Office for Codex**; the setup skill prepares Microsoft's local development
  certificate and sideloads the manifest on macOS, Windows, and Linux (Office on
  the web for Linux). Certificate installation may show an operating system
  trust prompt. See Microsoft's [Office Add-in
  development certificate guide](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/yeoman-generator-overview).
  Set `OFFICE_BRIDGE_CERT_DIR` in Codex's process environment to use another
  certificate location.

## Install and run

Register this repository's Codex marketplace and install the plugin as
described in the root README. Then ask Codex: **Set up Microsoft Office for
Codex.** The setup skill prepares the local certificate and sideloads the
manifest into Word, Excel, and PowerPoint on macOS and Windows, and uses the
Office on the web flow on Linux. Restart the Office app if it was already open,
then open the **Microsoft Office for Codex** task pane. Microsoft documents
[Mac sideloading](https://learn.microsoft.com/en-us/office/dev/add-ins/testing/sideload-an-office-add-in-on-mac) and the [Office Add-in Debugging tool](https://github.com/OfficeDev/Office-Addin-Scripts/tree/master/packages/office-addin-debugging).
Linux has no Office desktop host, so the setup skill opens Office on the web
and may require the user to sign in to Microsoft 365 in the browser.

Open the add-in pane in a document. The Codex MCP process installs runtime
dependencies on first use and starts the HTTPS bridge once the certificate is
available. The pane retries automatically until that bridge is ready. Use
`office_list_documents` to confirm connection and choose a document. If another
process is already using port 3000, set `OFFICE_BRIDGE_PORT` for the Codex MCP
process and update the URLs in `manifest.xml` to the same port before
sideloading.

## Tools

- `office_list_documents` reports connected task panes, each with a stable
  document ID for that pane session, host, platform, and connection time. Call
  it before acting, then use the returned `documentId` explicitly.
- `office_run_script` sends an async JavaScript function body to that document's
  task pane. The script receives `Office`, `Excel`, `Word`, `PowerPoint`,
  `Outlook`, and `globalThis`; return a JSON-serializable result. Use the
  host-specific Office.js API and its `run`/context/`sync` pattern.

Example Excel script:

```js
return await Excel.run(async (context) => {
  const range = context.workbook.getSelectedRange();
  range.load(["address", "values"]);
  await context.sync();
  return { address: range.address, values: range.values };
});
```

## Script execution and data handling

Scripts run with the task pane's regular JavaScript capabilities. The runner is
not a sandbox, does not restrict scripts to Office.js calls, and cannot undo a
document edit automatically. A script may read or modify the selected document
and may use other JavaScript APIs available to the pane. Codex should inspect
the target document and follow the user's request before writing. Do not run
untrusted scripts.

The local server binds to `localhost`, checks the task pane's exact WebSocket
origin, limits script input to 32,000 characters, result data to 50,000
characters, and pending execution to two minutes. These are local development
guardrails, not a production security boundary or a substitute for sandboxing.
Document contents and script results are sent to the local Codex process over
the loopback connection. The plugin does not send document data to a hosted
service.

## Current scope

Excel and Word were exercised with real Office task panes on macOS in the
prototype. The package adds a real stdio MCP server and a PowerPoint manifest
entry, but the packaged MCP flow, clean first-time sideload, Windows, and
PowerPoint have not yet been validated end to end. API availability depends on
the host and its Office.js requirement sets. Outlook needs its own manifest and
host-specific tests.
