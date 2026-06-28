#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
PYTHON_TEMPLATE = SKILL_ROOT / "templates" / "python.clean-code.pyproject.toml"
MCP_RUNTIME_FILES = (
    SKILL_ROOT / ".dockerignore",
    SKILL_ROOT / "Dockerfile",
    SKILL_ROOT / "compose.yaml",
    SKILL_ROOT / "runtime",
)
MCP_RUNTIME_TARGET = ".clean-code-mcp"

JS_DEV_PACKAGES = [
    "clean-code-tools",
    "eslint",
    "@eslint/js",
    "typescript-eslint",
    "eslint-plugin-sonarjs",
    "eslint-plugin-unicorn",
]
PYTHON_DEV_PACKAGES = ["clean-code-tools-python"]
ESLINT_CONFIG_NAMES = [
    "eslint.config.mjs",
    "eslint.config.js",
    "eslint.config.cjs",
    "eslint.config.ts",
]


@dataclass
class Change:
    label: str
    detail: str


@dataclass
class Plan:
    repo: Path
    languages: list[str] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    commands: list[list[str]] = field(default_factory=list)

    @property
    def can_apply(self) -> bool:
        return not self.blockers and bool(self.changes or self.commands)


def run(command: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and completed.returncode != 0:
        raise SystemExit(completed.stdout)
    return completed


def has_files(repo: Path, patterns: tuple[str, ...]) -> bool:
    return any(next(repo.glob(pattern), None) is not None for pattern in patterns)


def is_git_dirty(repo: Path) -> bool:
    if not (repo / ".git").exists():
        return False
    return bool(run(["git", "status", "--porcelain"], cwd=repo).stdout.strip())


def detect_js_package_manager(repo: Path) -> str | None:
    if (repo / "bun.lock").exists() or (repo / "bun.lockb").exists():
        return "bun"
    if (repo / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo / "yarn.lock").exists():
        return "yarn"
    if (repo / "package-lock.json").exists():
        return "npm"
    if (repo / "package.json").exists():
        return "npm"
    return None


def js_install_command(package_manager: str) -> list[str]:
    if package_manager == "bun":
        return ["bun", "add", "-d", *JS_DEV_PACKAGES]
    if package_manager == "pnpm":
        return ["pnpm", "add", "-D", *JS_DEV_PACKAGES]
    if package_manager == "yarn":
        return ["yarn", "add", "-D", *JS_DEV_PACKAGES]
    return ["npm", "install", "--save-dev", *JS_DEV_PACKAGES]


def detect_python_install_command(repo: Path) -> list[str] | None:
    if shutil.which("uv") and (
        (repo / "uv.lock").exists()
        or (repo / "pyproject.toml").exists()
        or has_files(repo, ("*.py", "src/**/*.py", "tests/**/*.py"))
    ):
        return ["uv", "add", "--dev", *PYTHON_DEV_PACKAGES]
    if (repo / "poetry.lock").exists():
        return ["poetry", "add", "--group", "dev", *PYTHON_DEV_PACKAGES]
    if (repo / "requirements-dev.txt").exists():
        return [sys.executable, "-m", "pip", "install", *PYTHON_DEV_PACKAGES]
    if (repo / "pyproject.toml").exists():
        return [sys.executable, "-m", "pip", "install", *PYTHON_DEV_PACKAGES]
    return None


def package_json_scripts(repo: Path) -> dict[str, object]:
    package_json = repo / "package.json"
    if not package_json.exists():
        return {}
    try:
        payload = json.loads(package_json.read_text())
    except json.JSONDecodeError:
        return {}
    scripts = payload.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def eslint_config(repo: Path) -> Path | None:
    for name in ESLINT_CONFIG_NAMES:
        path = repo / name
        if path.exists():
            return path
    return None


def plan_js(repo: Path, plan: Plan) -> None:
    package_manager = detect_js_package_manager(repo)
    if package_manager is None:
        return
    plan.languages.append("javascript/typescript")
    if shutil.which(package_manager) is None:
        plan.blockers.append(f"Detected {package_manager}, but `{package_manager}` is not installed.")
    plan.commands.append(js_install_command(package_manager))

    scripts = package_json_scripts(repo)
    if not scripts:
        plan.warnings.append("No package.json scripts found; add a lint script after install if desired.")

    config = eslint_config(repo)
    if config is None:
        plan.changes.append(
            Change(
                "create eslint.config.mjs",
                "Create a flat ESLint config that exports clean-code-tools recommended rules.",
            )
        )
        return

    config_text = config.read_text()
    if "clean-code-tools/configs/eslint.clean-code.recommended.mjs" in config_text:
        plan.changes.append(Change("eslint already configured", f"{config.name} already imports clean-code-tools."))
        return
    if config.suffix == ".cjs":
        plan.blockers.append(
            f"{config.name} is CommonJS; convert to flat ESM config or import the preset manually."
        )
        return
    if "export default [" in config_text:
        plan.changes.append(
            Change(
                f"modify {config.name}",
                "Import the clean-code preset and spread it at the start of the exported flat config array.",
            )
        )
        return
    plan.blockers.append(
        f"{config.name} exists but is not a simple `export default [...]` flat config. "
        "Integrate manually with `import cleanCode from "
        '"clean-code-tools/configs/eslint.clean-code.recommended.mjs";` and `...cleanCode`.'
    )


def pyproject_has_clean_code(text: str) -> bool:
    return "clean_code_tools_pylint" in text and "clean-code-todo-format" in text


def pyproject_has_lint_sections(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "[tool.ruff]",
            "[tool.ruff.lint]",
            "[tool.pylint",
        )
    )


