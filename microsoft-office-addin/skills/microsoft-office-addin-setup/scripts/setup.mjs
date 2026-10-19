import { copyFile, mkdir, rm } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const action = process.argv[2] ?? "install";
if (!new Set(["install", "remove"]).has(action)) {
  console.error("Usage: node setup.mjs [install|remove]");
  process.exit(2);
}
const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const manifest = join(packageRoot, "manifest.xml");
const filename = "microsoft-office-addin.xml";
const macApps = ["com.microsoft.Word", "com.microsoft.Excel", "com.microsoft.Powerpoint"];
const officeApps = ["word", "excel", "powerpoint"];

if (process.platform === "win32" || process.platform === "linux") {
  const officePlatform = process.platform === "win32" ? "desktop" : "web";
  if (action === "install") {
    for (const app of officeApps) {
      runNpx([
        "--yes", "office-addin-debugging", "start", "manifest.xml", officePlatform,
        "--app", app, "--debug-method", "direct", "--no-debug", "--no-live-reload",
        "--dev-server-port", "3000",
      ]);
      console.log(`Sideloaded ${app}.`);
    }
  } else {
    runNpx(["--yes", "office-addin-debugging", "stop", "manifest.xml", officePlatform]);
  }
  const completion = process.platform === "win32"
    ? "The Office apps may have opened; keep them open and use the Microsoft Office for Codex task pane."
    : "Office on the web may have opened in your browser; sign in to your Microsoft 365 account if prompted, then use the Microsoft Office for Codex task pane."
  console.log(action === "install"
    ? `Manifest installed for Word, Excel, and PowerPoint. ${completion}`
    : "Manifest sideload removed from Word, Excel, and PowerPoint.");
  process.exit(0);
}

if (process.platform !== "darwin") {
  console.error("Office add-in setup is supported on macOS, Windows, and Linux.");
  process.exit(2);
}

for (const appId of macApps) {
  const folder = join(homedir(), "Library/Containers", appId, "Data/Documents/wef");
  const target = join(folder, filename);
  if (action === "install") {
    await mkdir(folder, { recursive: true });
    await copyFile(manifest, target);
    console.log(`Sideloaded for ${appId}: ${target}`);
  } else {
    await rm(target, { force: true });
    console.log(`Removed sideload for ${appId}: ${target}`);
  }
}

console.log(action === "install"
  ? "Manifest installed. Open or restart Word, Excel, or PowerPoint to load the add-in."
  : "Manifest removed from the Word, Excel, and PowerPoint sideload folders.");

function runNpx(args) {
  const executable = process.platform === "win32" ? "npx.cmd" : "npx";
  const result = spawnSync(executable, args, {
    cwd: packageRoot,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
