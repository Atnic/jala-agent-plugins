#!/usr/bin/env python3
"""Install the local runtime and launch App Store Connect setup or account actions."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from runtime import StorageError, install_runtime, runtime_python


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "status", "forget", "install-runtime"))
    args = parser.parse_args()
    try:
        result = install_runtime(PLUGIN_ROOT)
        if args.command == "install-runtime":
            print("Local runtime installed.")
            return 0
        script = PLUGIN_ROOT / "scripts" / "local_setup.py"
        completed = subprocess.run([str(runtime_python()), str(script), args.command], check=False)
        return completed.returncode
    except (StorageError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
