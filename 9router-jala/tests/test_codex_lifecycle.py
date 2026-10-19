import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request


spec = importlib.util.spec_from_file_location("gateway_lifecycle", Path(__file__).parents[1] / "scripts" / "gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class CodexLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.root = self.home / "codex"
        self.root.mkdir()
        self.config = self.root / "config.toml"
        self.catalog = self.root / "models_9router_jala.json"
        self.values = {}
        store = Mock()
        store.get_password.side_effect = lambda *args: self.values.get("key")
        store.set_password.side_effect = lambda *args: self.values.update(key=args[-1])
        store.delete_password.side_effect = lambda *args: self.values.pop("key", None)
        self.store = store
        for context in (
            patch.object(gateway.Path, "home", return_value=self.home),
            patch.dict(os.environ, {"CODEX_HOME": str(self.root)}, clear=True),
            patch.object(gateway, "credential_store", return_value=store),
            patch.object(gateway, "send", return_value=(b'{"data":[]}', "application/json")),
            patch.object(gateway.sys, "platform", "freebsd"),
        ):
            context.start()
            self.addCleanup(context.stop)

    def command(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["gateway.py", *args]), patch.object(sys, "stdout", output), patch.object(sys, "stderr", error):
            result = gateway.main()
        return result, output.getvalue(), error.getvalue()

    def test_setup_then_revert_preserves_unrelated_configuration_and_saved_key(self):
        self.config.write_text('approval_policy = "on-request" # keep this note\n\n[model_providers.other]\nbase_url = "https://example.test/v1"\n')
        self.values["key"] = "test-lifecycle-secret"
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        result, output, error = self.command("revert-codex")
        self.assertEqual((result, error), (0, ""))
        document = gateway.tomllib.loads(self.config.read_text())
        self.assertEqual(document, {"forced_login_method": "chatgpt", "approval_policy": "on-request", "model_providers": {"other": {"base_url": "https://example.test/v1"}}})
        self.assertIn("# keep this note", self.config.read_text())
        self.assertEqual(self.values["key"], "test-lifecycle-secret")
        self.assertTrue(self.catalog.exists())
        self.assertIn("restart Codex", output)
        self.assertNotIn("test-lifecycle-secret", output + error)

    def test_repeated_revert_is_a_noop_without_accessing_credentials(self):
        self.values["key"] = "test-repeat-secret"
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        self.assertEqual(self.command("revert-codex")[0], 0)
        before = self.config.read_bytes()
        self.store.get_password.side_effect = RuntimeError("store locked")
        result, output, error = self.command("revert-codex")
        self.assertEqual((result, error), (0, ""))
        self.assertIn("already reverted", output)
        self.assertEqual(self.config.read_bytes(), before)
        self.config.unlink()
        self.assertEqual(self.command("revert-codex")[0], 0)
        self.assertFalse(self.config.exists())

    def test_setup_migrates_legacy_auth_value_and_repeated_setup_stays_clean(self):
        self.values["key"] = "test-upgrade-secret"
        self.config.write_text(
            'model = "9router-jala"\n'
            'model_provider = "9router-jala"\n'
            'preferred_auth_method = "apikey" # legacy setup value\n'
            'forced_login_method = "api"\n'
            'approval_policy = "on-request"\n'
            '\n[model_providers.9router-jala]\n'
            'wire_api = "responses"\n'
            'experimental_bearer_token = "test-upgrade-secret"\n'
            '\n[model_providers.other]\n'
            'base_url = "https://example.test/v1"\n'
        )

        for _ in range(2):
            result, output, error = self.command("setup-codex", "--reuse-saved-key")
            self.assertEqual((result, error), (0, ""))
            document = gateway.tomllib.loads(self.config.read_text())
            self.assertNotIn("preferred_auth_method", document)
            self.assertEqual(document["forced_login_method"], "chatgpt")
            self.assertEqual(document["approval_policy"], "on-request")
            self.assertEqual(document["model_providers"]["other"]["base_url"], "https://example.test/v1")
            self.assertEqual(document["model_providers"]["9router-jala"]["wire_api"], "responses")
            self.assertNotIn("test-upgrade-secret", output + error)
        self.assertEqual(self.values["key"], "test-upgrade-secret")

    def test_setup_removes_deprecated_guardian_context_only_from_config_scopes(self):
        self.values["key"] = "test-guardian-secret"
        self.config.write_text(
            'forced_login_method = "chatgpt"\n'
            'prompt = "[features.guardianv2] thread_context = true"\n'
            '\n[features.guardianv2]\n'
            'thread_context = true\n'
            'enabled = true # keep Guardian enabled\n'
            '\n[profiles.research]\n'
            'model_provider = "other"\n'
            'features = { guardianv2 = { thread_context = false, enabled = false }, other = true }\n'
            '\n[profiles.work.features.guardianv2]\n'
            'thread_context = true\n'
            '\n[other.features.guardianv2]\n'
            'thread_context = true # unrelated namespace\n'
        )

        previous = None
        for _ in range(2):
            result, output, error = self.command("setup-codex", "--reuse-saved-key")
            self.assertEqual((result, error), (0, ""))
            text = self.config.read_text()
            document = gateway.tomllib.loads(text)
            self.assertEqual(document["features"]["guardianv2"], {"enabled": True})
            self.assertEqual(document["profiles"]["research"], {
                "model_provider": "other",
                "features": {"guardianv2": {"enabled": False}, "other": True},
            })
            self.assertEqual(document["profiles"]["work"]["features"]["guardianv2"], {})
            self.assertTrue(document["other"]["features"]["guardianv2"]["thread_context"])
            self.assertEqual(document["prompt"], "[features.guardianv2] thread_context = true")
            self.assertEqual(document["forced_login_method"], "chatgpt")
            self.assertTrue(document["model_providers"]["9router-jala"]["requires_openai_auth"])
            self.assertIn("# keep Guardian enabled", text)
            self.assertIn("# unrelated namespace", text)
            self.assertNotIn("test-guardian-secret", output + error)
            if previous is not None:
                self.assertEqual(text, previous)
            previous = text

    def test_setup_cleans_guardian_in_interleaved_tables(self):
        fixtures = (
            (
                "features proxy",
                '[features.guardianv2]\nthread_context = false\nenabled = true\n'
                '[other]\nkeep = true # keep note\n[features]\nother = true\n',
                {"features": {"guardianv2": {"enabled": True}, "other": True}, "other": {"keep": True}},
            ),
            (
                "guardian proxy",
                '[features.guardianv2.extra]\nkeep = true # keep note\n'
                '[other]\nkeep = true\n[features.guardianv2]\nthread_context = true\n',
                {"features": {"guardianv2": {"extra": {"keep": True}}}, "other": {"keep": True}},
            ),
            (
                "profile proxy",
                '[profiles.research.features.guardianv2]\nthread_context = true\nenabled = false\n'
                '[profiles.work]\nmodel = "other" # keep note\n'
                '[profiles.research]\nmodel = "custom"\n',
                {"profiles": {
                    "research": {"features": {"guardianv2": {"enabled": False}}, "model": "custom"},
                    "work": {"model": "other"},
                }},
            ),
            (
                "profiles proxy",
                '[profiles.research.features.guardianv2]\nthread_context = false\n'
                '[other]\nkeep = true # keep note\n[profiles]\n',
                {"profiles": {"research": {"features": {"guardianv2": {}}}}, "other": {"keep": True}},
            ),
        )
        self.values["key"] = "test-interleaved-secret"
        for name, fixture, expected in fixtures:
            with self.subTest(layout=name):
                self.config.write_text('forced_login_method = "chatgpt"\n' + fixture)
                previous = None
                for _ in range(2):
                    result, output, error = self.command("setup-codex", "--reuse-saved-key")
                    self.assertEqual((result, error), (0, ""))
                    text = self.config.read_text()
                    document = gateway.tomllib.loads(text)
                    for section, value in expected.items():
                        self.assertEqual(document[section], value)
                    self.assertEqual(document["forced_login_method"], "chatgpt")
                    self.assertIn("# keep note", text)
                    self.assertNotIn("test-interleaved-secret", output + error)
                    if previous is not None:
                        self.assertEqual(text, previous)
                    previous = text

    def test_repeated_setup_preserves_chatgpt_identity_and_gateway_inference_settings(self):
        self.values["key"] = "test-desktop-secret"
        auth_file = self.root / "auth.json"
        auth_file.write_text('{"test_identity": "unchanged"}')
        self.config.write_text(
            'forced_login_method = "chatgpt" # keep sign-in choice\n'
            'forced_chatgpt_workspace_id = "test-workspace"\n'
            'preferred_auth_method = "apikey"\n'
            '\n[model_providers.9router-jala]\n'
            'requires_openai_auth = true\n'
            'experimental_bearer_token = "test-desktop-secret"\n'
            '\n[profiles.other]\n'
            'model_provider = "other"\n'
        )
        for _ in range(2):
            result, output, error = self.command("setup-codex", "--reuse-saved-key")
            self.assertEqual((result, error), (0, ""))
            document = gateway.tomllib.loads(self.config.read_text())
            provider = document["model_providers"]["9router-jala"]
            self.assertEqual(document["forced_login_method"], "chatgpt")
            self.assertTrue(provider["requires_openai_auth"])
            self.assertEqual(provider["experimental_bearer_token"], "test-desktop-secret")
            self.assertEqual(provider["base_url"], "https://9router.jala.tech/v1")
            self.assertEqual(provider["wire_api"], "responses")
            self.assertEqual(document["model_provider"], "9router-jala")
            self.assertEqual(document["forced_chatgpt_workspace_id"], "test-workspace")
            self.assertEqual(document["profiles"]["other"]["model_provider"], "other")
            self.assertIn("# keep sign-in choice", self.config.read_text())
            self.assertNotIn("preferred_auth_method", document)
            self.assertNotIn("test-desktop-secret", output + error)
            self.assertEqual(auth_file.read_text(), '{"test_identity": "unchanged"}')
        self.assertEqual(self.values["key"], "test-desktop-secret")

    def test_default_setup_selects_chatgpt_for_fresh_and_existing_configurations(self):
        self.values["key"] = "test-default-mode-secret"
        for existing in ("", 'forced_login_method = "api"\n',
                         '[model_providers.9router-jala]\nrequires_openai_auth = false\n',
                         'forced_login_method = "custom"\n'):
            with self.subTest(existing=existing):
                self.config.write_text(existing)
                result, output, error = self.command("setup-codex", "--reuse-saved-key")
                self.assertEqual((result, error), (0, ""))
                document = gateway.tomllib.loads(self.config.read_text())
                provider = document["model_providers"]["9router-jala"]
                self.assertEqual(document["forced_login_method"], "chatgpt")
                self.assertTrue(provider["requires_openai_auth"])
                self.assertEqual(provider["experimental_bearer_token"], "test-default-mode-secret")
                self.assertNotIn("test-default-mode-secret", output + error)

    def test_explicit_auth_modes_switch_without_changing_gateway_credentials(self):
        self.values["key"] = "test-auth-choice-secret"
        self.config.write_text('approval_policy = "on-request"\n')
        for mode in ("chatgpt", "api", "chatgpt"):
            with self.subTest(mode=mode):
                result, output, error = self.command("setup-codex", "--reuse-saved-key", "--auth-mode", mode)
                self.assertEqual((result, error), (0, ""))
                document = gateway.tomllib.loads(self.config.read_text())
                provider = document["model_providers"]["9router-jala"]
                self.assertEqual(document["forced_login_method"], mode)
                self.assertEqual(provider["requires_openai_auth"], mode == "chatgpt")
                self.assertEqual(provider["experimental_bearer_token"], "test-auth-choice-secret")
                self.assertEqual(provider["base_url"], "https://9router.jala.tech/v1")
                self.assertEqual(provider["wire_api"], "responses")
                self.assertEqual(document["approval_policy"], "on-request")
                self.assertEqual(self.values["key"], "test-auth-choice-secret")
                self.assertNotIn("test-auth-choice-secret", output + error)

    def test_revert_keeps_chatgpt_sign_in_choice_and_reports_it_on_repeated_runs(self):
        self.values["key"] = "test-chatgpt-revert-secret"
        self.config.write_text(
            'forced_login_method = "chatgpt" # account preference\n'
            'forced_chatgpt_workspace_id = "test-workspace"\n'
        )
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        for _ in range(2):
            result, output, error = self.command("revert-codex")
            self.assertEqual((result, error), (0, ""))
            document = gateway.tomllib.loads(self.config.read_text())
            self.assertEqual(document["forced_login_method"], "chatgpt")
            self.assertEqual(document["forced_chatgpt_workspace_id"], "test-workspace")
            self.assertIn("# account preference", self.config.read_text())
            self.assertNotIn("9router-jala", document.get("model_providers", {}))
            self.assertIn("forced_login_method", output)
            self.assertNotIn("test-chatgpt-revert-secret", output + error)
        self.assertEqual(self.values["key"], "test-chatgpt-revert-secret")

    def test_setup_preserves_customized_legacy_auth_value(self):
        self.values["key"] = "test-custom-auth-secret"
        self.config.write_text('preferred_auth_method = "custom-auth"\napproval_policy = "on-request"\n')

        result, output, error = self.command("setup-codex", "--reuse-saved-key")

        self.assertEqual((result, error), (0, ""))
        document = gateway.tomllib.loads(self.config.read_text())
        self.assertEqual(document["preferred_auth_method"], "custom-auth")
        self.assertEqual(document["forced_login_method"], "chatgpt")
        self.assertEqual(document["approval_policy"], "on-request")
        self.assertNotIn("test-custom-auth-secret", output + error)
        self.assertIn("Unsupported preferred_auth_method was retained", output)

    def test_legacy_setup_value_is_removed_on_revert_and_repeated_revert_is_a_noop(self):
        self.config.write_text(
            'model = "9router-jala"\n'
            'model_provider = "9router-jala"\n'
            'preferred_auth_method = "apikey"\n'
            'forced_login_method = "api"\n'
            'model_reasoning_effort = "high"\n'
            f'model_catalog_json = {json.dumps(str(self.catalog))}\n'
            '\n[model_providers.9router-jala]\n'
            'wire_api = "responses"\n'
            'experimental_bearer_token = "test-legacy-revert-secret"\n'
        )

        result, output, error = self.command("revert-codex")

        self.assertEqual((result, error), (0, ""))
        document = gateway.tomllib.loads(self.config.read_text())
        self.assertNotIn("preferred_auth_method", document)
        self.assertNotIn("model", document)
        self.assertNotIn("model_provider", document)
        self.assertNotIn("forced_login_method", document)
        self.assertNotIn("9router-jala", document.get("model_providers", {}))
        self.assertEqual(self.values["key"], "test-legacy-revert-secret")
        self.assertNotIn("test-legacy-revert-secret", output + error)

        before = self.config.read_bytes()
        self.store.get_password.side_effect = RuntimeError("store locked")
        result, output, error = self.command("revert-codex")
        self.assertEqual((result, error), (0, ""))
        self.assertIn("already reverted", output)
        self.assertEqual(self.config.read_bytes(), before)

    def test_revert_refuses_conflicting_saved_credentials(self):
        for location in ("native", "fallback"):
            with self.subTest(location=location):
                self.values["key"] = "test-config-secret"
                self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
                if location == "native":
                    self.values["key"] = "test-different-secret"
                else:
                    gateway.save_plaintext_key("test-different-secret")
                before = self.config.read_bytes()
                result, output, error = self.command("revert-codex")
                self.assertEqual(result, 1)
                self.assertIn("different", error)
                self.assertEqual(self.config.read_bytes(), before)
                self.assertNotIn("test-config-secret", output + error)
                self.assertNotIn("test-different-secret", output + error)
                gateway.credential_path().unlink(missing_ok=True)

    def test_revert_preserves_custom_values_and_reports_profiles_on_every_run(self):
        self.values["key"] = "test-profile-secret"
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        document = gateway.tomlkit.parse(self.config.read_text())
        document["model"] = "custom-model"
        document["model_reasoning_effort"] = "low"
        document["preferred_auth_method"] = "custom-auth"
        document["model_catalog_json"] = str(self.root / "custom-models.json")
        document["profiles"] = {"research": {"model_provider": "9router-jala", "model_catalog_json": str(self.catalog)}}
        self.config.write_text(gateway.tomlkit.dumps(document))
        for _ in range(2):
            result, output, error = self.command("revert-codex")
            self.assertEqual((result, error), (0, ""))
            parsed = gateway.tomllib.loads(self.config.read_text())
            self.assertEqual(parsed["model"], "custom-model")
            self.assertEqual(parsed["model_reasoning_effort"], "low")
            self.assertEqual(parsed["preferred_auth_method"], "custom-auth")
            self.assertEqual(parsed["model_catalog_json"], str(self.root / "custom-models.json"))
            self.assertEqual(parsed["profiles"]["research"]["model_provider"], "9router-jala")
            self.assertIn("profiles.research.model_provider", output)
            self.assertIn("profiles.research.model_catalog_json", output)
            self.assertIn("preferred_auth_method", output)
            self.assertNotIn("test-profile-secret", output + error)

    def test_revert_rejects_malformed_configuration_without_touching_credentials(self):
        for text in ('test-malformed-secret = [\n', 'model_providers = "test-malformed-secret"\n', '[model_providers]\n9router-jala = "test-malformed-secret"\n'):
            with self.subTest(text=text):
                self.config.write_text(text)
                self.store.get_password.side_effect = RuntimeError("test-locked-secret")
                result, output, error = self.command("revert-codex")
                self.assertEqual(result, 1)
                self.assertIn("left unchanged", error)
                self.assertEqual(self.config.read_text(), text)
                self.assertEqual(self.values, {})
                self.assertNotIn("test-malformed-secret", output + error)
                self.assertNotIn("test-locked-secret", output + error)

    def test_saved_key_setup_preflights_configuration_before_replacing_credentials(self):
        self.config.write_text('model = [\n')
        self.values["key"] = "test-original-secret"
        with patch.dict(os.environ, {"NINEROUTER_KEY": "test-new-secret"}):
            result, output, error = self.command("setup-codex", "--reuse-saved-key")
        self.assertEqual(result, 1)
        self.assertIn("valid TOML", error)
        self.assertEqual(self.values["key"], "test-original-secret")
        self.assertEqual(self.config.read_text(), 'model = [\n')
        self.assertFalse(self.catalog.exists())
        self.assertNotIn("test-new-secret", output + error)

    def test_setup_reports_partial_completion_and_retains_key_when_files_fail(self):
        replace = os.replace
        for failed_file in (self.catalog, self.config):
            with self.subTest(failed_file=failed_file.name):
                self.config.write_text('approval_policy = "on-request"\n')
                self.catalog.write_text('{"original": true}')
                self.values["key"] = "test-original-secret"

                def fail_replace(source, destination):
                    if Path(destination).resolve() == failed_file.resolve():
                        raise OSError("test-private-filesystem-secret")
                    return replace(source, destination)

                with patch.dict(os.environ, {"NINEROUTER_KEY": "test-retry-secret"}), patch.object(gateway.os, "replace", side_effect=fail_replace):
                    result, output, error = self.command("setup-codex", "--reuse-saved-key")
                self.assertEqual(result, 1)
                self.assertIn("Credential verified and saved", error)
                self.assertIn("Codex configuration unchanged", error)
                self.assertEqual(self.values["key"], "test-retry-secret")
                self.assertEqual(self.config.read_text(), 'approval_policy = "on-request"\n')
                if failed_file == self.catalog:
                    self.assertIn("Model catalog unchanged", error)
                    self.assertEqual(json.loads(self.catalog.read_text()), {"original": True})
                else:
                    self.assertIn("Model catalog updated", error)
                    self.assertIn("models", json.loads(self.catalog.read_text()))
                self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["config.toml", "models_9router_jala.json"])
                for secret in ("test-private-filesystem-secret", "test-retry-secret", "test-original-secret"):
                    self.assertNotIn(secret, output + error)

    def test_failed_setup_retry_keeps_explicit_auth_mode(self):
        replace = os.replace
        for mode, previous_mode in (("chatgpt", "api"), ("api", "chatgpt")):
            for failed_file in (self.catalog, self.config):
                with self.subTest(mode=mode, failed_file=failed_file.name):
                    original = f'forced_login_method = "{previous_mode}"\napproval_policy = "on-request"\n'
                    self.config.write_text(original)
                    self.catalog.write_text('{"original": true}')
                    self.values["key"] = "test-mode-retry-secret"

                    def fail_replace(source, destination):
                        if Path(destination).resolve() == failed_file.resolve():
                            raise OSError("test-private-error")
                        return replace(source, destination)

                    with patch.object(gateway.os, "replace", side_effect=fail_replace):
                        result, output, error = self.command("setup-codex", "--reuse-saved-key", "--auth-mode", mode)
                    self.assertEqual(result, 1)
                    self.assertEqual(self.config.read_text(), original)
                    self.assertIn(f"setup-codex --reuse-saved-key --auth-mode {mode}", error)
                    self.assertNotIn("test-mode-retry-secret", output + error)
                    self.assertNotIn("test-private-error", output + error)

                    retry = error.split("Retry setup with ", 1)[1].split(" after fixing", 1)[0]
                    result, output, error = self.command(*shlex.split(retry))
                    self.assertEqual((result, error), (0, ""))
                    document = gateway.tomllib.loads(self.config.read_text())
                    self.assertEqual(document["forced_login_method"], mode)
                    self.assertEqual(document["model_providers"]["9router-jala"]["requires_openai_auth"], mode == "chatgpt")
                    self.assertEqual(document["approval_policy"], "on-request")
                    self.assertEqual(self.values["key"], "test-mode-retry-secret")
                    self.assertNotIn("test-mode-retry-secret", output + error)

    def test_browser_setup_reports_saved_credential_when_configuration_write_fails(self):
        replace = os.replace

        def fail_config(source, destination):
            if Path(destination).resolve() == self.config.resolve():
                raise OSError("test-private-filesystem-secret")
            return replace(source, destination)

        with gateway.setup_server(configure=True) as server, patch.object(gateway.os, "replace", side_effect=fail_config):
            worker = threading.Thread(target=server.handle_request)
            worker.start()
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}{server.setup_endpoint}",
                data=b'{"key":"test-browser-secret","auth_mode":"chatgpt"}',
                headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{server.server_port}", "X-Setup-Token": server.setup_url.split("token=")[1]},
            )
            try:
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                body = caught.exception.read()
            finally:
                worker.join(timeout=5)
            self.assertEqual(caught.exception.code, 400)
            self.assertFalse(server.completed)
        self.assertIn("Credential verified and saved", json.loads(body)["error"])
        self.assertIn("Model catalog updated", json.loads(body)["error"])
        self.assertEqual(self.values["key"], "test-browser-secret")
        self.assertFalse(self.config.exists())
        self.assertNotIn(b"test-browser-secret", body)
        self.assertNotIn(b"test-private-filesystem-secret", body)
        self.assertIn("setup-codex --reuse-saved-key --auth-mode chatgpt", json.loads(body)["error"])
        retry = json.loads(body)["error"].split("Retry setup with ", 1)[1].split(" after fixing", 1)[0]
        result, output, error = self.command(*shlex.split(retry))
        self.assertEqual((result, error), (0, ""))
        document = gateway.tomllib.loads(self.config.read_text())
        self.assertEqual(document["forced_login_method"], "chatgpt")
        self.assertTrue(document["model_providers"]["9router-jala"]["requires_openai_auth"])
        self.assertNotIn("test-browser-secret", output + error)

    def test_lifecycle_refuses_symlinked_home_and_configuration(self):
        self.config.write_text('approval_policy = "on-request"\n')
        self.values["key"] = "test-symlink-secret"
        link = self.home / "linked-codex"
        link.symlink_to(self.root, target_is_directory=True)
        for command in (("setup-codex", "--reuse-saved-key"), ("revert-codex",), ("backup-codex-key",)):
            with self.subTest(command=command), patch.dict(os.environ, {"CODEX_HOME": str(link)}):
                result, output, error = self.command(*command)
                self.assertEqual(result, 1)
                self.assertIn("symlink", error)
                self.assertEqual(self.config.read_text(), 'approval_policy = "on-request"\n')
                self.assertFalse(self.catalog.exists())
                self.assertNotIn("test-symlink-secret", output + error)
        original = self.home / "original.toml"
        self.config.rename(original)
        self.config.symlink_to(original)
        for command in (("setup-codex", "--reuse-saved-key"), ("revert-codex",)):
            result, _, error = self.command(*command)
            self.assertEqual(result, 1)
            self.assertIn("symlink", error)
            self.assertEqual(original.read_text(), 'approval_policy = "on-request"\n')

    def test_revert_write_failure_preserves_configuration_and_backed_up_key(self):
        original = 'model_provider = "9router-jala"\n[model_providers.9router-jala]\nexperimental_bearer_token = "test-revert-secret"\n'
        self.config.write_text(original)
        with patch.object(gateway.os, "replace", side_effect=OSError("test-private-filesystem-secret")):
            result, output, error = self.command("revert-codex")
        self.assertEqual(result, 1)
        self.assertIn("Plugin credential preserved", error)
        self.assertIn("Codex configuration unchanged", error)
        self.assertEqual(self.config.read_text(), original)
        self.assertEqual(self.values["key"], "test-revert-secret")
        self.assertEqual(list(self.root.iterdir()), [self.config])
        self.assertNotIn("test-revert-secret", output + error)
        self.assertNotIn("test-private-filesystem-secret", output + error)

    def test_revert_stops_when_native_credential_preservation_cannot_be_verified(self):
        original = 'model_provider = "9router-jala"\n[model_providers.9router-jala]\nexperimental_bearer_token = "test-preserve-secret"\n'
        for failure in ("locked", "readback", "invalid-saved-key"):
            with self.subTest(failure=failure):
                self.config.write_text(original)
                self.values.clear()
                if failure == "locked":
                    self.store.get_password.side_effect = RuntimeError("test-locked-secret")
                elif failure == "readback":
                    self.store.get_password.side_effect = lambda *args: None
                else:
                    self.store.get_password.side_effect = lambda *args: "test-invalid-\u00e9-secret"
                result, output, error = self.command("revert-codex")
                self.assertEqual(result, 1)
                self.assertEqual(self.config.read_text(), original)
                self.assertFalse(gateway.credential_path().exists())
                for secret in ("test-preserve-secret", "test-locked-secret", "test-invalid-\u00e9-secret"):
                    self.assertNotIn(secret, output + error)

    def test_setup_reports_uncertain_credential_storage_without_changing_configuration(self):
        self.config.write_text('approval_policy = "on-request"\n')
        self.store.get_password.side_effect = lambda *args: None
        with patch.dict(os.environ, {"NINEROUTER_KEY": "test-uncertain-secret"}), patch.object(gateway.os, "replace", side_effect=OSError("test-private-error")):
            result, output, error = self.command("setup-codex", "--reuse-saved-key")
        self.assertEqual(result, 1)
        self.assertIn("credential storage could not be confirmed", error)
        self.assertIn("Codex configuration unchanged", error)
        self.assertEqual(self.config.read_text(), 'approval_policy = "on-request"\n')
        self.assertFalse(self.catalog.exists())
        self.assertNotIn("test-uncertain-secret", output + error)
        self.assertNotIn("test-private-error", output + error)

    def test_backup_command_remains_compatible_and_does_not_edit_configuration(self):
        original = '[model_providers.9router-jala]\nexperimental_bearer_token = "test-backup-secret"\n'
        self.config.write_text(original)
        result, output, error = self.command("backup-codex-key")
        self.assertEqual((result, error), (0, ""))
        self.assertEqual(self.values["key"], "test-backup-secret")
        self.assertEqual(self.config.read_text(), original)
        self.assertNotIn("test-backup-secret", output)
        self.assertEqual(self.command("revert-codex")[0], 0)

    def test_revert_preserves_global_settings_when_another_provider_is_active(self):
        self.values["key"] = "test-inactive-secret"
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        document = gateway.tomlkit.parse(self.config.read_text())
        document["preferred_auth_method"] = "apikey"
        document["model_provider"] = "other"
        self.config.write_text(gateway.tomlkit.dumps(document))
        result, output, error = self.command("revert-codex")
        self.assertEqual((result, error), (0, ""))
        document = gateway.tomllib.loads(self.config.read_text())
        self.assertEqual(document["model_provider"], "other")
        self.assertEqual(document["model"], "9router-jala")
        self.assertEqual(document["preferred_auth_method"], "apikey")
        self.assertEqual(document["forced_login_method"], "chatgpt")
        self.assertEqual(document["model_reasoning_effort"], "high")
        self.assertNotIn("model_catalog_json", document)
        self.assertNotIn("9router-jala", document.get("model_providers", {}))
        self.assertIn('"model"', output)
        self.assertIn("preferred_auth_method", output)

    def test_orphaned_owned_settings_require_credential_preservation(self):
        for original in ('model_provider = "9router-jala"\n', f'model_catalog_json = {json.dumps(str(self.catalog.resolve()))}\n'):
            with self.subTest(original=original):
                self.config.write_text(original)
                result, _, error = self.command("revert-codex")
                self.assertEqual(result, 1)
                self.assertIn("valid 9Router key", error)
                self.assertEqual(self.config.read_text(), original)


if __name__ == "__main__":
    unittest.main()
