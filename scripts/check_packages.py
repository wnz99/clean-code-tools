#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
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


def npm_pack_payload(output: str) -> list[dict[str, object]]:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        start = output.find("[")
        end = output.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise SystemExit(f"Could not parse npm pack JSON output:\n{output}") from None
        payload = json.loads(output[start : end + 1])
    if not isinstance(payload, list) or not payload:
        raise SystemExit(f"Expected npm pack JSON array, got:\n{output}")
    return payload


def check_npm_package() -> None:
    packed = run(["npm", "pack", "--dry-run", "--json"]).stdout
    package_files = {item["path"] for item in npm_pack_payload(packed)[0]["files"]}
    required_files = {
        "src/js/eslint-plugin-clean-code.mjs",
        "configs/eslint.clean-code.recommended.mjs",
    }
    missing_files = sorted(required_files - package_files)
    if missing_files:
        raise SystemExit(f"npm package missing files: {', '.join(missing_files)}")
    forbidden_prefixes = (
        "data/",
        "docs/",
        "evals/",
        "ops/",
        "sample-apps/",
        "scripts/",
        "skills/",
        "src/python/",
    )
    forbidden_files = {
        "pyproject.toml",
        "uv.lock",
        "configs/python.clean-code.pyproject.toml",
    }
    unexpected_files = sorted(
        path
        for path in package_files
        if path in forbidden_files or path.startswith(forbidden_prefixes)
    )
    if unexpected_files:
        raise SystemExit(f"npm package includes non-runtime files: {', '.join(unexpected_files)}")


def check_version_parity() -> None:
    package_json = json.loads((ROOT / "package.json").read_text())
    try:
        import tomllib
    except ImportError as exc:  # pragma: no cover - Python 3.12 project
        raise SystemExit("Python 3.11+ is required for tomllib") from exc
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    npm_version = package_json["version"]
    python_version = pyproject["project"]["version"]
    if npm_version == python_version:
        return
    raise SystemExit(
        f"Package versions must match for dual publishing: npm={npm_version}, python={python_version}"
    )


