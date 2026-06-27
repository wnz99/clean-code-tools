#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "python.clean-code.pyproject.toml"


def run(command: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and completed.returncode != 0:
        print(completed.stdout)
        raise SystemExit(completed.returncode)
    return completed


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="clean-code-python-config-") as raw_tmp:
        tmp = Path(raw_tmp)
        shutil.copyfile(CONFIG, tmp / "pyproject.toml")

        (tmp / "sample.py").write_text(
            """
MAX_ATTEMPTS = 5


def can_retry(failed_attempts: int) -> bool:
    return failed_attempts < MAX_ATTEMPTS
""".lstrip(),
        )
        (tmp / "smelly.py").write_text(
            """
# TODO clean this up
# old_result = calculate_total(order)

def calculate_total(order, include_tax, dry_run, retry, verbose, mode):
    if order.status == "pending":
        return 5
    return 0
""".lstrip(),
        )

        run(["uv", "run", "--project", str(ROOT), "--group", "lint", "ruff", "check", "sample.py"], cwd=tmp)
        run(
            [
                "uv",
                "run",
                "--project",
                str(ROOT),
                "--group",
                "lint",
                "pylint",
                "--rcfile=pyproject.toml",
                "sample.py",
            ],
            cwd=tmp,
        )

        ruff_smelly = run(
            ["uv", "run", "--project", str(ROOT), "--group", "lint", "ruff", "check", "smelly.py"],
            cwd=tmp,
            check=False,
        )
        pylint_smelly = run(
            [
                "uv",
                "run",
                "--project",
                str(ROOT),
                "--group",
                "lint",
                "pylint",
                "--rcfile=pyproject.toml",
                "smelly.py",
            ],
            cwd=tmp,
            check=False,
        )

        if ruff_smelly.returncode == 0:
            print("Expected Ruff to report clean-code findings for smelly.py")
            raise SystemExit(1)
        if pylint_smelly.returncode == 0:
            print("Expected Pylint to report design findings for smelly.py")
            raise SystemExit(1)

        ruff_output = ruff_smelly.stdout
        pylint_output = pylint_smelly.stdout
        required_ruff_codes = ["TD002", "TD003", "ERA001", "ARG001"]
        required_pylint_codes = ["R0913"]
        forbidden_codes = ["FIX002", "R0917"]

        for code in required_ruff_codes:
            if code not in ruff_output:
                print(ruff_output)
                raise SystemExit(f"Expected Ruff output to include {code}")
        for code in required_pylint_codes:
            if code not in pylint_output:
                print(pylint_output)
                raise SystemExit(f"Expected Pylint output to include {code}")
        for code in forbidden_codes:
            combined = f"{ruff_output}\n{pylint_output}"
            if code in combined:
                print(combined)
                raise SystemExit(f"Did not expect duplicate/noisy code {code}")

        print("python_config_check=ok")


if __name__ == "__main__":
    main()
