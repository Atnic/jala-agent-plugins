import { createServer, request as httpsRequest } from "node:https";
import { readFile } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";
import { homedir } from "node:os";
import { WebSocketServer, WebSocket } from "ws";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { CodexChat } from "./codex-chat.mjs";

const root = resolve(fileURLToPath(new URL(".", import.meta.url)));
const host = process.env.OFFICE_BRIDGE_HOST ?? "localhost";
const port = Number(process.env.OFFICE_BRIDGE_PORT ?? 43187);
const origin = `https://${host}:${port}`;
const maxScriptChars = 32_000;
const requestTimeoutMs = 120_000;
const panes = new Map();
const pending = new Map();
const chats = new Map();
const chatOwners = new Map();

const certDirectory = process.env.OFFICE_BRIDGE_CERT_DIR ?? resolve(homedir(), ".office-addin-dev-certs");
let httpsOptions;
let server;
let wsServer;
let bridgeStartPromise;

function createBridgeServer() {
  const createdServer = createServer({ key: httpsOptions.key, cert: httpsOptions.cert }, async (req, res) => {
  const url = new URL(req.url ?? "/", origin);
  if (req.method === "GET" && url.pathname === "/bridge/health") {
    return sendJson(res, 200, { ok: true, connectedPanes: listPanes() });
  }
  if (req.method === "GET" && url.pathname === "/bridge/panes") {
    return sendJson(res, 200, { panes: listPanes() });
  }
  if (req.method === "POST" && url.pathname === "/bridge/execute") {
    try {
      const body = await readJson(req);
      if (typeof body.documentId !== "string" || typeof body.script !== "string") {
        return sendJson(res, 400, { ok: false, error: { name: "InvalidRequest", message: "Provide documentId and script strings." } });
      }
      if (!body.script.trim() || body.script.length > maxScriptChars) {
        return sendJson(res, 400, { ok: false, error: { name: "InvalidScript", message: `Script must contain 1 to ${maxScriptChars} characters.` } });
      }
      const pane = panes.get(body.documentId);
      if (!pane || pane.socket.readyState !== WebSocket.OPEN) {
        return sendJson(res, 404, { ok: false, error: { name: "DocumentUnavailable", message: "No connected Office pane has that documentId. Call office_list_documents to refresh the list." } });
      }
      const requestId = randomUUID();
      const result = await new Promise((resolvePromise, rejectPromise) => {
        const timer = setTimeout(() => {
          pending.delete(requestId);
          rejectPromise(Object.assign(new Error(`Office task pane did not respond within ${requestTimeoutMs / 1000} seconds.`), { name: "OfficeTimeout" }));
        }, requestTimeoutMs);
        pending.set(requestId, { pane, resolve: resolvePromise, reject: rejectPromise, timer });
        pane.socket.send(JSON.stringify({ type: "execute", requestId, documentId: pane.documentId, script: body.script }));
      });
      return sendJson(res, 200, { ok: true, requestId, documentId: pane.documentId, result });
    } catch (error) {
      const status = error.name === "OfficeTimeout" ? 504 : error.name === "RequestTooLarge" ? 413 : 400;
      return sendJson(res, status, { ok: false, error: { name: error.name ?? "Error", message: error.message ?? String(error) } });
    }
  }

  const assetPath = url.pathname === "/" ? "/index.html" : url.pathname;
  const absolutePath = resolve(root, `.${decodeURIComponent(assetPath)}`);
  if (absolutePath !== root && !absolutePath.startsWith(`${root}${sep}`)) return sendText(res, 400, "Invalid path");
  try {
    const content = await readFile(absolutePath);
    const contentType = extname(absolutePath) === ".html" ? "text/html; charset=utf-8"
      : extname(absolutePath) === ".js" ? "text/javascript; charset=utf-8"
        : extname(absolutePath) === ".css" ? "text/css; charset=utf-8"
        : extname(absolutePath) === ".svg" ? "image/svg+xml"
        : extname(absolutePath) === ".png" ? "image/png" : "application/octet-stream";
    res.writeHead(200, { "content-type": contentType, "cache-control": "no-store", "x-content-type-options": "nosniff" });
    res.end(content);
  } catch {
    sendText(res, 404, "Not found");
  }
  });

  const createdWsServer = new WebSocketServer({ noServer: true, maxPayload: 64 * 1024 });
  const chatServer = new WebSocketServer({ noServer: true, maxPayload: 15 * 1024 * 1024 });
  createdServer.on("upgrade", (req, socket, head) => {
  const url = new URL(req.url ?? "/", origin);
  if (url.pathname === "/chat/ws" && req.headers.origin === origin && panes.has(url.searchParams.get("documentId"))) {
    chatServer.handleUpgrade(req, socket, head, (ws) => {
      const chat = new CodexChat({ root, port, certDirectory, owners: chatOwners, documentId: url.searchParams.get("documentId"), send: (message) => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message)); } });
      chats.set(chat, ws);
      let ready = false;
      ws.on("message", async (data) => {
        try {
          if (!ready) throw new Error("Codex is still connecting.");
          await chat.handle(JSON.parse(data.toString()));
        } catch (error) { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "error", message: error.message })); }
      });
      ws.on("close", () => { chat.close(); chats.delete(chat); });
      ws.on("error", () => { chat.close(); chats.delete(chat); });
      chat.start().then(() => { ready = true; }).catch(error => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "fatal", message: error.message })); chat.close(); });
    });
    return;
  }
  if (url.pathname !== "/bridge/ws" || req.headers.origin !== origin) {
    socket.write("HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n");
    socket.destroy();
    return;
  }
  const documentId = url.searchParams.get("documentId");
  const officeHost = url.searchParams.get("officeHost");
  const platform = url.searchParams.get("platform");
  if (!documentId || !officeHost || !platform || documentId.length > 128) {
    socket.write("HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n");
    socket.destroy();
    return;
  }
    createdWsServer.handleUpgrade(req, socket, head, (ws) => createdWsServer.emit("connection", ws, req, { documentId, officeHost, platform }));
  });
  return { server: createdServer, wsServer: createdWsServer };
}

