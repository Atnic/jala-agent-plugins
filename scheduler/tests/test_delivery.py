"""Exercise runner acknowledgement failures through a real subprocess boundary."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from scheduler import claude_delivery
from scheduler_core import Scheduler


@unittest.skipIf(os.name == 'nt', 'POSIX fake executable fixture')
class DeliveryTests(unittest.TestCase):
    def test_successful_cli_response_without_correlated_hooks_is_failure_and_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cli = base / 'fake-claude'
            cli.write_text('#!' + sys.executable + '\nimport sys,json\n'
                           'if sys.argv[1] == "agents": print("[]")\n'
                           'else: print(json.dumps({"session_id":"target", "num_turns":1, '
                           '"result":"Scheduler hooks need activation", "is_error":False}))\n')
            cli.chmod(0o700)
            transcript = base / 'transcript.jsonl'
            transcript.touch()
            now = time.time() - 7200
            store = Scheduler(base / 'state', clock=lambda: now)
            store.join('claude', 'target', (99999999, 0), metadata={'transcript_path': str(transcript)})
            store.save('claude', 'target', directory, '0 * * * *', 'UTC', 'Run the task', str(cli))
            store.bind('claude', 'target', 'native')
            now += 7200
            store.run_pending(lambda job, dispatch, lease: claude_delivery(store, job, dispatch, lease))
            outcome = store.list()[0]
            self.assertEqual(outcome['status'], 'failed')
            self.assertIn('not acknowledged', outcome['last_error'])
            store.run_pending(lambda *args: self.fail('Failed occurrence retried'))
            self.assertEqual(store.list()[0]['handled_at'], outcome['handled_at'])


if __name__ == '__main__':
    unittest.main()
