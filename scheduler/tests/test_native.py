"""Public dependency-free CLI and native lifecycle boundaries."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/scheduler.py'


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name) / 'state'
        self.env = {**os.environ, 'SESSION_SCHEDULER_HOME': str(self.home)}

    def cli(self, *arguments, success=True):
        # -S excludes installed dependencies, reproducing a fresh installation.
        result = subprocess.run([sys.executable, '-S', str(SCRIPT), *arguments],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr)
        return json.loads(result.stdout if success else result.stderr)

    def test_desktop_preflight_selects_native_without_runtime_or_hook_receipt(self):
        result = self.cli('preflight', '--engine', 'codex', '--session-id', 'current', '--native-automation')
        self.assertEqual(result['backend'], 'app-native')
        self.assertEqual(result['requirements'], [])
        self.assertFalse(result['catch_up_verified'])
        self.assertFalse((self.home / 'runtime').exists())


    def test_native_path_ignores_an_unusable_optional_private_runtime(self):
        runtime = self.home / 'runtime' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        runtime.parent.mkdir(parents=True)
        runtime.write_text('broken optional runtime', encoding='utf-8')
        runtime.chmod(0o700)
        result = self.cli('preflight', '--engine', 'codex', '--session-id', 'current', '--native-automation')
        self.assertTrue(result['ready'])
        self.assertEqual(self.cli('list'), [])

    def test_unavailable_capabilities_and_claude_runtime_are_reported_before_installing(self):
        unsupported = self.cli('preflight', '--engine', 'codex', '--session-id', 'current')
        self.assertFalse(unsupported['ready'])
        self.assertEqual(unsupported['backend'], 'unsupported')
        claude = self.cli('preflight', '--engine', 'claude', '--session-id', 'current', '--native-clock')
        self.assertEqual(claude['backend'], 'claude-hooks')
        self.assertFalse(claude['ready'])
        self.assertIn('private-runtime', claude['requirements'])
        self.assertFalse((self.home / 'runtime').exists())

    def test_failed_or_stale_native_updates_keep_the_existing_schedule_recoverable(self):
        prompt = Path(self.directory.name) / 'prompt.txt'
        prompt.write_text('Say hello', encoding='utf-8')
        arguments = ['native-record', '--engine', 'codex', '--session-id', 'current',
                     '--cwd', self.directory.name, '--native-id', 'automation-1', '--name', 'Hello',
                     '--rrule', 'FREQ=MINUTELY;INTERVAL=5', '--timezone', 'UTC', '--prompt-file', str(prompt)]
        self.cli(*arguments)
        stale = self.cli(*arguments, success=False)
        self.assertIn('Schedule changed', stale['error'])
        wrong = self.cli('native-forget', '--engine', 'codex', '--session-id', 'current',
                         '--native-id', 'another-automation', success=False)
        self.assertIn('retained', wrong['error'])
        self.assertEqual(self.cli('list')[0]['native_id'], 'automation-1')
        self.cli('cancel', '--engine', 'codex', '--session-id', 'current')
        # A host deletion failure leaves enough information for a later stop request.
        self.assertEqual(self.cli('list')[0]['native_id'], 'automation-1')

    def test_legacy_operations_cannot_overwrite_or_erase_native_tracking(self):
        sys.path.insert(0, str(SCRIPT.parent))
        from scheduler_core import Scheduler
        store = Scheduler(self.home)
        store.record_native('current', self.directory.name, 'Say hello', 'Hello',
                            'FREQ=MINUTELY;INTERVAL=5', 'UTC', 'automation-1')
        operations = [
            lambda: store.save('codex', 'current', self.directory.name, '*/5 * * * *', 'UTC', 'Say hello'),
            lambda: store.bind('codex', 'current', 'another-automation'),
            lambda: store.cancel('codex', 'current'),
        ]
        for operation in operations:
            with self.assertRaises(ValueError):
                operation()
        self.assertEqual(store.list()[0]['native_id'], 'automation-1')
        self.assertIsNone(store.claim('codex', 'current'))

    def test_native_schedule_can_be_listed_edited_and_stopped_from_later_processes(self):
        prompt = Path(self.directory.name) / 'prompt.txt'
        prompt.write_text('Say hello', encoding='utf-8')
        arguments = ['native-record', '--engine', 'codex', '--session-id', 'current',
                     '--cwd', self.directory.name, '--native-id', 'automation-1', '--name', 'Hello',
                     '--rrule', 'FREQ=MINUTELY;INTERVAL=5', '--timezone', 'UTC', '--prompt-file', str(prompt)]
        saved = self.cli(*arguments)['schedule']
        self.assertEqual(saved['backend'], 'app-native')
        self.assertEqual(saved['native_id'], 'automation-1')
        self.assertEqual(self.cli('list')[0]['prompt'], 'Say hello')
        prompt.write_text('Say good morning', encoding='utf-8')
        edited = self.cli(*arguments, '--expected-native-id', 'automation-1')['schedule']
        self.assertEqual(edited['prompt'], 'Say good morning')
        self.assertEqual(len(self.cli('list')), 1)
        tick = subprocess.run([sys.executable, '-S', str(SCRIPT), 'tick'], env=self.env,
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(tick.returncode, 0, tick.stderr)
        self.assertEqual(self.cli('list')[0]['status'], 'active')
        # Local deletion cannot stop a native timer; retain its ID until host deletion succeeds.
        pending = self.cli('cancel', '--engine', 'codex', '--session-id', 'current')
        self.assertEqual(pending['requires_native_delete'], 'automation-1')
        self.assertEqual(len(self.cli('list')), 1)
        self.cli('native-forget', '--engine', 'codex', '--session-id', 'current', '--native-id', 'automation-1')
        self.assertEqual(self.cli('list'), [])
        self.assertFalse((self.home / 'runtime').exists())


if __name__ == '__main__':
    unittest.main()