def plan_python(repo: Path, plan: Plan) -> None:
    if not ((repo / "pyproject.toml").exists() or has_files(repo, ("*.py", "src/**/*.py", "tests/**/*.py"))):
        return
    plan.languages.append("python")
    command = detect_python_install_command(repo)
    if command is None:
        plan.blockers.append("Python detected, but no supported installer/config was found.")
    else:
        if shutil.which(command[0]) is None and command[0] != sys.executable:
            plan.blockers.append(f"Detected Python installer `{command[0]}`, but it is not installed.")
        plan.commands.append(command)

    pyproject = repo / "pyproject.toml"
    if not pyproject.exists():
        plan.changes.append(
            Change(
                "create pyproject.toml",
                "Create pyproject.toml with clean-code Ruff and Pylint sections.",
            )
        )
        return

    text = pyproject.read_text()
    if pyproject_has_clean_code(text):
        plan.changes.append(Change("python lint already configured", "pyproject.toml already loads clean-code rules."))
        return
    if not pyproject_has_lint_sections(text):
        plan.changes.append(
            Change(
                "append pyproject.toml lint sections",
                "Append clean-code Ruff and Pylint sections to the existing pyproject.toml.",
            )
        )
        return
    plan.blockers.append(
        "pyproject.toml already has Ruff or Pylint sections. Merge the clean-code config manually "
        "to avoid overwriting local lint policy."
    )


def build_plan(repo: Path, *, allow_dirty: bool, require_languages: bool = True) -> Plan:
    plan = Plan(repo=repo)
    if is_git_dirty(repo) and not allow_dirty:
        plan.blockers.append("Git worktree is dirty. Commit/stash first or rerun with --allow-dirty.")
    plan_js(repo, plan)
    plan_python(repo, plan)
    if require_languages and not plan.languages:
        plan.blockers.append("No JavaScript/TypeScript or Python project files were detected.")
    return plan


def plan_mcp_runtime(repo: Path, plan: Plan, *, start: bool) -> None:
    if shutil.which("docker") is None:
        plan.blockers.append("Docker is required for the bundled MCP runtime but was not found.")
    target = repo / MCP_RUNTIME_TARGET
    if target.exists():
        plan.blockers.append(f"{MCP_RUNTIME_TARGET} already exists. Remove it or merge the runtime manually.")
        return
    plan.changes.append(
        Change(
            f"create {MCP_RUNTIME_TARGET}/",
            "Copy the bundled Dockerfile, Compose file, MCP server runtime, and clean-code corpus.",
        )
    )
    if start:
        plan.commands.append(
            [
                "docker",
                "compose",
                "-f",
                f"{MCP_RUNTIME_TARGET}/compose.yaml",
                "up",
                "--build",
                "-d",
            ]
        )


