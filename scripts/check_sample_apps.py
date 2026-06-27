#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


def check_python_app() -> None:
    with tempfile.TemporaryDirectory(prefix="clean-code-python-sample-") as raw_tmp:
        tmp = Path(raw_tmp)
        venv = tmp / ".venv"
        run([sys.executable, "-m", "venv", str(venv)], cwd=tmp)

        python = venv / "bin" / "python"
        ruff = venv / "bin" / "ruff"
        pylint = venv / "bin" / "pylint"
        app = ROOT / "sample-apps" / "python-app"

        run([str(python), "-m", "pip", "install", "--quiet", "ruff>=0.15.0", "pylint>=4.0.0"], cwd=tmp)
        run([str(ruff), "check", "src/clean_pricing.py"], cwd=app)
        run([str(pylint), "--rcfile=pyproject.toml", "src/clean_pricing.py"], cwd=app)

        ruff_smelly = run([str(ruff), "check", "src/smelly_pricing.py"], cwd=app, check=False)
        pylint_smelly = run(
            [str(pylint), "--rcfile=pyproject.toml", "src/smelly_pricing.py"],
            cwd=app,
            check=False,
        )
        if ruff_smelly.returncode == 0 or pylint_smelly.returncode == 0:
            print(ruff_smelly.stdout)
            print(pylint_smelly.stdout)
            raise SystemExit("Expected Python smelly sample to fail linting")

        for code in ["TD002", "TD003", "ERA001", "ARG001"]:
            if code not in ruff_smelly.stdout:
                print(ruff_smelly.stdout)
                raise SystemExit(f"Expected Python smelly Ruff output to include {code}")
        if "R0913" not in pylint_smelly.stdout:
            print(pylint_smelly.stdout)
            raise SystemExit("Expected Python smelly Pylint output to include R0913")


def check_ts_app(app_name: str, clean_script: str, smelly_script: str, expected_rule_ids: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix=f"clean-code-{app_name}-") as raw_tmp:
        tmp = Path(raw_tmp)
        package_json = ROOT / "sample-apps" / app_name / "package.json"
        package_text = package_json.read_text()
        packed = run(["npm", "pack", "--silent"], cwd=ROOT).stdout.strip().splitlines()[-1]
        tarball = ROOT / packed
        try:
            shutil.copytree(ROOT / "sample-apps" / app_name, tmp / app_name)
            isolated_app = tmp / app_name
            isolated_package = package_text.replace('"clean-code-tools": "file:../.."', f'"clean-code-tools": "{tarball}"')
            (isolated_app / "package.json").write_text(isolated_package)
            run(["npm", "install", "--silent"], cwd=isolated_app)
            run(["npm", "run", clean_script, "--silent"], cwd=isolated_app)
            smelly = run(["npm", "run", smelly_script, "--silent"], cwd=isolated_app, check=False)
            if smelly.returncode == 0:
                print(smelly.stdout)
                raise SystemExit(f"Expected isolated {app_name} smelly script to fail linting")
            for rule_id in expected_rule_ids:
                if rule_id not in smelly.stdout:
                    print(smelly.stdout)
                    raise SystemExit(f"Expected isolated {app_name} output to include {rule_id}")
        finally:
            tarball.unlink(missing_ok=True)


def main() -> None:
    check_python_app()
    check_ts_app(
        "ts-backend",
        "lint:clean",
        "lint:smelly",
        [
            "clean-code/todo-format",
            "clean-code/no-commented-out-code",
            "clean-code/no-boolean-flag-arguments",
            "clean-code/no-business-policy-literals",
            "clean-code/no-train-wrecks",
        ],
    )
    check_ts_app(
        "ts-frontend",
        "lint:clean",
        "lint:smelly",
        [
            "clean-code/todo-format",
            "clean-code/no-commented-out-code",
            "clean-code/no-output-argument-mutation",
            "clean-code/no-business-policy-literals",
            "clean-code/no-train-wrecks",
        ],
    )
    print("sample_apps_check=ok")


if __name__ == "__main__":
    main()
