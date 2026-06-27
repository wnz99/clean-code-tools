from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def parse_json(raw_json: str, *, source: str) -> Any:
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:
        error = f"Could not parse {source} as JSON: {exc}"
        raise SystemExit(error) from exc


def load_json_file(path: Path) -> Any:
    return parse_json(path.read_text(), source=str(path))


def run_json_command(command: str) -> Any:
    completed = subprocess.run(  # noqa: S603 - runs caller-provided local lint commands.
        shlex.split(command),
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if not completed.stdout.strip():
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(completed.returncode or 1)
    return parse_json(completed.stdout, source=command)