function registerPaneConnections() {
wsServer.on("connection", (socket, _req, metadata) => {
  const previous = panes.get(metadata.documentId);
  if (previous) previous.socket.close(1000, "Replaced by a newer connection for this document.");
  const pane = { ...metadata, socket, connectedAt: new Date().toISOString() };
  panes.set(pane.documentId, pane);
  socket.send(JSON.stringify({ type: "connected", documentId: pane.documentId }));
  socket.on("message", (data) => receivePaneMessage(pane, data.toString()));
  socket.on("close", () => disconnectPane(pane));
  socket.on("error", () => disconnectPane(pane));
});
}

const mcp = new McpServer({ name: "microsoft-office-addin", version: "0.2.0" }, {
  instructions: "Use office_list_documents first. It lists open task panes, not all files on disk. Select the target documentId explicitly before calling office_run_script. Scripts execute in that Office task pane with Office.js and unrestricted ambient JavaScript capabilities. Read the document before changing it when the request is ambiguous, and return a concise summary of what changed.",
});

mcp.registerTool("office_list_documents", {
  title: "List connected Office documents",
  description: "Lists Excel, Word, and PowerPoint task panes currently connected to the local Office bridge. Use this before choosing a document to inspect or edit.",
  inputSchema: {},
  annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
}, async () => {
  try {
    await ensureBridgeStarted();
  } catch (error) {
    return { isError: true, content: [{ type: "text", text: `Office bridge is not ready: ${error.message}. Ask Codex to set up Codex for Microsoft Office.` }] };
  }
  const documents = listPanes();
  return { structuredContent: { documents }, content: [{ type: "text", text: documents.length ? JSON.stringify(documents, null, 2) : "No Office task panes are connected. Open the Microsoft Office add-in pane in a document and try again." }] };
});

