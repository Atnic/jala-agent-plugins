import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scheduler import controller, hook
from scheduler_core import Scheduler, process_identity


class HookTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = 1767225600.0
        self.store = Scheduler(Path(self.directory.name), clock=lambda: self.now)
        self.owner = process_identity()

    def event(self, engine, event, prompt="", owner=None):
        return hook(self.store, engine, {"session_id": "target", "hook_event_name": event,
                                        "cwd": self.directory.name, "prompt": prompt}, owner or self.owner)

    def prepare(self, engine):
        self.event(engine, "SessionStart")
        job = self.store.save(engine, "target", self.directory.name, "0 * * * *", "UTC", "Reply exactly FOUR")
        self.store.bind(engine, "target", "native", job["key"])
        self.event(engine, "UserPromptSubmit", "Schedule confirmed")
        return job

    def test_idle_native_tick_stops_before_model_and_due_tick_supplies_saved_prompt(self):
        job = self.prepare("codex")
        prompt = "<heartbeat>\n<instructions>\n" + controller(job) + "\n</instructions>\n</heartbeat>"
        self.assertFalse(self.event("codex", "UserPromptSubmit", prompt)["continue"])
        self.now += 3601
        result = self.event("codex", "UserPromptSubmit", prompt)
        context = json.loads(result["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(context["saved_prompt"], "Reply exactly FOUR")
        self.event("codex", "Stop")
        self.assertEqual(self.store.list()[0]["status"], "completed")
        self.assertFalse(self.event("codex", "UserPromptSubmit", prompt)["continue"])

    def test_manual_request_is_unchanged_and_rejected_client_cannot_finish_owner_work(self):
        job = self.prepare("claude")
        self.assertEqual(self.event("claude", "UserPromptSubmit", "Help with my code"), {})
        self.now += 3601
        self.event("claude", "UserPromptSubmit", controller(job))
        rejected = self.event("claude", "UserPromptSubmit", "Try a second client", owner=(99999999, 1))
        self.assertEqual(rejected["stopReason"], "SESSION_SCHEDULER_BUSY")
        self.event("claude", "SessionEnd", owner=(99999999, 1))
        self.assertEqual(self.store.list()[0]["status"], "running")
        self.event("claude", "StopFailure")
        self.assertEqual(self.store.list()[0]["status"], "failed")
        self.assertFalse(self.event("claude", "UserPromptSubmit", controller(job))["continue"])

    def test_cancelled_timer_cannot_replay_its_saved_prompt(self):
        job = self.prepare("claude")
        self.store.cancel("claude", "target")
        self.now += 3601
        self.assertFalse(self.event("claude", "UserPromptSubmit", controller(job))["continue"])

    def test_native_creation_binds_only_the_current_controller(self):
        job = self.prepare("claude")
        payload = {"session_id": "target", "hook_event_name": "PostToolUse", "tool_name": "CronCreate",
                   "tool_input": {"prompt": controller(job)},
                   "tool_response": "Scheduled recurring job a1b2c3d4 (Every minute). Session-only."}
        for response in ({"id": "a1b2c3d4", "humanSchedule": "Every minute", "recurring": True, "durable": False},
                         "Scheduled recurring job a1b2c3d4 (Every minute). Session-only."):
            payload["tool_response"] = response
            self.assertEqual(hook(self.store, "claude", payload, self.owner), {})
            self.assertEqual(self.store.list()[0]["native_id"], "a1b2c3d4")
        payload["tool_input"] = {"prompt": "Unrelated reminder"}
        payload["tool_response"] = "Scheduled recurring job e1f2a3b4 (Every minute)."
        hook(self.store, "claude", payload, self.owner)
        self.assertEqual(self.store.list()[0]["native_id"], "a1b2c3d4")

    def test_cold_terminal_hook_requires_worker_acknowledgement_before_completion(self):
        self.prepare("claude")
        self.now += 3601
        dispatch = self.store.claim("claude", "target")
        payload = {"session_id": "target", "hook_event_name": "Stop"}
        hook(self.store, "claude", payload, self.owner, handoff="worker-test", dispatch_token=dispatch["token"])
        pending = self.store.list()[0]
        self.assertEqual(pending["status"], "running")
        self.assertEqual(pending["running"]["acknowledged"], "completed")
        self.store.finish("claude", "target", dispatch["token"], "failed", "Permission denied in CLI result")
        self.assertEqual(self.store.list()[0]["status"], "failed")

    def test_clock_repair_is_maintenance_only_and_has_a_stopping_condition(self):
        self.prepare("claude")
        self.now += 9 * 86400
        repair = self.event("claude", "Stop")
        self.assertEqual(repair["decision"], "block")
        self.assertIn("Restore", repair["reason"])
        self.assertIn("Do not execute saved work in this maintenance step", repair["reason"])
        self.assertIsNone(self.store.list()[0]["running"])
        self.assertEqual(self.event("claude", "Stop"), {})


if __name__ == "__main__":
    unittest.main()
