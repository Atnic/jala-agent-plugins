import { mkdir, writeFile, rename } from 'node:fs/promises';
import { homedir } from 'node:os';
import { resolve, isAbsolute } from 'node:path';
import { randomUUID } from 'node:crypto';

// Read the structured list_projects result from stdin; never inspect desktop storage.
let input = '';
for await (const chunk of process.stdin) {
  input += chunk;
  if (input.length > 2_000_000) throw new Error('Project catalog too large.');
}
const data = JSON.parse(input);
const records = Array.isArray(data) ? data : data.projects;
if (!Array.isArray(records)) throw new Error('Expected the projects array from Codex list_projects.');
const projects = records.filter(p => p.projectKind === 'local' && p.hostId === 'local' && typeof p.path === 'string' && isAbsolute(p.path) && typeof p.projectId === 'string' && typeof p.label === 'string')
  .map(({ projectId, label, path }) => ({ projectId, label, path }));
const directory = resolve(homedir(), '.codex', 'office-chats');
await mkdir(directory, { recursive: true, mode: 0o700 });
const temporary = resolve(directory, `codex-projects.${randomUUID()}.tmp`);
await writeFile(temporary, JSON.stringify({ version: 1, refreshedAt: new Date().toISOString(), projects }, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
await rename(temporary, resolve(directory, 'codex-projects.json'));
console.log(`Synced ${projects.length} existing local Codex projects.`);
