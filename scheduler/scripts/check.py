#!/usr/bin/env python3
"""The scheduler's local and CI check entry point."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    skill = ROOT / 'scheduler/skills/scheduler/SKILL.md'
    parts = skill.read_text(encoding='utf-8').split('---', 2)
    metadata = yaml.safe_load(parts[1]) if len(parts) == 3 and not parts[0].strip() else None
    if not isinstance(metadata, dict) or metadata.get('name') != 'scheduler' or not metadata.get('description'):
        raise ValueError('Scheduler skill needs valid YAML name and description')
    # This native desktop branch cannot instruct users to open a CLI-only menu.
    for path in (skill, skill.parent / 'references/native.md', ROOT / 'scheduler/README.md'):
        if '/hooks' in path.read_text(encoding='utf-8'):
            raise ValueError(f'{path.relative_to(ROOT)}: native setup must not require the CLI hook menu')
    checks = [
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'scheduler/tests', '-v'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', '.agents/skills/create-plugin/tests', '-v'],
        [sys.executable, '-m', 'mypy', '--strict', 'scheduler/scripts'],
        [sys.executable, '.agents/skills/create-plugin/scripts/validate_plugin.py', 'scheduler'],
    ]
    for command in checks:
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
