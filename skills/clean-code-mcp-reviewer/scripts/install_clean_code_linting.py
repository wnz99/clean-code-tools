#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
PYTHON_TEMPLATE = SKILL_ROOT / "templates" / "python.clean-code.pyproject.toml"
KNIP_CONFIG_NAME = "knip.json"
FALLOW_CONFIG_NAME = ".fallowrc.json"
MCP_RUNTIME_FILES = (
    SKILL_ROOT / ".dockerignore",
    SKILL_ROOT / "Dockerfile",
    SKILL_ROOT / "compose.yaml",
    SKILL_ROOT / "runtime",
)
MCP_RUNTIME_TARGET = ".clean-code-mcp"
HOOK_SOURCE = SKILL_ROOT / "hooks" / "clean_code_agent_feedback.py"
HOOK_CATALOG_SOURCE = SKILL_ROOT / "catalog" / "clean_code_review_triggers.json"
HOOK_SCRIPT_NAME = "clean_code_agent_feedback.py"
HOOK_CATALOG_NAME = "clean_code_review_triggers.json"
HOOK_MARKER = "# clean-code-mcp-reviewer hook"
HOOK_CHOICES = ("ask", "none", "pre-commit", "pre-push", "both")
RECOMMENDED_HOOK_CHOICE = "pre-push"

JS_DEV_PACKAGES = [
    "clean-code-tools",
    "eslint",
    "@eslint/js",
    "typescript-eslint",
    "eslint-plugin-sonarjs",
    "eslint-plugin-unicorn",
    "knip",
    "fallow",
]
PYTHON_DEV_PACKAGES = ["clean-code-tools-python", "deptry"]
ESLINT_CONFIG_NAMES = [
    "eslint.config.mjs",
    "eslint.config.js",
    "eslint.config.cjs",
    "eslint.config.ts",
]

PACKAGE_CHECK_SCRIPTS = {
    "check:knip": "knip --no-progress --no-config-hints",
    "check:fallow": "fallow dead-code --summary --quiet && fallow dupes --summary --quiet",
    "inspect:fallow-health": "fallow health --format compact || true",
}

KNIP_CONFIG = {
    "$schema": "https://unpkg.com/knip@6/schema.json",
    "entry": ["tests/**/*.test.{js,mjs,cjs,ts,tsx}"],
    "project": [
        "src/**/*.{js,mjs,cjs,ts,tsx}",
        "tests/**/*.{js,mjs,cjs,ts,tsx}",
        "configs/**/*.{js,mjs,cjs,ts}",
    ],
    "ignoreBinaries": ["uv"],
}

FALLOW_CONFIG = {
    "$schema": "https://raw.githubusercontent.com/fallow-rs/fallow/main/schema.json",
    "ignorePatterns": [
        ".codex/**",
        ".venv/**",
        "build/**",
        "dist/**",
        "node_modules/**",
    ],
    "rules": {
        "unused-dev-dependencies": "warn",
    },
}

DEPTRY_CONFIG = """[tool.deptry]
known_first_party = []

[tool.deptry.per_rule_ignores]
DEP002 = [
  "ruff",
]
"""


@dataclass
class Change:
    label: str
    detail: str


@dataclass
class PlannedCommand:
    label: str
    command: list[str]
    category: str
    cwd: Path | None = None


@dataclass
class ApplyOptions:
    wants_mcp_runtime: bool
    hook_choice: str
    hook_mode: str
    assume_yes: bool
    skip_install: bool
    create_backup: bool


@dataclass
class Plan:
    repo: Path
    git_root: Path
    languages: list[str] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    commands: list[PlannedCommand] = field(default_factory=list)
    verification: list[PlannedCommand] = field(default_factory=list)

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


def git_root_for(path: Path) -> Path:
    completed = run(["git", "rev-parse", "--show-toplevel"], cwd=path, check=False)
    if completed.returncode != 0:
        return path
    return Path(completed.stdout.strip()).resolve()


def is_git_dirty(repo: Path) -> bool:
    git_root = git_root_for(repo)
    if not (git_root / ".git").exists():
        return False
    return bool(run(["git", "status", "--porcelain"], cwd=git_root).stdout.strip())


def backup_root(repo: Path) -> Path:
    return git_root_for(repo) / ".git" / "clean-code-installer-backups"


