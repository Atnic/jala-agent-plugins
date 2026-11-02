#!/usr/bin/env python3
"""Run local Google Play Console profile management commands."""

from __future__ import annotations

import json
import sys

from local_setup import run_setup
from runtime import StorageError, connection_status, forget_profile, list_profiles


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: commands.py setup|status|list-profiles|forget-profile [profile]", file=sys.stderr)
        return 2
    action = sys.argv[1]
    try:
        if action == "setup" and len(sys.argv) == 2:
            result = run_setup()
        elif action == "status" and len(sys.argv) == 2:
            result = connection_status()
        elif action == "list-profiles" and len(sys.argv) == 2:
            result = list_profiles()
        elif action == "forget-profile" and len(sys.argv) == 3:
            result = forget_profile(sys.argv[2])
        else:
            print("Usage: commands.py setup|status|list-profiles|forget-profile [profile]", file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (StorageError, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
