#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_NAME = "clean-code-mcp-reviewer"
DEFAULT_SOURCE = REPO_ROOT / "skills" / DEFAULT_SKILL_NAME
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


def default_dest_root(agent: str) -> Path:
    if agent == "codex":
        return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser() / "skills"
    return Path.home() / ".claude" / "skills"


def validate_skill_source(source: Path) -> None:
    if not source.is_dir():
        raise InstallError.missing_source(source)
    if not (source / "SKILL.md").is_file():
        raise InstallError.missing_skill_md(source)


def copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__"}
    ignored.update(name for name in names if name.endswith(".pyc"))
    return ignored


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


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="Install the clean-code agent skill locally.")
    cli.add_argument(
        "--agent",
        choices=AGENTS,
        default="codex",
        help="Agent skills directory to target when --dest is not set.",
    )
    cli.add_argument("--source", default=str(DEFAULT_SOURCE), help="Skill source directory.")
    cli.add_argument("--dest", help="Destination skills directory.")
    cli.add_argument("--name", default=DEFAULT_SKILL_NAME, help="Installed skill directory name.")
    cli.add_argument("--replace", action="store_true", help="Overwrite an existing installed skill.")
    cli.add_argument("--dry-run", action="store_true", help="Print the destination without copying files.")
    return cli


def main() -> None:
    args = parser().parse_args()
    dest_root = Path(args.dest) if args.dest else default_dest_root(args.agent)
    try:
        destination = install_skill(
            Path(args.source),
            dest_root,
            name=args.name,
            replace=args.replace,
            dry_run=args.dry_run,
        )
    except InstallError as exc:
        raise SystemExit(str(exc)) from exc
    action = "Would install" if args.dry_run else "Installed"
    print(f"{action} {args.name} to {destination}")
    if not args.dry_run:
        print("Restart Codex to pick up the skill.")
        print("Then ask: Use $clean-code-mcp-reviewer to inspect this repo and plan installation.")


if __name__ == "__main__":
    main()