def wheel_files(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def sdist_files(path: Path) -> set[str]:
    with tarfile.open(path) as archive:
        files = set()
        for member in archive.getmembers():
            if not member.isfile():
                continue
            parts = Path(member.name).parts
            files.add(str(Path(*parts[1:])))
        return files


def assert_no_forbidden_files(
    *,
    artifact_name: str,
    package_files: set[str],
    forbidden_prefixes: tuple[str, ...],
    forbidden_files: set[str] | None = None,
) -> None:
    forbidden_files = forbidden_files or set()
    unexpected_files = sorted(
        path
        for path in package_files
        if path in forbidden_files or path.startswith(forbidden_prefixes)
    )
    if unexpected_files:
        raise SystemExit(
            f"{artifact_name} includes non-runtime files: {', '.join(unexpected_files)}"
        )


def venv_executable(venv: Path, executable: str) -> Path:
    return venv / "bin" / executable


def installed_python_config(venv: Path) -> str:
    script = (
        "from importlib.resources import files\n"
        "print(files('clean_code_tools_pylint').joinpath("
        "'configs/python.clean-code.pyproject.toml').read_text())\n"
    )
    return run([str(venv_executable(venv, "python")), "-c", script], cwd=venv).stdout


def check_python_package() -> None:
    with tempfile.TemporaryDirectory(prefix="clean-code-package-") as raw_tmp:
        tmp = Path(raw_tmp)
        dist = tmp / "dist"
        run(["uv", "build", "--out-dir", str(dist)])
        wheels = sorted(dist.glob("clean_code_tools_python-*.whl"))
        if not wheels:
            raise SystemExit("Expected uv build to create a clean-code-tools-python wheel")
        sdists = sorted(dist.glob("clean_code_tools_python-*.tar.gz"))
        if not sdists:
            raise SystemExit("Expected uv build to create a clean-code-tools-python sdist")

        wheel_package_files = wheel_files(wheels[-1])
        required_wheel_files = {
            "clean_code_tools_pylint/__init__.py",
            "clean_code_tools_pylint/ast_checker.py",
            "clean_code_tools_pylint/comments.py",
            "clean_code_tools_pylint/helpers.py",
            "clean_code_tools_pylint/configs/python.clean-code.pyproject.toml",
        }
        missing_wheel_files = sorted(required_wheel_files - wheel_package_files)
        if missing_wheel_files:
            raise SystemExit(f"Python wheel missing files: {', '.join(missing_wheel_files)}")
        assert_no_forbidden_files(
            artifact_name="Python wheel",
            package_files=wheel_package_files,
            forbidden_prefixes=(
                "data/",
                "docs/",
                "evals/",
                "ops/",
                "sample-apps/",
                "scripts/",
                "skills/",
                "src/",
                "tests/",
            ),
            forbidden_files={"uv.lock", "package.json", "bun.lock"},
        )

        sdist_package_files = sdist_files(sdists[-1])
        required_sdist_files = {
            "README.md",
            "pyproject.toml",
            "configs/python.clean-code.pyproject.toml",
            "src/python/clean_code_tools_pylint/__init__.py",
            "src/python/clean_code_tools_pylint/ast_checker.py",
            "src/python/clean_code_tools_pylint/comments.py",
            "src/python/clean_code_tools_pylint/helpers.py",
        }
        missing_sdist_files = sorted(required_sdist_files - sdist_package_files)
        if missing_sdist_files:
            raise SystemExit(f"Python sdist missing files: {', '.join(missing_sdist_files)}")
        assert_no_forbidden_files(
            artifact_name="Python sdist",
            package_files=sdist_package_files,
            forbidden_prefixes=(
                ".github/",
                "data/",
                "docs/",
                "evals/",
                "ops/",
                "sample-apps/",
                "scripts/",
                "skills/",
                "src/js/",
                "src/python/mcp_server/",
                "tests/",
            ),
            forbidden_files={"uv.lock", "package.json", "bun.lock"},
        )

        venv = tmp / ".venv"
        run([sys.executable, "-m", "venv", str(venv)])
        run([str(venv_executable(venv, "python")), "-m", "pip", "install", "--quiet", str(wheels[-1])])

        fixture = tmp / "fixture"
        fixture.mkdir()
        (fixture / "pyproject.toml").write_text(installed_python_config(venv))
        (fixture / "smelly.py").write_text(
            """
# TODO clean this up
# old_result = calculate_total(order)

def calculate_total(order, include_tax, dry_run, retry, verbose, mode):
    if order.status == "pending":
        order["status"] = "retry"
        calculate_total(order, True, False, False, False, "mode")
        return 5
    return 0
""".lstrip(),
        )

        ruff = run([str(venv_executable(venv, "ruff")), "check", "smelly.py"], cwd=fixture, check=False)
        pylint = run(
            [
                str(venv_executable(venv, "pylint")),
                "--rcfile=pyproject.toml",
                "smelly.py",
            ],
            cwd=fixture,
            check=False,
        )
        if ruff.returncode == 0 or pylint.returncode == 0:
            print(ruff.stdout)
            print(pylint.stdout)
            raise SystemExit("Expected installed package lint commands to report findings")
        for code in ["TD002", "TD003", "ERA001"]:
            if code not in ruff.stdout:
                print(ruff.stdout)
                raise SystemExit(f"Expected installed Ruff output to include {code}")
        for code in ["C9001", "C9002", "C9003", "C9004", "C9007"]:
            if code not in pylint.stdout:
                print(pylint.stdout)
                raise SystemExit(f"Expected installed Pylint output to include {code}")

def main() -> None:
    check_version_parity()
    check_npm_package()
    check_python_package()
    print("package_checks=ok")


if __name__ == "__main__":
    main()
