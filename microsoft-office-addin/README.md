# Microsoft Office for Codex

Connects Codex to the current workbook or document through an Office task pane.
The pane includes a chat composer, streaming replies, Markdown, visible reasoning summaries,
tool activity, approval requests, a stop button, and a saved conversation picker. It uses
a local `codex app-server` with the user’s existing Codex login and provider configuration.

The local MCP server serves the task pane over HTTPS, lists connected panes,
and routes a requested script to an explicitly selected document. The pane runs
that script in its Office.js context and returns JSON data or a structured error.

The add-in manifest currently targets Excel, Word, and PowerPoint. Outlook uses
a different add-in manifest and is not included in this package yet.

## Requirements

- Codex desktop or CLI running a local task. This plugin requires a local stdio
  MCP process and cannot run in a cloud-only session.
- Node.js 20.19.0 or newer and npm.
- For pane chat: a current Codex CLI that supports `codex app-server` and
  paginated thread history, signed in through Codex. Setup handles this through
  Codex; no API key needs to be pasted into the pane.
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

For everyday use, ask Codex **Start the Microsoft Office bridge**. The setup
skill recognizes this phrase, starts or reuses the bridge with
`office_list_documents`, and reports connected panes. It follows the setup flow
only when prerequisites are missing or installation is requested.

## Chat inside Office

After opening the pane, type a message in its composer. The **＋** button starts a
conversation; the picker resumes conversations created in Office. **More** and
**Load earlier messages** page through saved chats and history. **Stop** interrupts
the response; it cannot undo document changes already made. After a disconnection,
use **Reconnect** to resume the selected conversation. Closing the pane stops its
local chat process; saved history remains in Codex.

These are separate Codex threads, not a live mirror of the active desktop chat.
Click the folder chip above the composer to choose a project. Select a recent
folder, browse with **Home**, **Up**, and the folder list, or enter a full folder
path and press **Go**. Click **Use this folder** to start a new chat there.
**No project** uses the dedicated `~/.codex/office-chats` folder. The folder browser
uses the bridge's filesystem on macOS, Windows, and Linux; no native folder
dialog or shell helper is required. Windows drive and UNC paths can be entered
directly. Folder shortcuts combine recent Office choices with folders from
recent Codex chats; they are not a synchronized copy of the desktop sidebar.

Changing projects starts a new chat and keeps the previous conversation saved.
New panes open in the most recently used available project. Chat history is
scoped to Office-created conversations in the selected folder; choosing a
previous project lets you resume its chats. Resume restores the chat's original
working folder and project instructions. The bridge records recent choices,
the last folder, and Office thread IDs in `~/.codex/office-chats/projects.json`.
History is stored by Codex, not in browser storage or a transcript file maintained
by this plugin. Resuming a conversation binds its Office tool to the **currently open pane**,
so historical references to an older document should be checked before editing.

The chat inherits the local Codex account, model, provider, and available tools.
It starts and resumes Office threads with full filesystem/network access and
the `never` approval policy. This preference applies to Office chats only;
managed Codex policies still apply. The pane renders command and file approvals,
permission requests, user questions, and simple MCP forms. Unsupported forms can
be declined. It displays published reasoning summaries, not private reasoning.
Ordinary Office actions still run through the existing JavaScript bridge.

The brain button opens model and reasoning effort choices from App Server's
`model/list` catalog. Choices apply when sending the next message and persist
for subsequent turns in that chat. The paperclip button attaches up to five files
per message, totaling at most 10 MB. PNG, JPEG, WebP, and GIF images are passed as
image input; other files are made available to Codex through their local paths.
Files are copied on send to `~/.codex/office-chats/uploads/`, with generated
subdirectories and private file permissions. They remain there so saved chats
can reference them; remove that directory manually when those files are no
longer needed. File format support depends on the chosen model and local tools.

Set `OFFICE_CODEX_BIN` in the bridge process environment if `codex` is not on PATH.
On Windows, both a native executable and the npm `codex.cmd` shim are supported.
The CLI is launched on demand when a pane connects to chat. Credentials stay with
Codex and are never sent to the Office webview. The bridge must stay running while
the pane is in use; installing the add-in alone does not start a background service.

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


Version 0.2.0 chat was exercised with a real local Codex app-server and a browser
with simulated Office.js: streaming, approval, a round trip through the Office
script tool, saved-history resume, and 270 px light/dark layouts. The chat UI has
not yet been exercised inside real Office hosts or on Windows/Linux. `npm test`
runs the deterministic protocol and approval regression checks without model calls.


The task-pane theme follows the supplied Codex desktop reference: separate canvas,
context strip, and composer surfaces; a centered welcome state; a compact chat
menu; a folder project picker; and collapsible activity rows. A brain icon opens the model/effort picker,
and a paperclip opens the file picker. The access label is hidden. Voice is not
implemented. UI icons are supplied by Lucide. The welcome mark
is adapted from LobeHub’s Codex SVG (MIT; see `assets/codex-mark-LICENSE.txt`).
