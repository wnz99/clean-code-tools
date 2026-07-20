#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HOOK_DIR = Path(__file__).resolve().parent
CATALOG_NAME = "clean_code_review_triggers.json"
CATALOG_CANDIDATES = (
    HOOK_DIR / CATALOG_NAME,
    HOOK_DIR.parent / "catalog" / CATALOG_NAME,
)
JAVASCRIPT_EXTENSIONS = frozenset({".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"})
PYTHON_EXTENSIONS = frozenset({".py"})


@dataclass(frozen=True)
class Finding:
    tool: str
    rule: str
    file: str
    line: int | None
    message: str
    query: str


def load_catalog() -> dict[str, dict[str, dict[str, Any]]]:
    for path in CATALOG_CANDIDATES:
        if path.exists():
            payload = load_json(path.read_text())
            if isinstance(payload, dict):
                return {
                    section: rules
                    for section, rules in payload.items()
                    if isinstance(rules, dict) and section != "schema"
                }
    return {}


def query_for(section: str, rule: str) -> str | None:
    rule_payload = CATALOG.get(section, {}).get(rule)
    if not isinstance(rule_payload, dict):
        return None
    query = rule_payload.get("mcp_query")
    return query if isinstance(query, str) else None


def repo_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip())
    return Path.cwd()


def run(command: list[str], *, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def load_json(raw: str) -> Any | None:
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


CATALOG = load_catalog()


def package_manager(repo: Path) -> str | None:
    if (repo / "bun.lock").exists() or (repo / "bun.lockb").exists():
        return "bun"
    if (repo / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo / "yarn.lock").exists():
        return "yarn"
    if (repo / "package-lock.json").exists() or (repo / "package.json").exists():
        return "npm"
    return None


def changed_files(repo: Path, base_ref: str) -> list[str]:
    completed = run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", base_ref, "--"],
        cwd=repo,
        timeout=30,
    )
    if completed is None or completed.returncode != 0:
        return []
    return [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip() and (repo / line.strip()).exists()
    ]


def files_with_extensions(files: list[str] | None, extensions: frozenset[str]) -> list[str] | None:
    if files is None:
        return None
    return [path for path in files if Path(path).suffix in extensions]


def eslint_command(manager: str, files: list[str] | None = None) -> list[str]:
    targets = files or ["."]
    if manager == "bun":
        return ["bunx", "eslint", *targets, "--format", "json"]
    if manager == "pnpm":
        return ["pnpm", "exec", "eslint", *targets, "--format", "json"]
    if manager == "yarn":
        return ["yarn", "eslint", *targets, "--format", "json"]
    return ["npx", "eslint", *targets, "--format", "json"]


def eslint_findings(repo: Path, *, timeout: int, files: list[str] | None = None) -> list[Finding]:
    if not (repo / "package.json").exists():
        return []
    manager = package_manager(repo)
    if manager is None:
        return []
    target_files = files_with_extensions(files, JAVASCRIPT_EXTENSIONS)
    if target_files == []:
        return []
    completed = run(eslint_command(manager, target_files), cwd=repo, timeout=timeout)
    if completed is None:
        return []
    payload = load_json(completed.stdout)
    if not isinstance(payload, list):
        return []
    findings: list[Finding] = []
    for result in payload:
        if not isinstance(result, dict):
            continue
        file_path = str(result.get("filePath", ""))
        for message in result.get("messages", []):
            if not isinstance(message, dict):
                continue
            rule = message.get("ruleId")
            if not isinstance(rule, str):
                continue
            query = query_for("eslint", rule)
            if query is None:
                continue
            findings.append(
                Finding(
                    tool="eslint",
                    rule=rule,
                    file=relative(repo, file_path),
                    line=optional_int(message.get("line")),
                    message=str(message.get("message", "")),
                    query=query,
                )
            )
    return findings


def python_command(repo: Path, tool: str, files: list[str] | None = None) -> list[str]:
    targets = files or ["."]
    if shutil.which("uv") and ((repo / "uv.lock").exists() or (repo / "pyproject.toml").exists()):
        if tool == "ruff":
            return ["uv", "run", "ruff", "check", *targets, "--output-format=json"]
        return ["uv", "run", "pylint", *targets, "--output-format=json"]
    if tool == "ruff":
        return [sys.executable, "-m", "ruff", "check", *targets, "--output-format=json"]
    return [sys.executable, "-m", "pylint", *targets, "--output-format=json"]


