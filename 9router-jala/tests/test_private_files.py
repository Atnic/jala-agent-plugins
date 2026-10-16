import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("gateway_private_files", Path(__file__).parents[1] / "scripts" / "gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class PrivateFileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        home = patch.object(gateway.Path, "home", return_value=self.home)
        home.start()
        self.addCleanup(home.stop)

    def writers(self):
        config = self.home / "codex" / "config.toml"
        yield config, lambda: gateway.atomic_private_write(config, "replacement\n")
        credential = gateway.credential_path()
        yield credential, lambda: gateway.save_plaintext_key("test-replacement")

    def test_fallback_sync_failure_preserves_saved_key_and_cleans_temporary_file(self):
        gateway.save_plaintext_key("test-original")
        path = gateway.credential_path()
        with patch.object(gateway.os, "fsync", side_effect=OSError("sync failed")):
            with self.assertRaises(OSError):
                gateway.save_plaintext_key("test-replacement")
        self.assertEqual(gateway.read_plaintext_key(), "test-original")
        self.assertEqual(list(path.parent.iterdir()), [path])

    def test_shared_writer_refuses_symlinked_parent_without_changing_target(self):
        target = self.home / "real-directory"
        target.mkdir()
        saved = target / "config.toml"
        saved.write_text("original\n")
        link = self.home / "linked-directory"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            gateway.atomic_private_write(link / "config.toml", "replacement\n")
        self.assertEqual(saved.read_text(), "original\n")
        self.assertEqual(list(target.iterdir()), [saved])

    @unittest.skipUnless(os.name == "posix", "POSIX permission operation")
    def test_permission_failure_preserves_each_destination_and_cleans_temporary_files(self):
        for path, write in self.writers():
            with self.subTest(path=path.name):
                path.parent.mkdir(parents=True)
                path.write_text("original\n")
                with patch.object(gateway.os, "fchmod", side_effect=PermissionError("permissions refused")):
                    with self.assertRaises(PermissionError):
                        write()
                self.assertEqual(path.read_text(), "original\n")
                self.assertEqual(list(path.parent.iterdir()), [path])

    def test_replace_failure_preserves_each_destination_and_cleans_temporary_files(self):
        for path, write in self.writers():
            with self.subTest(path=path.name):
                path.parent.mkdir(parents=True)
                path.write_text("original\n")
                with patch.object(gateway.os, "replace", side_effect=PermissionError("replacement refused")):
                    with self.assertRaises(PermissionError):
                        write()
                self.assertEqual(path.read_text(), "original\n")
                self.assertEqual(list(path.parent.iterdir()), [path])

    def test_each_writer_refuses_destination_symlinks(self):
        target = self.home / "target"
        target.write_text("original\n")
        for path, write in self.writers():
            with self.subTest(path=path.name):
                path.parent.mkdir(parents=True)
                path.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    write()
                self.assertTrue(path.is_symlink())
                self.assertEqual(target.read_text(), "original\n")
                self.assertEqual(list(path.parent.iterdir()), [path])

    @unittest.skipUnless(os.name == "posix", "POSIX permission policy")
    def test_shared_persistence_preserves_distinct_directory_permission_policies(self):
        for path, write in self.writers():
            with self.subTest(path=path.name):
                path.parent.mkdir(parents=True)
                path.parent.chmod(0o755)
                write()
                expected_directory_mode = 0o700 if path == gateway.credential_path() else 0o755
                self.assertEqual(path.parent.stat().st_mode & 0o777, expected_directory_mode)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(list(path.parent.iterdir()), [path])

    def test_windows_acl_failure_preserves_each_destination_without_writing_contents(self):
        windows_os = types.SimpleNamespace(**{**vars(os), "name": "nt"})
        for path, write in self.writers():
            with self.subTest(path=path.name):
                path.parent.mkdir(parents=True)
                path.write_text("original\n")

                def windows_command(command, **kwargs):
                    if command[0] == "whoami":
                        return subprocess.CompletedProcess(command, 0, stdout=b'"user","S-1-5-21-123"\n')
                    self.assertEqual(Path(command[1]).read_bytes(), b"")
                    raise subprocess.CalledProcessError(5, command, output=b"test-sensitive-output")

                with patch.object(gateway, "os", windows_os), patch.object(gateway.subprocess, "run", side_effect=windows_command):
                    with self.assertRaisesRegex(ValueError, "private Windows file permissions") as caught:
                        write()
                self.assertNotIn("test-sensitive-output", str(caught.exception))
                self.assertEqual(path.read_text(), "original\n")
                self.assertEqual(list(path.parent.iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