def create_rollback_point(repo: Path) -> list[str]:
    git_root = git_root_for(repo)
    if not (git_root / ".git").exists():
        return ["No Git repository found; no rollback point was created."]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"backup/clean-code-install-{timestamp}"
    run(["git", "branch", branch, "HEAD"], cwd=git_root)

    notes = [
        f"Created backup branch `{branch}` at the pre-install HEAD.",
        f"Rollback committed installer changes with: git reset --hard {branch}",
    ]
    status = run(["git", "status", "--porcelain"], cwd=git_root).stdout
    if not status.strip():
        return notes

    patch_dir = backup_root(repo) / timestamp
    patch_dir.mkdir(parents=True, exist_ok=False)
    (patch_dir / "status.txt").write_text(status)
    unstaged = run(["git", "diff"], cwd=git_root).stdout
    staged = run(["git", "diff", "--cached"], cwd=git_root).stdout
    if unstaged:
        (patch_dir / "unstaged.patch").write_text(unstaged)
    if staged:
        (patch_dir / "staged.patch").write_text(staged)
    notes.append(f"Saved dirty-worktree patch backup under `{patch_dir}`.")
    notes.append("Reapply saved user changes with `git apply <patch>` after rollback if needed.")
    return notes


def resolve_target_repo(repo: Path, target: str | None) -> Path:
    if target is None:
        return repo
    target_path = (repo / target).resolve()
    try:
        target_path.relative_to(repo)
    except ValueError as exc:
        raise SystemExit("--target must stay inside --repo") from exc
    if not target_path.exists():
        raise SystemExit(f"Target path does not exist: {target_path}")
    return target_path


def package_manager_root(repo: Path, names: tuple[str, ...]) -> Path | None:
    git_root = git_root_for(repo)
    current = repo
    while True:
        if any((current / name).exists() for name in names):
            return current
        if current in (git_root, current.parent):
            return None
        current = current.parent


def has_js_workspaces(repo: Path) -> bool:
    if (repo / "pnpm-workspace.yaml").exists():
        return True
    package_json_path = repo / "package.json"
    if not package_json_path.exists():
        return False
    payload = package_json(repo)
    return "workspaces" in payload


def has_nested_project_files(repo: Path) -> bool:
    project_files = (
        "package.json",
        "pyproject.toml",
        "eslint.config.js",
        "eslint.config.mjs",
        "ruff.toml",
    )
    for name in project_files:
        matches = [path for path in repo.glob(f"**/{name}") if "node_modules" not in path.parts]
        if len(matches) > 1:
            return True
    return False


def root_monorepo_reason(repo: Path) -> str | None:
    if repo != git_root_for(repo):
        return None
    if has_js_workspaces(repo):
        return "root JavaScript workspace"
    if has_nested_project_files(repo):
        return "multiple nested project/config files"
    return None


