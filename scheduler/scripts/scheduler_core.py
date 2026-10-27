"""Persistent, latest-only scheduled continuations. No agent or OS configuration."""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

import psutil
from croniter import croniter

Document = dict[str, Any]


class DeliveryDeferred(Exception):
    """The backend proved no model turn was delivered because the session is busy."""


def process_identity(pid: int | None = None) -> tuple[int, float]:
    process = psutil.Process(pid)
    return process.pid, process.create_time()


def alive(pid: int, born: float) -> bool:
    try:
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE and process.create_time() == born
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        return True


def latest_occurrence(expression: str, zone: str, now: float) -> float:
    """Use wall-clock cron arithmetic, validating gaps and collapsing repeated minutes."""
    tz = ZoneInfo(zone)
    local = datetime.fromtimestamp(now, tz)
    wall = local.replace(tzinfo=None)
    if local.fold:
        wall += abs(local.replace(fold=0).utcoffset() - local.utcoffset())  # type: ignore[operator]
    iterator = croniter(expression, wall + timedelta(microseconds=1), max_years_between_matches=8)
    for _ in range(512):
        candidate = iterator.get_prev(datetime)
        stamp = candidate.replace(tzinfo=tz, fold=0).timestamp()
        restored = datetime.fromtimestamp(stamp, tz).replace(tzinfo=None)
        if restored == candidate and stamp <= now:
            return stamp
    raise ValueError("Could not resolve the cron schedule in this timezone")


