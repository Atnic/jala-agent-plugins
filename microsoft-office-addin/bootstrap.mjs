import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const packageRoot = fileURLToPath(new URL(".", import.meta.url));
const sdkEntry = new URL("./node_modules/@modelcontextprotocol/sdk/package.json", import.meta.url);

const [nodeMajor, nodeMinor] = process.versions.node.split(".").map(Number);
if (nodeMajor < 20 || (nodeMajor === 20 && nodeMinor < 19)) {
  console.error("Codex for Microsoft Office requires Node.js 20.19.0 or newer. Ask Codex to install or select a supported Node.js version, then restart Codex.");
  process.exit(1);
}

if (!existsSync(sdkEntry) || !existsSync(new URL("./node_modules/markdown-it/package.json", import.meta.url)) || !existsSync(new URL("./node_modules/lucide/package.json", import.meta.url))) {
  console.error("Installing Codex for Microsoft Office runtime dependencies on first use…");
  const npm = process.platform === "win32" ? "npm.cmd" : "npm";
  const install = spawnSync(npm, ["ci", "--omit=dev", "--no-audit", "--no-fund"], {
    cwd: packageRoot,
    stdio: ["ignore", "inherit", "inherit"],
    shell: process.platform === "win32",
  });
  if (install.error || install.status !== 0) {
    console.error("Could not install Codex for Microsoft Office dependencies. Check that Node.js and npm are installed and internet access is available, then ask Codex to set up Microsoft Office again.");
    process.exit(1);
  }
}

await import("./server.mjs");
