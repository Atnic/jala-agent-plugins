import plistlib
import sys
import tempfile
import subprocess
from unittest.mock import patch
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from platform_timer import plan, configure


class TimerTests(unittest.TestCase):
    def make(self, platform):
        return plan(platform, Path("/Users/Example Person"), Path("/Users/Example Person/Scheduler"),
                    Path("/Users/Example Person/Scheduler/runner/scheduler.py"), "/path with spaces/python", "S-1-5-21-123", "/bin:/custom bin")

    def test_mac_starts_at_login_and_runs_without_a_shell(self):
        p = self.make("darwin")
        data = plistlib.loads(p["files"][0]["content"].encode())
        self.assertTrue(data["RunAtLoad"])
        self.assertEqual(data["StartInterval"], 60)
        self.assertEqual(data["ProgramArguments"][0], "/path with spaces/python")
        self.assertEqual(data["ProgramArguments"][-1], "tick")
        self.assertNotIn("sudo", str(p["commands"]))

    def test_linux_is_a_persistent_user_timer(self):
        p = self.make("linux")
        timer = next(f["content"] for f in p["files"] if f["path"].endswith(".timer"))
        service = next(f["content"] for f in p["files"] if f["path"].endswith(".service"))
        self.assertIn("Persistent=true", timer)
        self.assertIn('ExecStart="/path with spaces/python"', service)
        self.assertTrue(all(command[:2] == ["systemctl", "--user"] for command in p["commands"]))

    def test_install_retries_registration_after_failed_bootstrap_with_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state"
            state.mkdir()
            script = Path(__file__).resolve().parents[1] / "scripts/scheduler.py"
            calls = []
            fail = True
            def run(command, **kwargs):
                nonlocal fail
                calls.append(command)
                if command[:2] == ["launchctl", "bootstrap"] and fail:
                    fail = False
                    raise subprocess.CalledProcessError(1, command)
            with patch("platform_timer.sys.platform", "darwin"), patch("platform_timer.Path.home", return_value=home), patch("platform_timer.subprocess.run", side_effect=run):
                with self.assertRaises(subprocess.CalledProcessError):
                    configure(state, script, True, False)
                configure(state, script, True, False)
            self.assertEqual(sum(c[:2] == ["launchctl", "bootstrap"] for c in calls), 2)
            self.assertTrue((state / "runner/.claude-plugin/plugin.json").is_file())
            self.assertTrue((state / "runner/scripts/scheduler.py").is_file())

    def test_windows_needs_no_password_and_runs_only_when_logged_on(self):
        p = self.make("win32")
        xml = ET.fromstring(p["files"][0]["content"])
        ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
        self.assertEqual(xml.findtext(".//t:LogonType", namespaces=ns), "InteractiveToken")
        self.assertEqual(xml.findtext(".//t:RunLevel", namespaces=ns), "LeastPrivilege")
        self.assertEqual(xml.findtext(".//t:MultipleInstancesPolicy", namespaces=ns), "IgnoreNew")
        self.assertEqual(xml.findtext(".//t:Repetition/t:Interval", namespaces=ns), "PT1M")


if __name__ == "__main__":
    unittest.main()