class Scheduler:
    def __init__(self, home: Path, clock: Callable[[], float] = time.time):
        self.home = home
        self.clock = clock
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        if home.is_symlink():
            raise ValueError("Scheduler state directory must not be a symlink")
        if os.name != "nt":
            home.chmod(0o700)
        self.path = home / "state.sqlite"
        if self.path.is_symlink():
            raise ValueError("Scheduler state must not be a symlink")
        fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        if os.name != "nt":
            self.path.chmod(0o600)
        with self._transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS schedules (engine TEXT, session TEXT, data TEXT NOT NULL, PRIMARY KEY(engine,session))")
            db.execute("CREATE TABLE IF NOT EXISTS leases (engine TEXT, session TEXT, pid INTEGER, born REAL, token TEXT, PRIMARY KEY(engine,session))")
            db.execute("CREATE TABLE IF NOT EXISTS history (engine TEXT, session TEXT, written REAL, pid INTEGER, born REAL, PRIMARY KEY(engine,session))")
            db.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT)")

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _read(db: sqlite3.Connection, engine: str, session: str) -> Document | None:
        row = db.execute("SELECT data FROM schedules WHERE engine=? AND session=?", (engine, session)).fetchone()
        return cast(Document, json.loads(row[0])) if row else None

    @staticmethod
    def _write(db: sqlite3.Connection, job: Document) -> None:
        db.execute("INSERT OR REPLACE INTO schedules VALUES (?,?,?)", (job["engine"], job["session_id"], json.dumps(job)))

    def save(self, engine: str, session: str, cwd: str, cron: str, zone: str, prompt: str,
             cli_path: str | None = None, owner: tuple[int, float] | None = None) -> Document:
        if engine not in ("codex", "claude") or not session.strip() or not prompt.strip():
            raise ValueError("Agent type, exact session ID, and a nonempty prompt are required")
        if len(cron.split()) != 5 or not croniter.is_valid(cron, strict=True):
            raise ValueError("Use a valid five-field cron schedule")
        tz = ZoneInfo(zone)
        croniter(cron, datetime.fromtimestamp(self.clock(), tz).replace(tzinfo=None), max_years_between_matches=8).get_next(datetime)
        work = Path(cwd).expanduser().resolve(strict=True)
        if not work.is_dir():
            raise ValueError("Working directory must exist")
        with self._transaction() as db:
            old = self._read(db, engine, session)
            if old and old.get("running") and alive(old["running"]["pid"], old["running"]["born"]):
                raise ValueError("Wait for the active continuation before editing its schedule")
            job: Document = {"engine": engine, "session_id": session, "cwd": str(work), "cron": cron,
                             "timezone": zone, "prompt": prompt, "key": uuid.uuid4().hex,
                             "created_at": self.clock(), "handled_at": self.clock(),
                             "native_id": None, "renew_at": None, "running": None,
                             "status": "setup_required", "last_error": None, "cli_path": cli_path}
            self._write(db, job)
            pid, born = owner or process_identity()
            db.execute("INSERT OR REPLACE INTO history VALUES (?,?,?,?,?)", (engine, session, self.clock(), pid, born))
            return job

    def list(self, engine: str | None = None) -> list[Document]:
        with self._transaction() as db:
            rows = db.execute("SELECT data FROM schedules ORDER BY engine,session").fetchall()
        return [job for row in rows if (job := cast(Document, json.loads(row[0]))) and (not engine or job["engine"] == engine)]

    def bind(self, engine: str, session: str, native_id: str, key: str | None = None,
             owner: tuple[int, float] | None = None) -> None:
        if not native_id.strip():
            raise ValueError("A native timer ID is required")
        with self._transaction() as db:
            job = self._read(db, engine, session)
            if not job:
                raise ValueError("Schedule not found")
            if key is not None and job["key"] != key:
                raise ValueError("Schedule changed while creating its native timer")
            job.update(native_id=native_id, renew_at=self.clock() + 6 * 86400 if engine == "claude" else None,
                       native_expires_at=self.clock() + 7 * 86400 if engine == "claude" else None,
                       native_owner=list(owner or process_identity()), repair_after=0, repair_owner=None, status="ready")
            self._write(db, job)

    def request_repair(self, engine: str, session: str, owner: tuple[int, float] | None = None) -> Document | None:
        """A resumed live Claude client may have lost its seven-day native clock."""
        with self._transaction() as db:
            job = self._read(db, engine, session)
            identity = list(owner or process_identity())
            if (not job or engine != "claude" or not job["native_id"] or job["running"]
                    or (job.get("native_owner") == identity and self.clock() < job.get("native_expires_at", float("inf")))
                    or (job.get("repair_owner") == identity and self.clock() < job.get("repair_after", 0))):
                return None
            job.update(repair_after=self.clock() + 86400, repair_owner=identity, status="timer_needs_repair",
                       last_error="Native clock expired; lifecycle hook requested restoration")
            self._write(db, job)
            return job

    def cancel(self, engine: str, session: str) -> Document | None:
        with self._transaction() as db:
            job = self._read(db, engine, session)
            db.execute("DELETE FROM schedules WHERE engine=? AND session=?", (engine, session))
            return job

    def claim(self, engine: str, session: str, key: str | None = None,
              owner: tuple[int, float] | None = None, maintenance: bool = False) -> Document | None:
        with self._transaction() as db:
            job = self._read(db, engine, session)
            if not job or not job["native_id"] or (key is not None and key != job["key"]):
                return None
            if running := job["running"]:
                if alive(running["pid"], running["born"]):
                    return None
                job.update(running=None, status="interrupted", last_error="Previous client exited before recording completion")
            occurrence = latest_occurrence(job["cron"], job["timezone"], self.clock())
            due = occurrence > job["handled_at"]
            identity = owner or process_identity()
            renew = (engine == "claude" and (self.clock() >= job["renew_at"] or job.get("native_owner") != list(identity))
                     and (due or maintenance))
            if not due and not renew:
                self._write(db, job)
                return None
            pid, born = identity
            dispatch: Document = {"token": uuid.uuid4().hex, "occurrence": occurrence if due else None,
                                  "prompt": job["prompt"] if due else None, "renew": renew,
                                  "pid": pid, "born": born, "previous_handled_at": job["handled_at"]}
            if due:
                job["handled_at"] = occurrence
            if renew:
                job["renew_at"] = self.clock() + 86400
            job.update(running=dispatch, status="running", last_error=None)
            self._write(db, job)
            return dispatch

    def finish(self, engine: str, session: str, token: str, status: str, error: str | None = None) -> None:
        with self._transaction() as db:
            job = self._read(db, engine, session)
            if job and job["running"] and job["running"]["token"] == token:
                db.execute("INSERT OR REPLACE INTO history VALUES (?,?,?,?,?)", (engine, session, self.clock(), job["running"]["pid"], job["running"]["born"]))
                job.update(running=None, status=status, last_error=error)
                self._write(db, job)

    def acknowledge(self, engine: str, session: str, token: str, status: str,
                    owner: tuple[int, float]) -> None:
        """Cold delivery completes only after both host hooks and CLI acknowledgement."""
        with self._transaction() as db:
            job = self._read(db, engine, session)
            if (job and job["running"] and job["running"]["token"] == token
                    and (job["running"]["pid"], job["running"]["born"]) == owner):
                # SessionEnd must not overwrite a successfully acknowledged Stop.
                if not job["running"].get("acknowledged"):
                    job["running"]["acknowledged"] = status
                    self._write(db, job)

    def reserve(self, engine: str, session: str, worker: bool = False) -> str | None:
        """Reserve an inactive client before starting a background resume process."""
        pid, born = process_identity()
        with self._transaction() as db:
            enabled = db.execute("SELECT value FROM settings WHERE name='worker_enabled'").fetchone()
            if worker and enabled and enabled[0] == "0":
                return None
            row = db.execute("SELECT pid,born FROM leases WHERE engine=? AND session=?", (engine, session)).fetchone()
            if row and alive(row[0], row[1]):
                return None
            token = "worker-" + uuid.uuid4().hex
            db.execute("INSERT OR REPLACE INTO leases VALUES (?,?,?,?,?)", (engine, session, pid, born, token))
            return token

    def release(self, engine: str, session: str, token: str | None) -> None:
        with self._transaction() as db:
            db.execute("DELETE FROM leases WHERE engine=? AND session=? AND token=?", (engine, session, token))

    def join(self, engine: str, session: str, owner: tuple[int, float], handoff: str | None = None,
             metadata: Document | None = None) -> bool:
        """All Claude foreground and background clients use the same lifetime lease."""
        pid, born = owner
        with self._transaction() as db:
            row = db.execute("SELECT pid,born,token FROM leases WHERE engine=? AND session=?", (engine, session)).fetchone()
            job = self._read(db, engine, session)
            if engine == "claude" and row and alive(row[0], row[1]) and (row[0], row[1]) != owner and row[2] != handoff:
                return False
            history = db.execute("SELECT written,pid,born FROM history WHERE engine=? AND session=?", (engine, session)).fetchone()
            owns = row and (row[0], row[1]) == owner
            transferred = handoff and row and row[2] == handoff
            if (engine == "claude" and job and not owns and not transferred and history
                    and (history[1], history[2]) != owner and born <= history[0]):
                # This process could have loaded a transcript before another
                # client wrote it. Require a fresh process, never stale context.
                return False
            if engine == "claude" and (job or row):
                token = row[2] if row else "client-" + uuid.uuid4().hex
                db.execute("INSERT OR REPLACE INTO leases VALUES (?,?,?,?,?)", (engine, session, pid, born, token))
            if metadata:
                db.execute("CREATE TABLE IF NOT EXISTS receipts (engine TEXT, session TEXT, data TEXT, PRIMARY KEY(engine,session))")
                db.execute("INSERT OR REPLACE INTO receipts VALUES (?,?,?)", (engine, session, json.dumps({**metadata, "pid": pid, "born": born})))
            if handoff and row and row[2] == handoff and job and job["running"]:
                job["running"].update(pid=pid, born=born)
                self._write(db, job)
            return True

    def owns(self, engine: str, session: str, owner: tuple[int, float]) -> bool:
        with self._transaction() as db:
            row = db.execute("SELECT pid,born FROM leases WHERE engine=? AND session=?", (engine, session)).fetchone()
            return bool(row and (row[0], row[1]) == owner)

    def note_turn(self, engine: str, session: str, owner: tuple[int, float]) -> None:
        with self._transaction() as db:
            db.execute("INSERT OR REPLACE INTO history VALUES (?,?,?,?,?)", (engine, session, self.clock(), *owner))

    def leave(self, engine: str, session: str, owner: tuple[int, float]) -> None:
        with self._transaction() as db:
            db.execute("DELETE FROM leases WHERE engine=? AND session=? AND pid=? AND born=?", (engine, session, *owner))

    def receipt(self, engine: str, session: str) -> Document | None:
        with self._transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS receipts (engine TEXT, session TEXT, data TEXT, PRIMARY KEY(engine,session))")
            row = db.execute("SELECT data FROM receipts WHERE engine=? AND session=?", (engine, session)).fetchone()
            return cast(Document, json.loads(row[0])) if row else None

    def pause_worker(self) -> bool:
        """Block future reservations; report whether an existing cold attempt must finish."""
        with self._transaction() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES ('worker_enabled','0')")
            rows = db.execute("SELECT pid,born FROM leases WHERE token LIKE 'worker-%'").fetchall()
            return any(alive(pid, born) for pid, born in rows)

    def enable_worker(self) -> None:
        with self._transaction() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES ('worker_enabled','1')")

    def _defer(self, engine: str, session: str, token: str) -> None:
        with self._transaction() as db:
            job = self._read(db, engine, session)
            if job and job["running"] and job["running"]["token"] == token:
                job.update(handled_at=job["running"]["previous_handled_at"], running=None, status="waiting")
                self._write(db, job)

    def run_pending(self, deliver: Callable[[Document, Document, str], None]) -> None:
        """Cold Claude delivery seam; a live client owns its native clock instead."""
        for job in self.list("claude"):
            session = job["session_id"]
            lease = self.reserve("claude", session, worker=True)
            if lease is None:
                continue
            try:
                dispatch = self.claim("claude", session, job["key"])
                if dispatch is None:
                    continue
                try:
                    deliver(job, dispatch, lease)
                except DeliveryDeferred:
                    self._defer("claude", session, dispatch["token"])
                except Exception as error:
                    self.finish("claude", session, dispatch["token"], "failed", str(error)[:1000])
                else:
                    self.finish("claude", session, dispatch["token"], "completed")
            finally:
                self.release("claude", session, lease)

    def wake_pending_apps(self, wake: Callable[[Document], None]) -> None:
        """Starting a desktop app is not delivery; its native hook claims the work."""
        for job in self.list("codex"):
            if not job["native_id"]:
                continue
            if running := job["running"]:
                if alive(running["pid"], running["born"]):
                    continue
                self.finish("codex", job["session_id"], running["token"], "interrupted", "Previous desktop client exited before recording completion")
            if latest_occurrence(job["cron"], job["timezone"], self.clock()) <= job["handled_at"]:
                continue
            try:
                wake(job)
            except Exception:
                with self._transaction() as db:
                    current = self._read(db, "codex", job["session_id"])
                    if current and current["key"] == job["key"] and not current["running"]:
                        current.update(status="waiting_app", last_error="Open the recorded desktop app once and check its startup configuration")
                        self._write(db, current)