def add_clean_code_to_eslint_array(text: str) -> str:
    import_line = 'import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";\n'
    if import_line not in text:
        text = import_line + text
    return text.replace("export default [", "export default [\n  ...cleanCode,", 1)


def apply_js(repo: Path) -> None:
    config = eslint_config(repo)
    if config is None:
        (repo / "eslint.config.mjs").write_text(
            'import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";\n\n'
            "export default cleanCode;\n"
        )
        return
    text = config.read_text()
    if "clean-code-tools/configs/eslint.clean-code.recommended.mjs" in text:
        return
    config.write_text(add_clean_code_to_eslint_array(text))


def apply_python(repo: Path) -> None:
    pyproject = repo / "pyproject.toml"
    template = PYTHON_TEMPLATE.read_text()
    if not pyproject.exists():
        pyproject.write_text(template)
        return
    text = pyproject.read_text()
    if pyproject_has_clean_code(text):
        return
    pyproject.write_text(text.rstrip() + "\n\n" + template)


def apply_plan(plan: Plan, *, skip_install: bool) -> None:
    for language in plan.languages:
        if language == "javascript/typescript":
            apply_js(plan.repo)
        if language == "python":
            apply_python(plan.repo)
    if skip_install:
        return
    for command in plan.commands:
        print(f"running: {' '.join(command)}")
        run(command, cwd=plan.repo)


def apply_mcp_runtime(repo: Path) -> None:
    target = repo / MCP_RUNTIME_TARGET
    target.mkdir()
    for source in MCP_RUNTIME_FILES:
        destination = target / source.name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def print_plan(plan: Plan) -> None:
    print(f"repo: {plan.repo}")
    print(f"languages: {', '.join(plan.languages) if plan.languages else 'none'}")
    if plan.changes:
        print("\nplanned changes:")
        for change in plan.changes:
            print(f"- {change.label}: {change.detail}")
    if plan.commands:
        print("\ninstall commands:")
        for command in plan.commands:
            print(f"- {' '.join(command)}")
    if plan.warnings:
        print("\nwarnings:")
        for warning in plan.warnings:
            print(f"- {warning}")
    if plan.blockers:
        print("\nblockers:")
        for blocker in plan.blockers:
            print(f"- {blocker}")
        print("\nNo changes were applied.")
    else:
        print("\nstatus: safe to apply")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install clean-code lint packages and config.")
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    parser.add_argument("--apply", action="store_true", help="Apply safe changes and install packages.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow applying with a dirty git worktree.")
    parser.add_argument("--skip-install", action="store_true", help="Modify files without running package installers.")
    parser.add_argument(
        "--mcp-runtime",
        action="store_true",
        help=f"Also copy the Dockerized MCP runtime into {MCP_RUNTIME_TARGET}/.",
    )
    parser.add_argument(
        "--start-mcp-runtime",
        action="store_true",
        help="After applying, run the Dockerized Weaviate + MCP stack.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        raise SystemExit(f"Repo does not exist: {repo}")
    wants_mcp_runtime = args.mcp_runtime or args.start_mcp_runtime
    plan = build_plan(repo, allow_dirty=args.allow_dirty, require_languages=not wants_mcp_runtime)
    if wants_mcp_runtime:
        plan_mcp_runtime(repo, plan, start=args.start_mcp_runtime)
    print_plan(plan)
    if args.apply:
        if not plan.can_apply:
            raise SystemExit(1)
        if wants_mcp_runtime:
            apply_mcp_runtime(repo)
        apply_plan(plan, skip_install=args.skip_install)
        print("\napplied: clean-code lint configuration updated")


if __name__ == "__main__":
    main()
