#!/usr/bin/env python3
"""Session Scheduler CLI and host lifecycle hooks."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import venv
from pathlib import Path
from typing import Any

PREFIX = "Session Scheduler tick: "
ROOT = Path(__file__).resolve().parents[1]
HOOK_INPUT: dict[str, Any] = {}


def home_path() -> Path:
    if len(sys.argv) > 2 and sys.argv[1] == "--state-home":
        return Path(sys.argv[2]).expanduser().absolute()
    if value := os.environ.get("SESSION_SCHEDULER_HOME"):
        return Path(value).expanduser().absolute()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "SessionScheduler"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/SessionScheduler"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "session-scheduler"


def runtime_python(home: Path) -> Path:
    return home / "runtime" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def invoked_command() -> str:
    offset = 3 if len(sys.argv) > 2 and sys.argv[1] == "--state-home" else 1
    return sys.argv[offset] if len(sys.argv) > offset else ""


def bootstrap() -> None:
    home = home_path()
    if invoked_command() == "install-runtime":
        if sys.version_info < (3, 11):
            raise ValueError("Install the private runtime using Python 3.11 or newer")
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        if home.is_symlink() or (home / "runtime").is_symlink():
            raise ValueError("Runtime directory must not be a symlink")
        venv.EnvBuilder(with_pip=True).create(home / "runtime")
        subprocess.run([str(runtime_python(home)), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
        print(json.dumps({"runtime": str(runtime_python(home))}))
        raise SystemExit(0)
    python = runtime_python(home)
    if python.is_file() and Path(sys.prefix).resolve() != (home / "runtime").resolve():
        os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])


def host_identity(engine: str) -> tuple[int, float]:
    import psutil
    binary = shutil.which(engine)
    expected = Path(binary).resolve() if binary else None
    for parent in psutil.Process().parents():
        try:
            if (expected and Path(parent.exe()).resolve() == expected) or parent.name().lower() in (engine, engine + ".exe"):
                return parent.pid, parent.create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    raise ValueError(f"Cannot identify the current {engine} host process")


def desktop_launcher() -> dict[str, str] | None:
    import psutil
    for parent in psutil.Process().parents():
        try:
            executable = Path(parent.exe())
            name = parent.name().lower()
            arguments = parent.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if sys.platform == "darwin" and name in ("chatgpt", "codex"):
            bundles = [p for p in executable.parents if p.suffix == ".app" and p.stem in ("ChatGPT", "Codex")]
            if bundles:
                return {"kind": "bundle", "path": str(bundles[-1]), "executable": str(executable)}
        elif sys.platform != "darwin" and name in ("chatgpt", "codex", "chatgpt.exe", "codex.exe"):
            args = arguments
            if parent.pid != host_identity("codex")[0] and (len(args) == 1 or args[1] not in ("app-server", "exec", "resume", "review", "mcp-server")):
                return {"kind": "executable", "path": str(executable), "executable": str(executable)}
    return None


def wake_codex(store: Any, job: dict[str, Any]) -> None:
    import psutil
    receipt = store.receipt("codex", job["session_id"])
    launcher = receipt.get("app_launcher") if receipt else None
    if not launcher or not Path(launcher["path"]).exists():
        raise ValueError("Desktop launcher is unavailable")
    for process in psutil.process_iter():
        try:
            if process.exe() == launcher["executable"]:
                return
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    command = ["open", "-g", "-a", launcher["path"]] if launcher["kind"] == "bundle" else [launcher["path"]]
    if launcher["kind"] == "bundle":
        subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=True)
    else:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=os.name != "nt")


def controller(job: dict[str, Any]) -> str:
    return (PREFIX + str(job["key"]) + "\n"
            + "Confirmed recurring task: " + json.dumps(job["prompt"], ensure_ascii=False) + "\n"
            + "Cadence: " + str(job["cron"]) + " in " + str(job["timezone"]) + "\n"
            "The Session Scheduler hook checks whether this task is due and prevents duplicate occurrences. "
            "Use saved_prompt from its hook context for the current occurrence. Report the task's outcome in this conversation. "
            "If that context is absent, do not execute the task; report that the scheduler hooks need activation. "
            "If renew_timer is true, renew this session's native minute clock using CronCreate with '* * * * *' "
            "and controller_prompt from the hook context. The PostToolUse hook records the new task ID; delete the old task if present. "
            "A maintenance-only tick renews the clock without executing the task. Use existing permissions and this same conversation.")


def tick_key(engine: str, prompt: str) -> str | None:
    text = prompt.strip()
    if engine == "codex" and text.startswith("<heartbeat>") and "<instructions>" in text:
        text = text.split("<instructions>", 1)[1].lstrip()
    if not text.startswith(PREFIX):
        return None
    first: str = text.splitlines()[0][len(PREFIX):].strip()
    return first if re.fullmatch(r"[a-f0-9]{32}", first) else "invalid"


def hook(store: Any, engine: str, payload: dict[str, Any], owner: tuple[int, float],
         handoff: str | None = None, dispatch_token: str | None = None) -> dict[str, Any]:
    session = str(payload["session_id"])
    event = payload["hook_event_name"]
    quiet: dict[str, Any] = {"continue": False, "suppressOutput": True}
    if event in ("SessionStart", "UserPromptSubmit"):
        metadata = {k: payload.get(k) for k in ("cwd", "transcript_path", "permission_mode")}
        metadata.update(hook_version=1, claude_config_dir=os.environ.get("CLAUDE_CONFIG_DIR"))
        if engine == "codex":
            metadata["app_launcher"] = desktop_launcher()
        if not store.join(engine, session, owner, handoff, metadata):
            return {**quiet, "stopReason": "SESSION_SCHEDULER_BUSY"}
    jobs = [j for j in store.list(engine) if j["session_id"] == session]
    job = jobs[0] if jobs else None
    if engine == "claude" and job and event not in ("SessionStart", "UserPromptSubmit") and not store.owns(engine, session, owner):
        return {}
    if (engine == "claude" and event == "PostToolUse" and job and payload.get("tool_name") == "CronCreate"
            and tick_key(engine, str(payload.get("tool_input", {}).get("prompt", ""))) == job["key"]):
        response = payload.get("tool_response", {})
        native_id = response.get("id") or response.get("jobId") if isinstance(response, dict) else None
        if not native_id:
            match = re.search(r"Scheduled recurring job ([a-f0-9]{8})\b", json.dumps(response))
            native_id = match.group(1) if match else None
        if not native_id or not re.fullmatch(r"[a-f0-9]{8}", str(native_id)):
            raise ValueError("Cannot bind the native clock acknowledgement")
        store.bind(engine, session, str(native_id), job["key"], owner)
        return {}
    if event == "UserPromptSubmit" and (key := tick_key(engine, str(payload.get("prompt", "")))) is not None:
        if not job or key != job["key"]:
            return quiet
        running = job["running"]
        if running and dispatch_token == running["token"] and (running["pid"], running["born"]) == owner:
            dispatch = running
        else:
            if running and (running["pid"], running["born"]) == owner:
                store.finish(engine, session, running["token"], "interrupted", "The previous turn did not report completion")
            dispatch = store.claim(engine, session, key, owner=owner, maintenance=True)
        if dispatch is None:
            return quiet
        context = {"saved_prompt": dispatch["prompt"], "renew_timer": dispatch["renew"] and not handoff,
                   "token": dispatch["token"], "occurrence": dispatch["occurrence"],
                   "old_native_task_id": job["native_id"], "controller_prompt": controller(job),
                   "helper": str(Path(__file__).resolve()), "engine": engine, "session_id": session,
                   "bind_arguments": ["bind", "--engine", engine, "--session-id", session, "--key", job["key"], "--native-id", "NEW_TASK_ID"]}
        return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": json.dumps(context)}}
    if event in ("Stop", "StopFailure", "Interrupt", "SessionEnd") and job and job["running"]:
        running = job["running"]
        if (running["pid"], running["born"]) == owner:
            status = "completed" if event == "Stop" else "failed" if event == "StopFailure" else "interrupted"
            error = None if status == "completed" else f"Host event: {event}"
            if handoff:
                store.acknowledge(engine, session, running["token"], status, owner)
            else:
                store.finish(engine, session, running["token"], status, error)
    if event == "SessionEnd":
        store.leave(engine, session, owner)
    if event in ("Stop", "StopFailure", "Interrupt") and job:
        store.note_turn(engine, session, owner)
    if event == "Stop" and not handoff and (repair := store.request_repair(engine, session, owner)):
        instructions = {"controller_prompt": controller(repair), "helper": str(Path(__file__).resolve()),
                        "bind_arguments": ["bind", "--engine", engine, "--session-id", session, "--key", repair["key"], "--native-id", "NEW_TASK_ID"],
                        "old_native_task_id": repair["native_id"]}
        return {"decision": "block", "reason": "Restore this user's previously confirmed Session Scheduler clock. "
                "Create a recurring CronCreate task with '* * * * *' and controller_prompt below; the PostToolUse hook binds its new ID automatically, "
                "then delete the old task if it still exists. Do not execute saved work in this maintenance step or create another conversation. "
                "If restoration fails, report it and stop without repeating the attempt. " + json.dumps(instructions)}
    return {}


def stop_process(process: subprocess.Popen[str]) -> None:
    import psutil
    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    for child in children:
        try:
            if child.is_running():
                child.kill()
        except psutil.NoSuchProcess:
            pass


def claude_delivery(store: Any, job: dict[str, Any], dispatch: dict[str, Any], lease: str) -> None:
    from scheduler_core import DeliveryDeferred
    receipt = store.receipt("claude", job["session_id"])
    if not receipt or not receipt.get("transcript_path") or not Path(receipt["transcript_path"]).is_file():
        raise ValueError("The original Claude session transcript is unavailable")
    binary = job.get("cli_path") or shutil.which("claude")
    if not binary:
        raise ValueError("Claude executable is unavailable on the runner's PATH")
    env = os.environ.copy()
    # This is a coordinated background client, not a recursive agent invocation.
    env.pop("CLAUDECODE", None)
    if receipt.get("claude_config_dir"):
        env["CLAUDE_CONFIG_DIR"] = receipt["claude_config_dir"]
    listing = subprocess.run([binary, "agents", "--json"], env=env, capture_output=True, text=True, timeout=15, check=True)
    if any(row.get("sessionId") == job["session_id"] for row in json.loads(listing.stdout)):
        raise DeliveryDeferred()
    env["SESSION_SCHEDULER_HANDOFF"] = lease
    env["SESSION_SCHEDULER_DISPATCH"] = dispatch["token"]
    env["SESSION_SCHEDULER_HOME"] = str(store.home)
    command = [binary, "-p", "--plugin-dir", str(ROOT), "--resume", job["session_id"], "--output-format", "json", "--permission-mode", "dontAsk"]
    with subprocess.Popen(command, cwd=job["cwd"], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, start_new_session=os.name != "nt") as process:
        try:
            output, _ = process.communicate(controller(job), timeout=1200)
        except subprocess.TimeoutExpired:
            stop_process(process)
            raise ValueError("Claude continuation timed out; it will not be retried") from None
        try:
            result = json.loads(output)
        except json.JSONDecodeError:
            raise ValueError("Claude did not return a delivery acknowledgement") from None
        if "SESSION_SCHEDULER_BUSY" in str(result.get("result", "")):
            raise DeliveryDeferred()
        if process.returncode or result.get("is_error") or result.get("permission_denials") or result.get("session_id") != job["session_id"]:
            raise ValueError("Claude continuation failed or did not preserve the target session ID")
        acknowledgement = next((j["running"] for j in store.list("claude") if j["session_id"] == job["session_id"]), None)
        if (not result.get("num_turns") or not acknowledgement or acknowledgement["token"] != dispatch["token"]
                or acknowledgement.get("acknowledged") != "completed" or acknowledgement["pid"] != process.pid):
            raise ValueError("Claude delivery was not acknowledged by the target session hooks")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Schedule continuations of existing agent sessions")
    result.add_argument("--state-home")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("install-runtime")
    commands.add_parser("list")
    commands.add_parser("tick")
    commands.add_parser("doctor")
    for name in ("context", "set", "bind", "cancel", "hook", "nudge"):
        command = commands.add_parser(name)
        command.add_argument("--engine", choices=("codex", "claude"), required=True)
        command.add_argument("--session-id", required=name not in ("context", "hook", "nudge"))
        if name == "set":
            command.add_argument("--cwd", required=True)
            command.add_argument("--cron", required=True)
            command.add_argument("--timezone", required=True)
            command.add_argument("--prompt-file", required=True)
        if name == "bind":
            command.add_argument("--native-id", required=True)
            command.add_argument("--key", required=True)
    for name in ("install", "uninstall"):
        command = commands.add_parser(name)
        command.add_argument("--dry-run", action="store_true")
    return result


def main() -> None:
    from scheduler_core import Scheduler, alive
    args = parser().parse_args()
    store = Scheduler(home_path())
    if args.command == "nudge":
        session = str(HOOK_INPUT.get("session_id", ""))
        job = next((j for j in store.list("claude") if j["session_id"] == session), None)
        owner = host_identity("claude")
        if (job and not os.environ.get("SESSION_SCHEDULER_HANDOFF") and store.join("claude", session, owner)
                and (job.get("native_owner") != list(owner) or time.time() >= job.get("native_expires_at", float("inf")))
                and (job.get("repair_owner") != list(owner) or time.time() >= job.get("repair_after", 0))):
            time.sleep(2)
            print("Session Scheduler reports an expired native clock for this previously confirmed schedule. Complete the normal lifecycle checks.", file=sys.stderr)
            raise SystemExit(2)
        return
    if args.command == "hook":
        payload = HOOK_INPUT
        owner = host_identity(args.engine)
        response = hook(store, args.engine, payload, owner, os.environ.get("SESSION_SCHEDULER_HANDOFF"), os.environ.get("SESSION_SCHEDULER_DISPATCH"))
        print(json.dumps(response))
        return
    if args.command == "list":
        print(json.dumps(store.list(), ensure_ascii=False))
    elif args.command == "doctor":
        print(json.dumps({"home": str(store.home), "python": sys.executable, "claude": shutil.which("claude"),
                          "schedules": len(store.list()), "standalone_codex": False}))
    elif args.command == "tick":
        store.wake_pending_apps(lambda job: wake_codex(store, job))
        store.run_pending(lambda job, dispatch, lease: claude_delivery(store, job, dispatch, lease))
    elif args.command in ("install", "uninstall"):
        from platform_timer import configure
        def before_stop() -> None:
            if store.pause_worker():
                raise ValueError("Catch-up runner paused. Let its current attempt finish, then repeat this command")
        result = configure(store.home, Path(__file__).resolve(), args.command == "install", args.dry_run, before_stop)
        if args.command == "install" and not args.dry_run:
            store.enable_worker()
        print(json.dumps(result))
    else:
        engine = args.engine
        session_value = args.session_id or os.environ.get("CODEX_THREAD_ID" if engine == "codex" else "CLAUDE_SESSION_ID")
        if not session_value:
            raise ValueError("Pass the exact current session ID")
        session = str(session_value)
        if args.command in ("context", "set"):
            receipt = store.receipt(engine, session)
            if not receipt or not alive(receipt["pid"], receipt["born"]):
                raise ValueError("No live plugin hook receipt. Install the runtime, activate/trust the hooks, then start or resume the target session")
            if args.command == "context":
                print(json.dumps({"engine": engine, "session_id": session, **receipt}))
                return
        if args.command == "set":
            assert receipt is not None
            if Path(args.cwd).expanduser().resolve() != Path(receipt["cwd"]).resolve():
                raise ValueError("Use the target session's existing working directory")
            if engine == "codex" and not receipt.get("app_launcher"):
                raise ValueError("A supported Codex/ChatGPT desktop launcher is required for startup catch-up")
            old = next((j for j in store.list(engine) if j["session_id"] == session), None)
            binary = shutil.which("claude") if engine == "claude" else None
            if engine == "claude" and (not binary or Path(binary).suffix.lower() in (".cmd", ".bat")):
                raise ValueError("Install the native Claude executable before scheduling")
            current_owner = host_identity(engine)
            if current_owner != (receipt["pid"], receipt["born"]):
                raise ValueError("Another client owns the hook receipt; start or resume the target session here")
            job = store.save(engine, session, args.cwd, args.cron, args.timezone, Path(args.prompt_file).read_text(), binary, current_owner)
            if not store.join(engine, session, (receipt["pid"], receipt["born"])):
                raise ValueError("The target session is owned by another client")
            print(json.dumps({"schedule": job, "controller_prompt": controller(job), "previous_native_id": old["native_id"] if old else None}))
        elif args.command == "bind":
            store.bind(engine, session, args.native_id, args.key, host_identity(engine))
            print(json.dumps({"status": "ready"}))
        elif args.command == "cancel":
            print(json.dumps({"cancelled": store.cancel(engine, session)}))


if __name__ == "__main__":
    os.umask(0o077)
    try:
        bootstrap()
        if invoked_command() in ("hook", "nudge"):
            HOOK_INPUT = json.load(sys.stdin)
        main()
    except Exception as error:
        if invoked_command() == "nudge":
            raise SystemExit(0)
        if invoked_command() == "hook":
            needs_guard = not HOOK_INPUT or tick_key("codex", str(HOOK_INPUT.get("prompt", ""))) is not None
            state = home_path() / "state.sqlite"
            if state.exists():
                try:
                    with sqlite3.connect(f"file:{state}?mode=ro", uri=True) as db:
                        needs_guard |= bool(db.execute("SELECT 1 FROM schedules WHERE engine='claude' AND session=?", (HOOK_INPUT.get("session_id"),)).fetchone())
                except sqlite3.Error:
                    needs_guard = True
            print(json.dumps({"continue": False, "suppressOutput": True, "stopReason": "Session Scheduler hook unavailable; run install-runtime and doctor"} if needs_guard else {}))
            raise SystemExit(0)
        else:
            print(json.dumps({"error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