mcp.registerTool("office_run_script", {
  title: "Run Office.js script in a document",
  description: "Runs arbitrary JavaScript in the selected connected Excel, Word, or PowerPoint task pane. Bindings available: Office, Excel, Word, PowerPoint, and globalThis. Use the Office.js run/context/sync pattern appropriate to the host. The script can read or modify that document, and has the task pane's ordinary JavaScript access; it is not sandboxed. Return a JSON-serializable value. Always pass a documentId from office_list_documents.",
  inputSchema: {
    documentId: z.string().min(1).describe("The exact documentId returned by office_list_documents."),
    script: z.string().min(1).max(maxScriptChars).describe("Async JavaScript function body executed in the Office task pane. Return JSON-serializable data."),
  },
  annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
}, async ({ documentId, script }) => {
  try {
    await ensureBridgeStarted();
  } catch (error) {
    return { isError: true, content: [{ type: "text", text: `Office bridge is not ready: ${error.message}. Ask Codex to set up Codex for Microsoft Office.` }] };
  }
  const response = await bridgeRequest("/bridge/execute", { documentId, script });
  if (!response.ok) return { isError: true, structuredContent: { error: response.error }, content: [{ type: "text", text: `${response.error.name}: ${response.error.message}` }] };
  return { structuredContent: response, content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
});

await mcp.connect(new StdioServerTransport());
ensureBridgeStarted().catch(() => {});

async function ensureBridgeStarted() {
  if (server?.listening) return;
  if (bridgeStartPromise) return bridgeStartPromise;
  bridgeStartPromise = (async () => {
    const [ca, cert, key] = await Promise.all([
      readFile(resolve(certDirectory, "ca.crt")),
      readFile(resolve(certDirectory, "localhost.crt")),
      readFile(resolve(certDirectory, "localhost.key")),
    ]);
    httpsOptions = { ca, cert, key };
    const bridge = createBridgeServer();
    server = bridge.server;
    wsServer = bridge.wsServer;
    registerPaneConnections();
    await new Promise((resolvePromise, rejectPromise) => {
      server.once("error", rejectPromise);
      server.listen(port, host, () => {
        server.off("error", rejectPromise);
        console.error(`Codex for Microsoft Office bridge listening at ${origin}`);
        resolvePromise();
      });
    });
  })().catch((error) => {
    bridgeStartPromise = undefined;
    throw new Error(`could not read or start the localhost certificate at ${certDirectory} (${error.message})`);
  });
  return bridgeStartPromise;
}

function listPanes() {
  return [...panes.values()].filter((pane) => pane.socket.readyState === WebSocket.OPEN).map(({ documentId, officeHost, platform, connectedAt }) => ({ documentId, host: officeHost, platform, connectedAt }));
}

function receivePaneMessage(pane, raw) {
  let message;
  try { message = JSON.parse(raw); } catch { return; }
  if (message.type !== "result" || typeof message.requestId !== "string") return;
  const item = pending.get(message.requestId);
  if (!item || item.pane !== pane) return;
  clearTimeout(item.timer);
  pending.delete(message.requestId);
  if (message.ok) item.resolve(message.result);
  else item.reject(Object.assign(new Error(message.error?.message ?? "Office script failed."), { name: message.error?.name ?? "OfficeScriptError" }));
}

function disconnectPane(pane) {
  if (panes.get(pane.documentId) !== pane) return;
  panes.delete(pane.documentId);
  for (const [requestId, item] of pending) {
    if (item.pane === pane) {
      clearTimeout(item.timer);
      pending.delete(requestId);
      item.reject(Object.assign(new Error("Office task pane disconnected during execution."), { name: "OfficeDisconnected" }));
    }
  }
}

async function bridgeRequest(path, body) {
  const payload = JSON.stringify(body);
  return await new Promise((resolvePromise, rejectPromise) => {
    const req = httpsRequest(`${origin}${path}`, {
      method: "POST",
      ca: httpsOptions.ca,
      headers: { "content-type": "application/json", "content-length": Buffer.byteLength(payload) },
    }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        try { resolvePromise(JSON.parse(Buffer.concat(chunks).toString("utf8"))); }
        catch (error) { rejectPromise(error); }
      });
    });
    req.setTimeout(requestTimeoutMs + 5_000, () => req.destroy(new Error("Office bridge HTTP request timed out.")));
    req.on("error", rejectPromise);
    req.end(payload);
  });
}

async function readJson(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 64 * 1024) throw Object.assign(new Error("Request body exceeds the 64 KB limit."), { name: "RequestTooLarge" });
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function sendJson(res, status, value) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
  res.end(JSON.stringify(value));
}

function sendText(res, status, value) {
  res.writeHead(status, { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" });
  res.end(value);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
async function shutdown() {
  for (const [chat, ws] of chats) { chat.close(); ws.close(1001, "Codex bridge stopping."); }
  for (const pane of panes.values()) pane.socket.close(1001, "Codex bridge stopping.");
  await mcp.close().catch(() => {});
  if (!server) process.exit(0);
  server.close(() => process.exit(0));
}