def js_package_manager_root(repo: Path) -> Path | None:
    lock_root = package_manager_root(
        repo,
        ("bun.lock", "bun.lockb", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"),
    )
    if lock_root is not None:
        return lock_root
    return package_manager_root(repo, ("package.json",))


def detect_js_package_manager(repo: Path) -> str | None:
    manager_root = js_package_manager_root(repo)
    if manager_root is None:
        return None
    manager_markers = (
        ("bun", ("bun.lock", "bun.lockb")),
        ("pnpm", ("pnpm-lock.yaml",)),
        ("yarn", ("yarn.lock",)),
        ("npm", ("package-lock.json", "package.json")),
    )
    for manager, markers in manager_markers:
        if any((manager_root / marker).exists() for marker in markers):
            return manager
    return None


def js_install_command(package_manager: str, *, workspace_root: bool) -> list[str]:
    if package_manager == "bun":
        return ["bun", "add", "-d", *JS_DEV_PACKAGES]
    if package_manager == "pnpm":
        command = ["pnpm", "add", "-D"]
        if workspace_root:
            command.append("-w")
        return [*command, *JS_DEV_PACKAGES]
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


def package_json(repo: Path) -> dict[str, object]:
    package_json_path = repo / "package.json"
    if not package_json_path.exists():
        return {}
    try:
        payload = json.loads(package_json_path.read_text())
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


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
    manager_root = js_package_manager_root(repo)
    manager_root = manager_root or repo
    workspace_root = repo == manager_root and has_js_workspaces(repo)
    plan.languages.append("javascript/typescript")
    if manager_root != repo:
        plan.warnings.append(
            f"Using JavaScript package manager from ancestor `{manager_root}` for target `{repo}`."
        )
    if workspace_root:
        plan.warnings.append(
            "JavaScript workspace root detected. Use --target <package-path> when the clean-code "
            "config belongs to a nested package instead of the root workspace."
        )
    if shutil.which(package_manager) is None:
        plan.blockers.append(f"Detected {package_manager}, but `{package_manager}` is not installed.")
    plan.commands.append(
        PlannedCommand(
            "install JavaScript/TypeScript clean-code dev packages",
            js_install_command(package_manager, workspace_root=workspace_root),
            "dependency-install",
            manager_root,
        )
    )

    scripts = package_json_scripts(repo)
    if not scripts:
        plan.warnings.append("No package.json scripts found; add a lint script after install if desired.")
    missing_scripts = [name for name in PACKAGE_CHECK_SCRIPTS if name not in scripts]
    if missing_scripts:
        plan.changes.append(
            Change(
                "update package.json clean-code check scripts",
                "Add Knip/Fallow scripts for dependency, dead-code, duplication, and advisory health checks.",
            )
        )

    if not (repo / KNIP_CONFIG_NAME).exists():
        plan.changes.append(
            Change(
                f"create {KNIP_CONFIG_NAME}",
                "Configure Knip to check JS/TS unused files, exports, binaries, and dependencies.",
            )
        )
    if not (repo / FALLOW_CONFIG_NAME).exists():
        plan.changes.append(
            Change(
                f"create {FALLOW_CONFIG_NAME}",
                "Configure Fallow dead-code and duplication checks with common generated/vendor ignores.",
            )
        )

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


def pyproject_has_deptry(text: str) -> bool:
    return "[tool.deptry]" in text


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
        plan.commands.append(
            PlannedCommand(
                "install Python clean-code dev package",
                command,
                "dependency-install",
                repo,
            )
        )

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
    if not pyproject_has_deptry(text):
        plan.changes.append(
            Change(
                "append pyproject.toml deptry section",
                "Configure deptry for Python dependency hygiene checks.",
            )
        )
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


def add_verification_plan(plan: Plan) -> None:
    scripts = package_json_scripts(plan.repo)
    package_manager = detect_js_package_manager(plan.repo)
    run_prefix = {
        "bun": ["bun", "run"],
        "pnpm": ["pnpm", "run"],
        "yarn": ["yarn"],
        "npm": ["npm", "run"],
    }.get(package_manager or "npm", ["npm", "run"])
    for name in ("lint", "test", "check", "check:knip", "check:fallow"):
        if name in scripts:
            plan.verification.append(
                PlannedCommand(
                    f"verify package script `{name}`",
                    [*run_prefix, name],
                    "verification",
                    plan.repo,
                )
            )
            break
    if (plan.repo / "pyproject.toml").exists():
        plan.verification.append(
            PlannedCommand("verify Ruff config", ["ruff", "check", "."], "verification", plan.repo)
        )
    if not plan.verification:
        plan.warnings.append("No obvious lint/test verification command was detected; run the repo's CI checks manually.")


def build_plan(
    repo: Path,
    *,
    allow_dirty: bool,
    require_languages: bool = True,
    allow_root_monorepo: bool = False,
) -> Plan:
    plan = Plan(repo=repo, git_root=git_root_for(repo))
    if is_git_dirty(repo) and not allow_dirty:
        plan.blockers.append("Git worktree is dirty. Commit/stash first or rerun with --allow-dirty.")
    monorepo_reason = root_monorepo_reason(repo)
    if monorepo_reason and not allow_root_monorepo:
        plan.blockers.append(
            f"Root monorepo detected ({monorepo_reason}). Do not apply root-level clean-code "
            "configuration automatically. Rerun with --target <package-or-service> for a package-local "
            "plan, or pass --allow-root-monorepo only after the user explicitly approves root-level changes."
        )
    plan_js(repo, plan)
    plan_python(repo, plan)
    if require_languages and not plan.languages:
        plan.blockers.append("No JavaScript/TypeScript or Python project files were detected.")
    add_verification_plan(plan)
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
            PlannedCommand(
                "start Dockerized clean-code MCP runtime",
                [
                    "docker",
                    "compose",
                    "-f",
                    f"{MCP_RUNTIME_TARGET}/compose.yaml",
                    "up",
                    "--build",
                    "-d",
                ],
                "docker-runtime",
            )
        )


def git_hooks_dir(repo: Path) -> Path:
    completed = run(["git", "rev-parse", "--git-path", "hooks"], cwd=repo, check=False)
    hooks_path = completed.stdout.strip()
    if completed.returncode == 0 and hooks_path:
        return (repo / hooks_path).resolve()
    return repo / ".git" / "hooks"