def ruff_findings(repo: Path, *, timeout: int, files: list[str] | None = None) -> list[Finding]:
    if not has_python(repo):
        return []
    target_files = files_with_extensions(files, PYTHON_EXTENSIONS)
    if target_files == []:
        return []
    completed = run(python_command(repo, "ruff", target_files), cwd=repo, timeout=timeout)
    if completed is None:
        return []
    payload = load_json(completed.stdout)
    if not isinstance(payload, list):
        return []
    findings: list[Finding] = []
    for message in payload:
        if not isinstance(message, dict):
            continue
        rule = message.get("code")
        if not isinstance(rule, str):
            continue
        query = query_for("ruff", rule)
        if query is None:
            continue
        location = message.get("location", {})
        if not isinstance(location, dict):
            location = {}
        findings.append(
            Finding(
                tool="ruff",
                rule=rule,
                file=relative(repo, str(message.get("filename", ""))),
                line=optional_int(location.get("row")),
                message=str(message.get("message", "")),
                query=query,
            )
        )
    return findings


def pylint_findings(repo: Path, *, timeout: int, files: list[str] | None = None) -> list[Finding]:
    if not has_python(repo):
        return []
    target_files = files_with_extensions(files, PYTHON_EXTENSIONS)
    if target_files == []:
        return []
    completed = run(python_command(repo, "pylint", target_files), cwd=repo, timeout=timeout)
    if completed is None:
        return []
    payload = load_json(completed.stdout)
    if not isinstance(payload, list):
        return []
    findings: list[Finding] = []
    for message in payload:
        if not isinstance(message, dict):
            continue
        rule = message.get("symbol")
        if not isinstance(rule, str):
            continue
        query = query_for("pylint", rule)
        if query is None:
            continue
        findings.append(
            Finding(
                tool="pylint",
                rule=rule,
                file=relative(repo, str(message.get("path", ""))),
                line=optional_int(message.get("line")),
                message=str(message.get("message", "")),
                query=query,
            )
        )
    return findings


def has_python(repo: Path) -> bool:
    return (repo / "pyproject.toml").exists() or any(repo.glob("**/*.py"))


def optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def relative(repo: Path, path: str) -> str:
    if not path:
        return path
    raw = Path(path)
    try:
        return raw.resolve().relative_to(repo).as_posix()
    except ValueError:
        return path


def print_feedback(findings: list[Finding], *, hook_name: str, limit: int, blocking: bool) -> None:
    if not findings:
        print(f"clean-code agent hook ({hook_name}): no semantic review candidates found.")
        return
    print(f"clean-code agent hook ({hook_name}): {len(findings)} semantic review candidate(s).")
    print("These are deterministic tripwires, not final findings.")
    print(
        "Agent instruction: use skill `clean-code-tools` if available; "
        "read each file first, then query MCP narrowly."
    )
    for index, finding in enumerate(findings[:limit], start=1):
        location = f"{finding.file}:{finding.line}" if finding.line else finding.file
        print(f"{index}. {location} [{finding.tool}:{finding.rule}] {finding.message}")
        print(f"   suggested MCP query: {finding.query}")
    remaining = len(findings) - limit
    if remaining > 0:
        print(f"... {remaining} more candidate(s) omitted; run lint directly for full output.")
    if blocking:
        print("Blocking mode is enabled. Review or bypass intentionally with CLEAN_CODE_AGENT_HOOK_MODE=advisory.")


def include_pylint() -> bool:
    return os.environ.get("CLEAN_CODE_AGENT_HOOK_PYLINT", "0").lower() in {"1", "true", "yes"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit clean-code feedback for local Git hooks.")
    parser.add_argument("--hook", default="git-hook")
    parser.add_argument("--mode", choices=("advisory", "blocking"), default=os.environ.get("CLEAN_CODE_AGENT_HOOK_MODE", "advisory"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--changed-since", help="Only inspect files changed from this Git ref.")
    args = parser.parse_args()

    repo = repo_root()
    changed = changed_files(repo, args.changed_since) if args.changed_since else None
    findings = [
        *eslint_findings(repo, timeout=args.timeout, files=changed),
        *ruff_findings(repo, timeout=args.timeout, files=changed),
    ]
    if include_pylint():
        findings.extend(pylint_findings(repo, timeout=args.timeout, files=changed))
    print_feedback(findings, hook_name=args.hook, limit=args.limit, blocking=args.mode == "blocking")
    if findings and args.mode == "blocking":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
