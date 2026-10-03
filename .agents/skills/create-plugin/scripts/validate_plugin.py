#!/usr/bin/env python3
"""Read-only local plugin consistency checks; not a host schema validator."""
import argparse
import json
from pathlib import Path
import re
import sys

NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
VERSION = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z")


def validate(plugin, repo):
    errors = []

    def fail(path, message):
        errors.append(f"{path}: {message}")

    def read(path):
        try:
            obj = json.loads(path.read_text())
            if not isinstance(obj, dict):
                raise ValueError('expected a JSON object')
            return obj
        except (OSError, ValueError) as exc:
            fail(path, str(exc))
            return {}

    def local(base, value, kind):
        if not isinstance(value, str) or not value:
            fail(base, f'{kind} must be a nonempty local path')
            return None
        target = (base / value).resolve()
        if not target.is_relative_to(base.resolve()):
            fail(base, f'{kind} escapes permitted root: {value}')
            return None
        if not target.exists():
            fail(base, f'missing {kind}: {value}')
            return None
        return target

    plugin, repo = Path(plugin).resolve(), Path(repo).resolve()
    if not plugin.is_relative_to(repo) or plugin == repo:
        return ['plugin directory must be inside the repository']
    portable = read(plugin / 'plugin.json')
    name, version = portable.get('name'), portable.get('version')
    if not isinstance(name, str) or not NAME.fullmatch(name):
        fail(plugin / 'plugin.json', 'invalid plugin name')
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        fail(plugin / 'plugin.json', 'invalid semantic version')
    manifests = [('portable', portable)]
    hosts = [('codex', '.codex-plugin/plugin.json', '.agents/plugins/marketplace.json'),
             ('claude', '.claude-plugin/plugin.json', '.claude-plugin/marketplace.json')]
    for host, manifest, catalog in hosts:
        path = plugin / manifest
        if not path.exists():
            continue
        obj = read(path)
        manifests.append((host, obj))
        if obj.get('name') != name or obj.get('version') != version:
            fail(path, 'name/version must match portable manifest')
        data = read(repo / catalog)
        entries = data.get('plugins', [])
        if not isinstance(entries, list):
            fail(repo / catalog, 'plugins must be an array')
            entries = []
        matches = [e for e in entries if isinstance(e, dict) and e.get('name') == name]
        if len(matches) != 1:
            fail(repo / catalog, 'expected exactly one matching plugin entry')
        else:
            source = matches[0].get('source')
            if isinstance(source, dict):
                source = source.get('path') if source.get('source') == 'local' else None
            target = local(repo, source, 'catalog source')
            if target is not None and target != plugin:
                fail(repo / catalog, 'catalog source resolves to a different package')

    skill_roots = set()
    if (plugin / 'skills').exists():
        target = local(plugin, 'skills', 'skills directory')
        if target:
            skill_roots.add(target)
    for host, obj in manifests:
        if 'skills' in obj:
            target = local(plugin, obj['skills'], 'skills directory')
            if target:
                skill_roots.add(target)
        if host == 'codex' and (plugin / 'skills').is_dir() and 'skills' not in obj:
            fail(plugin / '.codex-plugin/plugin.json', 'declare the skills directory')
        interface = obj.get('interface', {}) if host == 'codex' else obj.get('extensions', {}).get('com.openai', {}).get('interface', {})
        if not isinstance(interface, dict):
            fail(plugin, 'interface must be an object')
            continue
        for key in ('composerIcon', 'logo', 'logoDark'):
            if key in interface:
                target = local(plugin, interface[key], key)
                if target and not target.is_file():
                    fail(target, 'asset must be a file')

    skill_count = 0
    for folder in skill_roots:
        if not folder.is_dir():
            fail(folder, 'skills path must be a directory')
            continue
        for child in folder.iterdir():
            if not child.is_dir():
                continue
            if not child.resolve().is_relative_to(plugin):
                fail(child, 'skill directory escapes package')
            if not NAME.fullmatch(child.name) or len(child.name) > 64:
                fail(child, 'invalid skill directory name')
            if not (child / 'SKILL.md').is_file():
                fail(child, 'missing SKILL.md')
            elif not (child / 'SKILL.md').resolve().is_relative_to(plugin):
                fail(child, 'SKILL.md escapes package')
            else:
                skill_count += 1

    mcp_count = 0

    def mcp(obj, path):
        nonlocal mcp_count
        servers = obj.get('mcpServers')
        if not isinstance(servers, dict) or not servers:
            fail(path, 'mcpServers must be a nonempty object')
        elif any(not isinstance(s, dict) or not s for s in servers.values()):
            fail(path, 'each MCP server must be a nonempty object')
        else:
            mcp_count += len(servers)

    if (plugin / '.mcp.json').exists():
        target = local(plugin, '.mcp.json', 'MCP configuration')
        if target:
            mcp(read(target), target)
    for _, obj in manifests:
        if 'mcpServers' not in obj:
            continue
        value = obj['mcpServers']
        if isinstance(value, str):
            target = local(plugin, value, 'MCP configuration')
            if target:
                mcp(read(target), target)
        elif isinstance(value, dict):
            mcp({'mcpServers': value}, plugin)
        else:
            fail(plugin, 'mcpServers must be a path or server map')
    if not skill_count and not mcp_count:
        fail(plugin, 'package must contain skills or declared MCP configuration')
    if not (plugin / 'README.md').is_file():
        fail(plugin, 'missing plugin README.md')
    try:
        if f'{plugin.relative_to(repo).as_posix()}/README.md' not in (repo / 'README.md').read_text():
            fail(repo / 'README.md', 'missing plugin README reference')
    except OSError as exc:
        fail(repo / 'README.md', str(exc))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plugin_directory', type=Path)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    if not args.repo_root.is_dir() or not (args.repo_root / 'README.md').is_file():
        parser.error('repository root must be a directory with README.md')
    try:
        errors = validate(args.plugin_directory, args.repo_root)
    except (OSError, TypeError, AttributeError) as exc:
        errors = [f'cannot inspect package: {exc}']
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Structural validation passed. Host compatibility and runtime behavior were not tested.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