def selected_hooks(choice: str) -> tuple[str, ...]:
    if choice == "both":
        return ("pre-commit", "pre-push")
    if choice in ("pre-commit", "pre-push"):
        return (choice,)
    return ()


def prompt_hook_choice() -> str:
    print("\nInstall clean-code agent feedback Git hooks?")
    print("  1. no hooks")
    print("  2. pre-push only (recommended)")
    print("  3. pre-commit only")
    print("  4. both pre-commit and pre-push")
    answer = input("Choose [1-4, default 2]: ").strip()
    return {
        "": RECOMMENDED_HOOK_CHOICE,
        "2": "pre-push",
        "3": "pre-commit",
        "4": "both",
    }.get(answer, "none")


def resolve_hook_choice(choice: str) -> str:
    if choice == "ask" and sys.stdin.isatty():
        return prompt_hook_choice()
    if choice == "ask":
        return "none"
    return choice


def plan_git_hooks(repo: Path, plan: Plan, *, choice: str, mode: str) -> None:
    hooks = selected_hooks(choice)
    if not hooks:
        plan.warnings.append(
            "Git hooks were not selected. Use --git-hooks pre-push to install the recommended agent feedback hook."
        )
        return
    git_root = git_root_for(repo)
    if not (git_root / ".git").exists():
        plan.blockers.append("Git hooks requested, but this is not a Git working tree.")
        return
    missing_hook_files = [
        str(path)
        for path in (HOOK_SOURCE, HOOK_CATALOG_SOURCE)
        if not path.exists()
    ]
    if missing_hook_files:
        plan.blockers.append(f"Hook support is missing from the skill: {', '.join(missing_hook_files)}")
        return
    hooks_dir = git_hooks_dir(git_root)
    for hook_name in hooks:
        hook_path = hooks_dir / hook_name
        if hook_path.exists() and HOOK_MARKER not in hook_path.read_text(errors="ignore"):
            plan.blockers.append(
                f"{hook_name} already exists and is not managed by clean-code-mcp-reviewer. "
                "Merge the hook manually or move the existing hook first."
            )
            continue
        plan.changes.append(
            Change(
                f"install {hook_name} hook",
                f"Run clean-code agent feedback in {mode} mode whenever Git invokes {hook_name}.",
            )
        )


def add_clean_code_to_eslint_array(text: str) -> str:
    import_line = 'import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";\n'
    if import_line not in text:
        text = import_line + text
    if "export default []" in text:
        return text.replace("export default []", "export default [\n  ...cleanCode,\n]", 1)
    return text.replace("export default [", "export default [\n  ...cleanCode,", 1)


def apply_js(repo: Path) -> None:
    config = eslint_config(repo)
    if config is None:
        (repo / "eslint.config.mjs").write_text(
            'import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";\n\n'
            "export default cleanCode;\n"
        )
        apply_js_quality_config(repo)
        return
    text = config.read_text()
    if "clean-code-tools/configs/eslint.clean-code.recommended.mjs" in text:
        apply_js_quality_config(repo)
        return
    config.write_text(add_clean_code_to_eslint_array(text))
    apply_js_quality_config(repo)


def apply_js_quality_config(repo: Path) -> None:
    knip_config = repo / KNIP_CONFIG_NAME
    if not knip_config.exists():
        knip_config.write_text(json.dumps(KNIP_CONFIG, indent=2) + "\n")

    fallow_config = repo / FALLOW_CONFIG_NAME
    if not fallow_config.exists():
        fallow_config.write_text(json.dumps(FALLOW_CONFIG, indent=2) + "\n")

    package_json_path = repo / "package.json"
    payload = package_json(repo)
    if not payload:
        return
    scripts = payload.get("scripts")
    if not isinstance(scripts, dict):
        scripts = {}
    changed = False
    for name, command in PACKAGE_CHECK_SCRIPTS.items():
        if name not in scripts:
            scripts[name] = command
            changed = True
    if not changed:
        return
    payload["scripts"] = scripts
    package_json_path.write_text(json.dumps(payload, indent=2) + "\n")


def apply_python(repo: Path) -> None:
    pyproject = repo / "pyproject.toml"
    template = PYTHON_TEMPLATE.read_text()
    if not pyproject.exists():
        pyproject.write_text(template)
        return
    text = pyproject.read_text()
    if pyproject_has_clean_code(text):
        pyproject.write_text(ensure_deptry_config(text))
        return
    pyproject.write_text(text.rstrip() + "\n\n" + template)


