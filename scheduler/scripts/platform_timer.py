"""One user-level catch-up timer. Native clocks handle live sessions."""
from __future__ import annotations

import csv
import io
import os
import plistlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from collections.abc import Callable

LABEL = "tech.jala.session-scheduler"


def systemd_quote(value: str) -> str:
    return '"' + value.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def plan(platform: str, user_home: Path, state: Path, script: Path, python: str,
         sid: str, search_path: str) -> dict[str, Any]:
    args = [python, str(script), "--state-home", str(state), "tick"]
    if platform == "darwin":
        file = user_home / "Library/LaunchAgents" / (LABEL + ".plist")
        content = plistlib.dumps({"Label": LABEL, "ProgramArguments": args, "RunAtLoad": True,
                                 "StartInterval": 60, "ProcessType": "Background",
                                 "EnvironmentVariables": {"SESSION_SCHEDULER_HOME": str(state), "PATH": search_path}}).decode()
        domain = f"gui/{os.getuid() if hasattr(os, 'getuid') else 0}"
        return {"files": [{"path": str(file), "content": content}],
                "commands": [["launchctl", "bootstrap", domain, str(file)]],
                "stop": [["launchctl", "bootout", f"{domain}/{LABEL}"]]}
    if platform.startswith("linux"):
        directory = user_home / ".config/systemd/user"
        service = directory / "session-scheduler.service"
        timer = directory / "session-scheduler.timer"
        content = ("[Unit]\nDescription=Session Scheduler catch-up\n[Service]\nType=oneshot\nTimeoutStartSec=infinity\n"
                   + "Environment=" + systemd_quote("SESSION_SCHEDULER_HOME=" + str(state)) + "\n"
                   + "Environment=" + systemd_quote("PATH=" + search_path) + "\n"
                   + "ExecStart=" + " ".join(systemd_quote(arg) for arg in args) + "\n")
        timing = "[Unit]\nDescription=Session Scheduler minute tick\n[Timer]\nOnCalendar=*-*-* *:*:00\nPersistent=true\nAccuracySec=1s\n[Install]\nWantedBy=timers.target\n"
        return {"files": [{"path": str(service), "content": content}, {"path": str(timer), "content": timing}],
                "commands": [["systemctl", "--user", "daemon-reload"], ["systemctl", "--user", "enable", "--now", timer.name]],
                "stop": [["systemctl", "--user", "disable", "--now", timer.name]]}
    if platform == "win32":
        ns = "http://schemas.microsoft.com/windows/2004/02/mit/task"
        ET.register_namespace("", ns)
        def element(parent: ET.Element, tag: str, value: str | None = None, **attributes: str) -> ET.Element:
            node = ET.SubElement(parent, "{" + ns + "}" + tag, attributes)
            node.text = value
            return node
        task = ET.Element("{" + ns + "}Task", {"version": "1.2"})
        triggers = element(task, "Triggers")
        timed = element(triggers, "TimeTrigger")
        repeat = element(timed, "Repetition")
        element(repeat, "Interval", "PT1M")
        element(repeat, "StopAtDurationEnd", "false")
        element(timed, "StartBoundary", "2020-01-01T00:00:00")
        element(timed, "Enabled", "true")
        login = element(triggers, "LogonTrigger")
        element(login, "Enabled", "true")
        element(login, "UserId", sid)
        principals = element(task, "Principals")
        principal = element(principals, "Principal", id="Author")
        element(principal, "UserId", sid)
        element(principal, "LogonType", "InteractiveToken")
        element(principal, "RunLevel", "LeastPrivilege")
        settings = element(task, "Settings")
        element(settings, "MultipleInstancesPolicy", "IgnoreNew")
        element(settings, "DisallowStartIfOnBatteries", "false")
        element(settings, "StopIfGoingOnBatteries", "false")
        element(settings, "StartWhenAvailable", "true")
        element(settings, "ExecutionTimeLimit", "PT0S")
        element(settings, "Enabled", "true")
        action = element(element(task, "Actions", Context="Author"), "Exec")
        element(action, "Command", python)
        element(action, "Arguments", subprocess.list2cmdline([str(script), "--state-home", str(state), "tick"]))
        element(action, "WorkingDirectory", str(state))
        file = state / "runner/task.xml"
        return {"files": [{"path": str(file), "content": ET.tostring(task, encoding="unicode")}],
                "commands": [["schtasks", "/Create", "/TN", LABEL, "/XML", str(file), "/F"]],
                "stop": [["schtasks", "/Delete", "/TN", LABEL, "/F"]]}
    raise ValueError("Supported timer platforms: macOS, Linux, Windows")


def configure(state: Path, script: Path, install: bool, dry_run: bool,
              before_stop: Callable[[], None] | None = None) -> dict[str, Any]:
    sid = ""
    if sys.platform == "win32":
        output = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True)
        sid = list(csv.reader(io.StringIO(output)))[0][1]
    stable = state / "runner"
    commands = plan(sys.platform, Path.home(), state, stable / "scripts" / script.name, sys.executable,
                    sid, os.environ.get("PATH", ""))
    if dry_run:
        return commands
    if before_stop:
        before_stop()
    for command in commands["stop"]:
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if install:
        stable.mkdir(mode=0o700, exist_ok=True)
        (stable / "scripts").mkdir(exist_ok=True)
        for name in ("scheduler.py", "scheduler_core.py", "platform_timer.py"):
            target = stable / "scripts" / name
            temporary = stable / "scripts" / (name + ".new")
            shutil.copyfile(script.parent / name, temporary)
            temporary.chmod(0o600)
            os.replace(temporary, target)
        for component in (".claude-plugin", "hooks", "skills"):
            shutil.copytree(script.parent.parent / component, stable / component, dirs_exist_ok=True)
        shutil.copyfile(script.parent.parent / "requirements.txt", stable / "requirements.txt")
        for item in commands["files"]:
            target = Path(item["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item["content"])
            target.chmod(0o600)
        for command in commands["commands"]:
            subprocess.run(command, check=True)
    else:
        for item in commands["files"]:
            Path(item["path"]).unlink(missing_ok=True)
        if sys.platform.startswith("linux"):
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    return {"installed": install, "timer": LABEL}
