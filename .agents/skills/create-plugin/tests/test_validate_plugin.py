import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/validate_plugin.py'
spec = importlib.util.spec_from_file_location('validator', SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.plugin = self.repo / 'sample'
        self.write('README.md', '[Sample](sample/README.md)')
        self.write('sample/README.md', '# Sample')
        self.manifest = {'name': 'sample', 'version': '0.1.0'}
        self.put('sample/plugin.json', self.manifest)
        self.write('sample/skills/sample-task/SKILL.md', '---\nname: sample-task\ndescription: Sample task\n---\n')

    def write(self, path, content):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def put(self, path, obj):
        self.write(path, json.dumps(obj))

    def errors(self):
        return validator.validate(self.plugin, self.repo)

    def host(self):
        self.put('sample/.codex-plugin/plugin.json', {**self.manifest, 'skills': './skills/'})
        self.put('.agents/plugins/marketplace.json', {'plugins': [{'name': 'sample', 'source': {'source': 'local', 'path': './sample'}}]})

    def test_skills_without_branding_or_hosts(self):
        self.assertEqual(self.errors(), [])

    def test_mcp_only_and_combined(self):
        self.put('sample/.mcp.json', {'mcpServers': {'remote': {'url': 'https://example.com/mcp'}}})
        self.assertEqual(self.errors(), [])
        (self.plugin / 'skills/sample-task/SKILL.md').unlink()
        (self.plugin / 'skills/sample-task').rmdir()
        self.assertEqual(self.errors(), [])

    def test_empty_and_missing_entrypoint(self):
        (self.plugin / 'skills/sample-task/SKILL.md').unlink()
        self.assertTrue(self.errors())
        (self.plugin / 'skills/sample-task').rmdir()
        self.assertTrue(self.errors())

    def test_malformed_json(self):
        self.write('sample/plugin.json', '{')
        self.assertTrue(self.errors())

    def test_identity_and_version(self):
        self.host()
        for key, value in [('name', 'other'), ('version', '0.2.0')]:
            with self.subTest(key=key):
                self.put('sample/.codex-plugin/plugin.json', {**self.manifest, key: value, 'skills': './skills/'})
                self.assertTrue(self.errors())

    def test_legacy_claude_manifest_may_omit_version(self):
        self.put('sample/.claude-plugin/plugin.json', {'name': 'sample'})
        self.put('.claude-plugin/marketplace.json', {'plugins': [{'name': 'sample', 'source': './sample'}]})
        self.assertEqual(self.errors(), [])

    def test_declared_claude_version_must_match(self):
        self.put('.claude-plugin/marketplace.json', {'plugins': [{'name': 'sample', 'source': './sample'}]})
        self.put('sample/.claude-plugin/plugin.json', self.manifest)
        self.assertEqual(self.errors(), [])
        for version in ('0.0.9', None, '', 1):
            with self.subTest(version=version):
                self.put('sample/.claude-plugin/plugin.json', {**self.manifest, 'version': version})
                self.assertTrue(any('version must match portable manifest' in error for error in self.errors()))

    def test_legacy_claude_manifest_still_requires_matching_name(self):
        self.put('.claude-plugin/marketplace.json', {'plugins': [{'name': 'sample', 'source': './sample'}]})
        for name in ('other', None):
            with self.subTest(name=name):
                manifest = {} if name is None else {'name': name}
                self.put('sample/.claude-plugin/plugin.json', manifest)
                self.assertTrue(any('name must match portable manifest' in error for error in self.errors()))

    def test_codex_manifest_requires_matching_version(self):
        self.host()
        self.put('sample/.codex-plugin/plugin.json', {'name': 'sample', 'skills': './skills/'})
        self.assertTrue(any('version must match portable manifest' in error for error in self.errors()))

    def test_catalog_errors(self):
        self.host()
        self.assertEqual(self.errors(), [])
        for entries in [[], [{'name': 'sample', 'source': './sample'}] * 2,
                        [{'name': 'sample', 'source': './other'}]]:
            self.put('.agents/plugins/marketplace.json', {'plugins': entries})
            self.assertTrue(self.errors())

    def test_missing_paths(self):
        for field, value in [('skills', './missing'), ('mcpServers', './missing.json')]:
            self.put('sample/plugin.json', {**self.manifest, field: value})
            self.assertTrue(self.errors())
        self.put('sample/plugin.json', {**self.manifest, 'extensions': {'com.openai': {'interface': {'logo': './missing.svg'}}}})
        self.assertTrue(self.errors())

    def test_escaping_paths_and_symlinks(self):
        for field in ['skills', 'mcpServers']:
            self.put('sample/plugin.json', {**self.manifest, field: '../README.md'})
            self.assertTrue(self.errors())
        self.put('sample/plugin.json', self.manifest)
        (self.plugin / 'skills/sample-task/SKILL.md').unlink()
        (self.plugin / 'skills/sample-task/SKILL.md').symlink_to(self.repo / 'README.md')
        self.assertTrue(self.errors())
        self.assertTrue(validator.validate(self.repo.parent, self.repo))

    def test_read_only(self):
        self.host()
        before = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.assertEqual(self.errors(), [])
        after = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_utf8_files_do_not_depend_on_the_platform_default_encoding(self):
        (self.repo / 'README.md').write_text('文書 — [Sample](sample/README.md)', encoding='utf-8')
        (self.plugin / 'plugin.json').write_text(json.dumps({**self.manifest, 'description': '文書'}, ensure_ascii=False), encoding='utf-8')
        result = subprocess.run([sys.executable, '-X', 'warn_default_encoding', '-W', 'error::EncodingWarning',
                                 str(SCRIPT), str(self.plugin), '--repo-root', str(self.repo)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))

    def test_invalid_utf8_readme_is_a_validation_error(self):
        (self.repo / 'README.md').write_bytes(b'\xff')
        self.assertTrue(any('README.md' in error for error in self.errors()))

    def test_cli_exit_codes(self):
        def run(*args):
            return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True)
        self.assertEqual(run(self.plugin, '--repo-root', self.repo).returncode, 0)
        self.assertEqual(run(self.repo / 'missing', '--repo-root', self.repo).returncode, 1)
        self.assertEqual(run(self.plugin, '--repo-root', self.repo / 'missing').returncode, 2)


if __name__ == '__main__':
    unittest.main()