def ensure_deptry_config(text: str) -> str:
    if pyproject_has_deptry(text):
        return text
    return text.rstrip() + "\n\n" + DEPTRY_CONFIG


def confirm(action: str, *, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print(f"skipped: {action} requires interactive approval or --yes")
        return False
    answer = input(f"{action}? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def apply_lint_config(plan: Plan) -> None:
    for language in plan.languages:
        if language == "javascript/typescript":
            apply_js(plan.repo)
        if language == "python":
            apply_python(plan.repo)


def run_planned_commands(plan: Plan, *, category: str) -> None:
    for planned in plan.commands:
        if planned.category != category:
            continue
        print(f"running: {' '.join(planned.command)}")
        run(planned.command, cwd=planned.cwd or plan.repo)


def has_commands(plan: Plan, category: str) -> bool:
    return any(command.category == category for command in plan.commands)


def apply_mcp_runtime(repo: Path) -> None:
    target = repo / MCP_RUNTIME_TARGET
    target.mkdir()
    for source in MCP_RUNTIME_FILES:
        destination = target / source.name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def hook_wrapper(hook_name: str, *, mode: str) -> str:
    return f"""#!/bin/sh
{HOOK_MARKER}
HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ "${{CLEAN_CODE_AGENT_HOOK:-1}}" = "0" ]; then
  exit 0
fi
exec python3 "$HOOK_DIR/{HOOK_SCRIPT_NAME}" --hook {hook_name} --mode "${{CLEAN_CODE_AGENT_HOOK_MODE:-{mode}}}"
"""


def apply_git_hooks(repo: Path, *, choice: str, mode: str) -> None:
    hooks = selected_hooks(choice)
    if not hooks:
        return
    hooks_dir = git_hooks_dir(git_root_for(repo))
    hooks_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HOOK_SOURCE, hooks_dir / HOOK_SCRIPT_NAME)
    shutil.copy2(HOOK_CATALOG_SOURCE, hooks_dir / HOOK_CATALOG_NAME)
    (hooks_dir / HOOK_SCRIPT_NAME).chmod(0o755)
    for hook_name in hooks:
        hook_path = hooks_dir / hook_name
        hook_path.write_text(hook_wrapper(hook_name, mode=mode))
        hook_path.chmod(0o755)


def print_plan(plan: Plan) -> None:
    print(f"repo: {plan.repo}")
    if plan.git_root != plan.repo:
        print(f"git root: {plan.git_root}")
    print(f"languages: {', '.join(plan.languages) if plan.languages else 'none'}")
    if plan.changes:
        print("\nplanned changes:")
        for change in plan.changes:
            print(f"- {change.label}: {change.detail}")
    if plan.commands:
        print("\nplanned commands:")
        for planned in plan.commands:
            cwd = planned.cwd or plan.repo
            cwd_note = f" (cwd: {cwd})" if cwd != plan.repo else ""
            print(f"- {planned.label}: {' '.join(planned.command)}{cwd_note}")
    if plan.verification:
        print("\nrecommended verification after apply:")
        for planned in plan.verification:
            cwd = planned.cwd or plan.repo
            cwd_note = f" (cwd: {cwd})" if cwd != plan.repo else ""
            print(f"- {planned.label}: {' '.join(planned.command)}{cwd_note}")
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


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install clean-code lint packages and config.")
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    parser.add_argument(
        "--target",
        help="Nested package/app path inside --repo to configure in a monorepo.",
    )
    parser.add_argument("--apply", action="store_true", help="Apply safe changes and install packages.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Apply all planned host changes without interactive confirmation. Use only in automation.",
    )
    parser.add_argument("--allow-dirty", action="store_true", help="Allow applying with a dirty git worktree.")
    parser.add_argument(
        "--allow-root-monorepo",
        action="store_true",
        help="Allow root-level config changes in a detected monorepo after explicit user approval.",
    )
    parser.add_argument("--no-backup", action="store_true", help="Do not create a Git rollback point before --apply.")
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
    parser.add_argument(
        "--git-hooks",
        choices=HOOK_CHOICES,
        default="ask",
        help="Install local Git hooks for agent feedback. In interactive --apply mode, ask by default.",
    )
    parser.add_argument(
        "--git-hook-mode",
        choices=("advisory", "blocking"),
        default="advisory",
        help="Hook behavior when clean-code candidates are found.",
    )
    return parser


def apply_lint_config_if_approved(plan: Plan, *, assume_yes: bool) -> None:
    if not plan.languages:
        return
    if confirm("Modify lint configuration files", assume_yes=assume_yes):
        apply_lint_config(plan)
        return
    print("skipped: lint configuration files were not modified")


def apply_runtime_if_approved(repo: Path, *, wants_mcp_runtime: bool, assume_yes: bool) -> None:
    if not wants_mcp_runtime:
        return
    if confirm(f"Create {MCP_RUNTIME_TARGET}/ Docker MCP runtime files", assume_yes=assume_yes):
        apply_mcp_runtime(repo)
        return
    print(f"skipped: {MCP_RUNTIME_TARGET}/ was not created")


def apply_hooks_if_approved(repo: Path, *, hook_choice: str, mode: str, assume_yes: bool) -> None:
    if not selected_hooks(hook_choice):
        return
    if confirm("Install clean-code Git hook feedback", assume_yes=assume_yes):
        apply_git_hooks(repo, choice=hook_choice, mode=mode)
        return
    print("skipped: Git hooks were not installed")


def install_packages_if_approved(plan: Plan, *, skip_install: bool, assume_yes: bool) -> None:
    if skip_install:
        print("skipped: package installation disabled by --skip-install")
        return
    if not has_commands(plan, "dependency-install"):
        return
    if confirm("Install clean-code lint packages as development dependencies", assume_yes=assume_yes):
        run_planned_commands(plan, category="dependency-install")
        return
    print("skipped: lint packages were not installed")


def start_runtime_if_approved(plan: Plan, *, assume_yes: bool) -> None:
    if not has_commands(plan, "docker-runtime"):
        return
    if confirm("Build and start the Dockerized clean-code MCP runtime", assume_yes=assume_yes):
        run_planned_commands(plan, category="docker-runtime")
        return
    print("skipped: Dockerized clean-code MCP runtime was not started")


def apply_requested_setup(plan: Plan, options: ApplyOptions) -> None:
    if not plan.can_apply:
        raise SystemExit(1)
    if options.create_backup:
        print("\nrollback point:")
        for note in create_rollback_point(plan.repo):
            print(f"- {note}")
    apply_lint_config_if_approved(plan, assume_yes=options.assume_yes)
    apply_runtime_if_approved(
        plan.repo,
        wants_mcp_runtime=options.wants_mcp_runtime,
        assume_yes=options.assume_yes,
    )
    apply_hooks_if_approved(
        plan.repo,
        hook_choice=options.hook_choice,
        mode=options.hook_mode,
        assume_yes=options.assume_yes,
    )
    install_packages_if_approved(
        plan,
        skip_install=options.skip_install,
        assume_yes=options.assume_yes,
    )
    start_runtime_if_approved(plan, assume_yes=options.assume_yes)
    if plan.verification:
        print("\nrecommended verification:")
        for planned in plan.verification:
            cwd = planned.cwd or plan.repo
            cwd_note = f" (cwd: {cwd})" if cwd != plan.repo else ""
            print(f"- {' '.join(planned.command)}{cwd_note}")
    print("\nfinished: requested clean-code setup steps processed")


def main() -> None:
    args = parser().parse_args()
    repo = Path(args.repo).resolve()
    if not repo.exists():
        raise SystemExit(f"Repo does not exist: {repo}")
    target_repo = resolve_target_repo(repo, args.target)
    wants_mcp_runtime = args.mcp_runtime or args.start_mcp_runtime
    plan = build_plan(
        target_repo,
        allow_dirty=args.allow_dirty,
        require_languages=not wants_mcp_runtime,
        allow_root_monorepo=args.allow_root_monorepo,
    )
    if wants_mcp_runtime:
        plan_mcp_runtime(target_repo, plan, start=args.start_mcp_runtime)
    hook_choice = resolve_hook_choice(args.git_hooks) if args.apply else args.git_hooks
    if hook_choice != "ask":
        plan_git_hooks(target_repo, plan, choice=hook_choice, mode=args.git_hook_mode)
    elif (plan.git_root / ".git").exists():
        plan.warnings.append(
            "Git hook setup will be offered during --apply. Use --git-hooks none to skip the prompt."
        )
    print_plan(plan)
    if args.apply:
        apply_requested_setup(
            plan,
            ApplyOptions(
                wants_mcp_runtime=wants_mcp_runtime,
                hook_choice=hook_choice,
                hook_mode=args.git_hook_mode,
                assume_yes=args.yes,
                skip_install=args.skip_install,
                create_backup=not args.no_backup,
            ),
        )


if __name__ == "__main__":
    main()
