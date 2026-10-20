import { mkdir, readFile, writeFile, rename, unlink, realpath, stat, readdir } from 'node:fs/promises';
import { homedir } from 'node:os';
import { resolve, isAbsolute, basename, dirname } from 'node:path';
import { randomUUID } from 'node:crypto';

// Store folder choices and Office-owned thread IDs, never chat transcripts.
export class OfficeProjects {
  constructor(directory = resolve(homedir(), '.codex', 'office-chats')) {
    this.directory = directory;
    this.file = resolve(directory, 'projects.json');
    this.writes = Promise.resolve();
  }
  async read() {
    try {
      const state = JSON.parse(await readFile(this.file, 'utf8'));
      if (state.version !== 1 || !Array.isArray(state.recent) || !state.threads || typeof state.threads !== 'object' || Array.isArray(state.threads)) throw new Error('Invalid project state.');
      return state;
    } catch (error) {
      if (error.code === 'ENOENT') return { version: 1, recent: [], threads: {}, lastProject: this.directory };
      throw new Error('Could not read Office project preferences. Check ~/.codex/office-chats/projects.json.');
    }
  }
  async folder(path) {
    if (typeof path !== 'string' || !path || path.length > 4096 || /[\x00-\x1f]/.test(path)) throw new Error('Choose a local project folder.');
    if (path === '~') path = homedir();
    else if (/^~[\\/]/.test(path)) path = resolve(homedir(), path.slice(2));
    if (!isAbsolute(path)) throw new Error('Enter the full folder path, or start with ~/.');
    try {
      const canonical = await realpath(path);
      if (!(await stat(canonical)).isDirectory()) throw new Error('Not a directory.');
      return canonical;
    } catch { throw new Error('That folder is unavailable. Choose an existing folder you can access.'); }
  }
  async initial() {
    await mkdir(this.directory, { recursive: true, mode: 0o700 });
    const state = await this.read();
    return this.folder(state.lastProject || this.directory).catch(() => this.folder(this.directory));
  }
  async remember(cwd, threadId) {
    const task = this.writes.then(async () => {
      const state = await this.read();
      state.lastProject = cwd;
      state.recent = [cwd, ...state.recent.filter(path => path !== cwd)].slice(0, 12);
      state.threads[threadId] = cwd;
      await mkdir(this.directory, { recursive: true, mode: 0o700 });
      const temporary = `${this.file}.${randomUUID()}.tmp`;
      try {
        await writeFile(temporary, JSON.stringify(state, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
        await rename(temporary, this.file);
      } finally { await unlink(temporary).catch(() => {}); }
    });
    this.writes = task.catch(() => {});
    return task;
  }
  async owns(thread) {
    const state = await this.read();
    // Older Office chats lived exclusively in the dedicated working folder.
    return Object.hasOwn(state.threads, thread.id) || resolve(thread.cwd) === resolve(this.directory);
  }
  async choices(suggestions = []) {
    const state = await this.read();
    const candidates = [...new Set([state.lastProject, ...state.recent, ...suggestions])].filter(path => typeof path === 'string' && isAbsolute(path));
    const results = await Promise.allSettled(candidates.slice(0, 100).map(path => this.folder(path)));
    return [...new Set(results.filter(r => r.status === 'fulfilled').map(r => r.value))]
      .filter(path => path !== resolve(this.directory)).slice(0, 20).map(path => ({ path, name: basename(path) || path }));
  }
  async browse(path, offset = 0) {
    const cwd = await this.folder(path);
    const entries = await readdir(cwd, { withFileTypes: true });
    const directories = entries.filter(entry => entry.isDirectory());
    // Include directory symlinks; resolving a link happens when navigating into it.
    const links = await Promise.allSettled(entries.filter(entry => entry.isSymbolicLink()).map(async entry => (await stat(resolve(cwd, entry.name))).isDirectory() ? entry : null));
    directories.push(...links.filter(r => r.status === 'fulfilled' && r.value).map(r => r.value));
    directories.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
    offset = Number.isSafeInteger(offset) && offset >= 0 ? offset : 0;
    return { path: cwd, parent: dirname(cwd), folders: directories.slice(offset, offset + 100).map(entry => ({ name: entry.name, path: resolve(cwd, entry.name) })), offset, nextOffset: offset + 100 < directories.length ? offset + 100 : null };
  }
}

export const officeProjects = new OfficeProjects();
