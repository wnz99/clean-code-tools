#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_NAME = "clean-code-mcp-reviewer"
DEFAULT_SOURCE = REPO_ROOT / "skills" / DEFAULT_SKILL_NAME
DEFAULT_REMOTE_URL = "https://github.com/wnz99/clean-code-tools.git"
DEFAULT_UPDATE_BRANCH = "main"
AGENTS = ("claude", "codex")


class InstallError(Exception):
    @classmethod
    def missing_source(cls, source: Path) -> InstallError:
        return cls(f"Skill source does not exist: {source}")

    @classmethod
    def missing_skill_md(cls, source: Path) -> InstallError:
        return cls(f"Skill source is missing SKILL.md: {source}")

    @classmethod
    def existing_destination(cls, destination: Path) -> InstallError:
        return cls(
            f"Destination already exists: {destination}\n"
            "Use --replace to overwrite the installed skill."
        )

    @classmethod
    def failed_git_command(cls, output: str) -> InstallError:
        return cls(f"Failed to fetch the latest skill source:\n{output.strip()}")


def default_dest_root(agent: str, project: Path) -> Path:
    agent_directory = ".codex" if agent == "codex" else ".claude"
    return project.expanduser().resolve() / agent_directory / "skills"


def validate_skill_source(source: Path) -> None:
    if not source.is_dir():
        raise InstallError.missing_source(source)
    if not (source / "SKILL.md").is_file():
        raise InstallError.missing_skill_md(source)


def copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__"}
    ignored.update(name for name in names if name.endswith(".pyc"))
    return ignored


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise InstallError.failed_git_command(completed.stdout)
    return completed


def fetch_skill_source_from_main(
    *,
    remote_url: str,
    branch: str,
    workspace: Path,
    skill_name: str,
) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    checkout = workspace / "clean-code-tools"
    run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            branch,
            remote_url,
            str(checkout),
        ],
    )
    return checkout / "skills" / skill_name


def install_skill(source: Path, dest_root: Path, *, name: str, replace: bool, dry_run: bool) -> Path:
    source = source.resolve()
    validate_skill_source(source)
    dest_root = dest_root.expanduser().resolve()
    destination = dest_root / name

    if destination.exists() and not replace:
        raise InstallError.existing_destination(destination)

    if dry_run:
        return destination

    dest_root.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=copy_ignore)
    return destination


def install_mcp_runtime(skill: Path, project: Path) -> None:
    installer = skill / "scripts" / "install_clean_code_linting.py"
    run(
        [
            sys.executable,
            str(installer),
            "--repo",
            str(project.resolve()),
            "--mcp-only",
            "--apply",
            "--yes",
            "--git-hooks",
            "none",
            "--no-backup",
        ]
    )


def shared_mcp_home() -> Path:
    configured = os.environ.get("CLEAN_CODE_TOOLS_HOME")
    return Path(configured).expanduser().resolve() if configured else Path.home() / ".clean-code-tools"


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="Install the clean-code agent skill into a project.")
    cli.add_argument(
        "--agent",
        choices=AGENTS,
        default="codex",
        help="Project-local agent skills directory to target when --dest is not set.",
    )
    cli.add_argument("--project", default=".", help="Project root for the local skill installation.")
    cli.add_argument("--source", default=str(DEFAULT_SOURCE), help="Skill source directory.")
    cli.add_argument("--dest", help="Destination skills directory.")
    cli.add_argument("--name", default=DEFAULT_SKILL_NAME, help="Installed skill directory name.")
    cli.add_argument("--replace", action="store_true", help="Overwrite an existing installed skill.")
    cli.add_argument("--dry-run", action="store_true", help="Print the destination without copying files.")
    cli.add_argument(
        "--no-mcp-runtime",
        action="store_true",
        help="Install only the project-local skill and skip the default shared MCP installation.",
    )
    cli.add_argument(
        "--from-main",
        action="store_true",
        help="Fetch the latest skill from the clean-code-tools main branch before installing.",
    )
    cli.add_argument(
        "--remote-url",
        default=DEFAULT_REMOTE_URL,
        help="Git remote used by --from-main.",
    )
    cli.add_argument(
        "--branch",
        default=DEFAULT_UPDATE_BRANCH,
        help="Git branch used by --from-main.",
    )
    return cli


def main() -> None:
    args = parser().parse_args()
    dest_root = Path(args.dest) if args.dest else default_dest_root(args.agent, Path(args.project))
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        source = Path(args.source)
        if args.from_main:
            temp_dir = tempfile.TemporaryDirectory()
            source = fetch_skill_source_from_main(
                remote_url=args.remote_url,
                branch=args.branch,
                workspace=Path(temp_dir.name),
                skill_name=args.name,
            )
        destination = install_skill(
            source,
            dest_root,
            name=args.name,
            replace=args.replace,
            dry_run=args.dry_run,
        )
    except InstallError as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
    action = "Would install" if args.dry_run else "Installed"
    print(f"{action} {args.name} to {destination}")
    if not args.dry_run:
        if not args.no_mcp_runtime:
            install_mcp_runtime(destination, Path(args.project))
            print(f"Installed and indexed the shared MCP runtime in {shared_mcp_home()}.")
        print("Restart the agent in this project to pick up the skill.")
        print("Then ask: Use $clean-code-mcp-reviewer to inspect this repo and plan installation.")


if __name__ == "__main__":
    main()
