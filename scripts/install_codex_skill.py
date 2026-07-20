#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_NAME = "clean-code-tools"
DEFAULT_SOURCE = REPO_ROOT / "skills" / DEFAULT_SKILL_NAME
DEFAULT_REMOTE_URL = "https://github.com/wnz99/clean-code-tools.git"
DEFAULT_UPDATE_BRANCH = "main"
AGENTS = ("claude", "codex")
MCP_SERVER_NAME = "clean-code-tools"
CODEX_MCP_START = "# BEGIN clean-code-tools managed MCP"
CODEX_MCP_END = "# END clean-code-tools managed MCP"


class McpRegistrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent: Literal["claude", "codex"]
    project: Path
    home: Path


class McpServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str
    args: list[str]
    env: dict[str, str]


class ClaudeMcpConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    mcpServers: dict[str, McpServerConfig | JsonValue] = Field(default_factory=dict)


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

    @classmethod
    def unmanaged_codex_mcp(cls, config_path: Path) -> InstallError:
        return cls(
            f"Refusing to overwrite unmanaged Codex MCP server {MCP_SERVER_NAME!r} "
            f"in {config_path}."
        )


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


def runtime_python(home: Path) -> Path:
    if os.name == "nt":
        return home / ".venv" / "Scripts" / "python.exe"
    return home / ".venv" / "bin" / "python"


def mcp_server_config(home: Path) -> McpServerConfig:
    return McpServerConfig(
        command=str(runtime_python(home)),
        args=[str(home / "runtime" / "scripts" / "clean_code_mcp_server.py")],
        env={
            "CLEAN_CODE_INDEX_BASE": str(home),
            "CLEAN_CODE_VECTOR_INDEX_PATH": str(home / "clean-code-index.sqlite"),
        },
    )


def codex_mcp_block(config: McpServerConfig) -> str:
    command = json.dumps(config.command)
    args = ", ".join(json.dumps(argument) for argument in config.args)
    env = "\n".join(f"{key} = {json.dumps(value)}" for key, value in config.env.items())
    return (
        f"{CODEX_MCP_START}\n"
        f"[mcp_servers.{MCP_SERVER_NAME}]\n"
        f"command = {command}\n"
        f"args = [{args}]\n\n"
        f"[mcp_servers.{MCP_SERVER_NAME}.env]\n"
        f"{env}\n"
        f"{CODEX_MCP_END}"
    )


def register_codex_mcp(project: Path, config: McpServerConfig) -> Path:
    config_path = project / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    current = config_path.read_text() if config_path.exists() else ""
    if current:
        tomllib.loads(current)
    block = codex_mcp_block(config)
    managed_pattern = re.compile(
        rf"{re.escape(CODEX_MCP_START)}.*?{re.escape(CODEX_MCP_END)}",
        re.DOTALL,
    )
    if managed_pattern.search(current):
        updated = managed_pattern.sub(block, current, count=1)
    else:
        parsed = tomllib.loads(current) if current else {}
        existing_servers = parsed.get("mcp_servers", {})
        if MCP_SERVER_NAME in existing_servers:
            raise InstallError.unmanaged_codex_mcp(config_path)
        separator = "\n\n" if current.strip() else ""
        updated = f"{current.rstrip()}{separator}{block}\n"
    tomllib.loads(updated)
    config_path.write_text(updated)
    return config_path


def register_claude_mcp(project: Path, config: McpServerConfig) -> Path:
    config_path = project / ".mcp.json"
    if config_path.exists():
        parsed = ClaudeMcpConfig.model_validate_json(config_path.read_text())
    else:
        parsed = ClaudeMcpConfig()
    parsed.mcpServers[MCP_SERVER_NAME] = config
    config_path.write_text(parsed.model_dump_json(indent=2) + "\n")
    return config_path


def register_mcp_launcher(*, agent: str, project: Path, home: Path) -> Path:
    request = McpRegistrationRequest.model_validate(
        {"agent": agent, "project": project.resolve(), "home": home.resolve()}
    )
    config = mcp_server_config(request.home)
    if request.agent == "codex":
        return register_codex_mcp(request.project, config)
    return register_claude_mcp(request.project, config)


def shared_mcp_home() -> Path:
    configured = os.environ.get("CLEAN_CODE_TOOLS_HOME")
    return Path(configured).expanduser().resolve() if configured else Path.home() / ".clean-code-tools"


def print_mcp_launcher_requirements(home: Path) -> None:
    """Print the environment contract required by project-local MCP launchers."""
    print("Configure the clean-code MCP launcher with:")
    print(f"  CLEAN_CODE_INDEX_BASE={home}")
    print(f"  CLEAN_CODE_VECTOR_INDEX_PATH={home / 'clean-code-index.sqlite'}")
    print("After restarting the agent, verify search_clean_code_patterns returns results.")


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
            home = shared_mcp_home()
            print(f"Installed and indexed the shared MCP runtime in {home}.")
            launcher_config = register_mcp_launcher(
                agent=args.agent,
                project=Path(args.project),
                home=home,
            )
            print(f"Configured the {args.agent} MCP launcher in {launcher_config}.")
        print("Restart the agent in this project to pick up the skill.")
        print("Then ask: Use $clean-code-tools to inspect this repo and plan installation.")


if __name__ == "__main__":
    main()
