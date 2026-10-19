import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const packageRoot = fileURLToPath(new URL(".", import.meta.url));
const sdkEntry = new URL("./node_modules/@modelcontextprotocol/sdk/package.json", import.meta.url);

if (Number(process.versions.node.split(".")[0]) < 20) {
  console.error("Microsoft Office for Codex requires Node.js 20 or newer. Ask Codex to install or select a supported Node.js version, then restart Codex.");
  process.exit(1);
}

if (!existsSync(sdkEntry)) {
  console.error("Installing Microsoft Office for Codex runtime dependencies on first use…");
  const npm = process.platform === "win32" ? "npm.cmd" : "npm";
  const install = spawnSync(npm, ["ci", "--omit=dev", "--no-audit", "--no-fund"], {
    cwd: packageRoot,
    stdio: ["ignore", "inherit", "inherit"],
    shell: process.platform === "win32",
  });
  if (install.error || install.status !== 0) {
    console.error("Could not install Microsoft Office for Codex dependencies. Check that Node.js and npm are installed and internet access is available, then ask Codex to set up Microsoft Office again.");
    process.exit(1);
  }
}

await import("./server.mjs");
