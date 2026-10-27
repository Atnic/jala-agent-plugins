"""Behavior at the persisted scheduler, clock, and delivery boundaries."""
import sys
from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scheduler_core import DeliveryDeferred, Scheduler, latest_occurrence, process_identity


def instant(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = instant("2026-01-01T00:00:00")
        self.scheduler = Scheduler(Path(self.directory.name), clock=lambda: self.now)

    def test_after_long_shutdown_only_latest_occurrence_runs_once(self):
        self.scheduler.save("codex", "session-a", self.directory.name, "0 8 * * *", "Asia/Jakarta", "Summarize work")
        self.scheduler.bind("codex", "session-a", "native-a")
        self.now = instant("2026-10-26T04:00:00")
        dispatch = self.scheduler.claim("codex", "session-a")
        self.assertEqual(dispatch["occurrence"], instant("2026-10-26T01:00:00"))
        self.assertEqual(dispatch["prompt"], "Summarize work")
        self.scheduler.finish("codex", "session-a", dispatch["token"], "completed")
        restarted = Scheduler(Path(self.directory.name), clock=lambda: self.now)
        self.assertIsNone(restarted.claim("codex", "session-a"))

    def test_busy_session_does_not_consume_due_work(self):
        self.scheduler.save("claude", "session-b", self.directory.name, "0 * * * *", "UTC", "Check deployment")
        self.scheduler.bind("claude", "session-b", "native-b")
        owner = self.scheduler.reserve("claude", "session-b")
        self.now = instant("2026-01-01T03:20:00")
        delivered = []
        self.scheduler.run_pending(lambda job, dispatch, token: delivered.append(dispatch))
        self.assertEqual(delivered, [])
        self.scheduler.release("claude", "session-b", owner)
        self.scheduler.run_pending(lambda job, dispatch, token: delivered.append(dispatch))
        self.assertEqual([d["occurrence"] for d in delivered], [instant("2026-01-01T03:00:00")])

    def job(self, engine="claude", session="session-c", cron="0 * * * *"):
        saved = self.scheduler.save(engine, session, self.directory.name, cron, "UTC", "Check deployment")
        self.scheduler.bind(engine, session, "native-c")
        return saved

    def test_failure_does_not_retry_but_next_occurrence_is_eligible(self):
        self.job()
        attempts = []
        def fail(job, dispatch, lease):
            attempts.append(dispatch["occurrence"])
            raise RuntimeError("Permission denied")
        self.now = instant("2026-01-01T01:20:00")
        self.scheduler.run_pending(fail)
        self.scheduler.run_pending(fail)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(self.scheduler.list()[0]["status"], "failed")
        self.now = instant("2026-01-01T02:00:00")
        self.scheduler.run_pending(fail)
        self.assertEqual(attempts, [instant("2026-01-01T01:00:00"), instant("2026-01-01T02:00:00")])

    def test_explicit_busy_acknowledgement_keeps_latest_pending(self):
        self.job()
        self.now = instant("2026-01-01T01:20:00")
        def busy(job, dispatch, lease):
            raise DeliveryDeferred()
        self.scheduler.run_pending(busy)
        self.now = instant("2026-01-01T04:20:00")
        delivered = []
        self.scheduler.run_pending(lambda job, dispatch, lease: delivered.append(dispatch["occurrence"]))
        self.assertEqual(delivered, [instant("2026-01-01T04:00:00")])

    def test_active_claim_and_restarted_worker_cannot_duplicate(self):
        self.job("codex")
        self.now = instant("2026-01-01T01:20:00")
        first = self.scheduler.claim("codex", "session-c")
        other = Scheduler(Path(self.directory.name), clock=lambda: self.now)
        self.assertIsNone(other.claim("codex", "session-c"))
        self.scheduler.finish("codex", "session-c", first["token"], "interrupted")
        self.assertIsNone(other.claim("codex", "session-c"))

    def test_overlapping_ticks_have_one_persisted_claim(self):
        self.job("codex")
        self.now += 3601
        def claim(_):
            store = Scheduler(Path(self.directory.name), clock=lambda: self.now)
            return store.claim("codex", "session-c")
        with ThreadPoolExecutor(max_workers=4) as workers:
            claims = list(workers.map(claim, range(4)))
        self.assertEqual(sum(item is not None for item in claims), 1)

    def test_edit_and_cancel_reject_old_native_ticks(self):
        old = self.job("codex")
        self.now = instant("2026-01-01T01:20:00")
        self.job("codex", cron="30 * * * *")
        self.now = instant("2026-01-01T02:40:00")
        self.assertIsNone(self.scheduler.claim("codex", "session-c", old["key"]))
        self.assertEqual(len(self.scheduler.list()), 1)
        cancelled = self.scheduler.cancel("codex", "session-c")
        self.assertEqual(cancelled["native_id"], "native-c")
        self.assertIsNone(self.scheduler.claim("codex", "session-c"))
        self.assertEqual(self.scheduler.list(), [])

    def test_invalid_edit_preserves_existing_definition(self):
        self.job("codex")
        with self.assertRaises(ValueError):
            self.scheduler.save("codex", "session-c", self.directory.name, "0 0 31 2 *", "UTC", "New prompt")
        self.assertEqual(self.scheduler.list()[0]["prompt"], "Check deployment")

    def test_repeated_dst_minute_is_once_and_nonexistent_minute_is_skipped(self):
        self.assertEqual(latest_occurrence("30 1 * * *", "America/New_York", instant("2026-11-01T06:15:00")), instant("2026-11-01T05:30:00"))
        self.assertEqual(latest_occurrence("30 1 * * *", "America/New_York", instant("2026-11-01T06:45:00")), instant("2026-11-01T05:30:00"))
        self.assertEqual(latest_occurrence("30 2 * * *", "America/New_York", instant("2026-03-08T08:00:00")), instant("2026-03-07T07:30:00"))

    def test_rejected_client_cannot_release_the_owner(self):
        self.job()
        token = self.scheduler.reserve("claude", "session-c")
        self.assertFalse(self.scheduler.join("claude", "session-c", (99999999, 0)))
        self.scheduler.leave("claude", "session-c", (99999999, 0))
        self.assertIsNone(self.scheduler.reserve("claude", "session-c"))
        self.assertTrue(self.scheduler.join("claude", "session-c", process_identity(), handoff=token))
        self.scheduler.release("claude", "session-c", token)
        self.assertIsNotNone(self.scheduler.reserve("claude", "session-c"))

    def test_startup_wakes_after_dead_desktop_attempt_without_replaying_it(self):
        self.job("codex")
        self.now += 3601
        dispatch = self.scheduler.claim("codex", "session-c", owner=(99999999, 0))
        wakeups = []
        self.scheduler.wake_pending_apps(lambda job: wakeups.append(job["session_id"]))
        self.assertEqual(wakeups, [])
        self.assertEqual(self.scheduler.list()[0]["status"], "interrupted")
        self.now += 3600
        self.scheduler.wake_pending_apps(lambda job: wakeups.append(job["session_id"]))
        self.assertEqual(wakeups, ["session-c"])
        next_dispatch = self.scheduler.claim("codex", "session-c")
        self.assertGreater(next_dispatch["occurrence"], dispatch["occurrence"])

    def test_paused_worker_finishes_existing_attempt_and_blocks_new_reservations(self):
        self.job()
        lease = self.scheduler.reserve("claude", "session-c", worker=True)
        self.assertTrue(self.scheduler.pause_worker())
        self.scheduler.release("claude", "session-c", lease)
        self.assertIsNone(self.scheduler.reserve("claude", "session-c", worker=True))
        self.scheduler.enable_worker()
        self.assertIsNotNone(self.scheduler.reserve("claude", "session-c", worker=True))

    def test_expired_native_clock_repair_does_not_consume_user_work_or_loop(self):
        self.job()
        self.now = instant("2026-01-10T03:20:00")
        repair = self.scheduler.request_repair("claude", "session-c")
        self.assertEqual(repair["native_id"], "native-c")
        self.assertIsNone(self.scheduler.request_repair("claude", "session-c"))
        self.scheduler.bind("claude", "session-c", "replacement", repair["key"])
        self.assertIsNone(self.scheduler.request_repair("claude", "session-c"))
        dispatch = self.scheduler.claim("claude", "session-c")
        self.assertEqual(dispatch["occurrence"], instant("2026-01-10T03:00:00"))


if __name__ == "__main__":
    unittest.main()
