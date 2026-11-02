#!/usr/bin/env python3
"""Install the local runtime and manage Google Play Console profiles."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from runtime import StorageError, install_runtime, runtime_python


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "status", "list-profiles", "forget-profile", "install-runtime"))
    parser.add_argument("profile", nargs="?", help="Profile name for forget-profile.")
    args = parser.parse_args()
    if args.command == "forget-profile" and not args.profile:
        parser.error("forget-profile requires a profile name")
    if args.command != "forget-profile" and args.profile:
        parser.error("profile name is only accepted for forget-profile")
    try:
        install_runtime(PLUGIN_ROOT)
        if args.command == "install-runtime":
            print("Local runtime installed.")
            return 0
        script = PLUGIN_ROOT / "scripts" / "commands.py"
        command = [str(runtime_python()), str(script), args.command]
        if args.profile:
            command.append(args.profile)
        return subprocess.run(command, check=False).returncode
    except (StorageError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
