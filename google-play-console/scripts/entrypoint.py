#!/usr/bin/env python3
"""Prepare the user-local runtime and launch the stdio MCP server."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from runtime import StorageError, install_runtime, runtime_python


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        install_runtime(PLUGIN_ROOT)
    except (StorageError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    server = PLUGIN_ROOT / "scripts" / "server.py"
    os.execv(str(runtime_python()), [str(runtime_python()), str(server)])
    return 1


if __name__ == "__main__":
    sys.exit(main())
