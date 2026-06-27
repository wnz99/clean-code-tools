#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_TARGETS = [
    "src/mcp_server",
    "scripts",
]
PYLINT_TARGETS = [
    "src/mcp_server",
]


def run(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        raise SystemExit(completed.returncode)
    return completed


def main() -> None:
    run(["uv", "run", "--group", "lint", "ruff", "check", *PYTHON_TARGETS])
    run(["uv", "run", "--group", "lint", "pylint", *PYLINT_TARGETS])
    print("repo_python_lint_check=ok")


if __name__ == "__main__":
    main()
