from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "install_codex_skill.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("install_codex_skill", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


installer = load_installer()


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)  # noqa: S603,S607


class InstallCodexSkillTest(unittest.TestCase):
    def test_default_dest_root_uses_project_codex_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            self.assertEqual(installer.default_dest_root("codex", project), project / ".codex" / "skills")

    def test_default_dest_root_supports_project_local_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            self.assertEqual(installer.default_dest_root("claude", project), project / ".claude" / "skills")

    def test_install_copies_skill_and_ignores_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source-skill"
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n")
            cache = source / "__pycache__"
            cache.mkdir()
            (cache / "ignored.pyc").write_bytes(b"bytecode")

            destination = installer.install_skill(
                source,
                root / "codex" / "skills",
                name="source-skill",
                replace=False,
                dry_run=False,
            )

            self.assertTrue((destination / "SKILL.md").exists())
            self.assertFalse((destination / "__pycache__").exists())

    def test_existing_destination_requires_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source-skill"
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n")
            dest_root = root / "codex" / "skills"
            existing = dest_root / "source-skill"
            existing.mkdir(parents=True)

            with self.assertRaises(installer.InstallError):
                installer.install_skill(
                    source,
                    dest_root,
                    name="source-skill",
                    replace=False,
                    dry_run=False,
                )

            installer.install_skill(
                source,
                dest_root,
                name="source-skill",
                replace=True,
                dry_run=False,
            )
            self.assertTrue((existing / "SKILL.md").exists())

    def test_dry_run_validates_source_without_copying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source-skill"
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n")

            destination = installer.install_skill(
                source,
                root / "codex" / "skills",
                name="source-skill",
                replace=False,
                dry_run=True,
            )

            self.assertEqual(destination, (root / "codex" / "skills" / "source-skill").resolve())
            self.assertFalse(destination.exists())

    def test_missing_source_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaises(installer.InstallError) as missing_source:
                installer.install_skill(
                    root / "missing",
                    root / "codex" / "skills",
                    name="source-skill",
                    replace=False,
                    dry_run=False,
                )

            self.assertIn("does not exist", str(missing_source.exception))

    def test_missing_skill_md_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source-skill"
            source.mkdir()

            with self.assertRaises(installer.InstallError) as missing_skill_md:
                installer.install_skill(
                    source,
                    root / "codex" / "skills",
                    name="source-skill",
                    replace=False,
                    dry_run=False,
                )

            self.assertIn("SKILL.md", str(missing_skill_md.exception))

    def test_main_dry_run_prints_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source-skill"
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n")
            output = io.StringIO()

            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "install_codex_skill.py",
                        "--agent",
                        "codex",
                        "--source",
                        str(source),
                        "--dest",
                        str(root / "codex" / "skills"),
                        "--dry-run",
                    ],
                ),
                redirect_stdout(output),
            ):
                installer.main()

            self.assertIn("Would install", output.getvalue())

    def test_runtime_install_uses_installed_project_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            skill = root / ".codex" / "skills" / "clean-code-mcp-reviewer"
            installer_path = skill / "scripts" / "install_clean_code_linting.py"
            installer_path.parent.mkdir(parents=True)
            installer_path.write_text("# test\n")
            with mock.patch.object(installer, "run") as run_mock:
                installer.install_mcp_runtime(skill, root)
            command = run_mock.call_args.args[0]
            self.assertIn(str(installer_path), command)
            self.assertIn("--mcp-only", command)
            self.assertIn("--apply", command)

    def test_shared_mcp_home_honors_configured_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            configured = Path(tmp).resolve() / "runtime-home"
            with mock.patch.dict(os.environ, {"CLEAN_CODE_TOOLS_HOME": str(configured)}):
                self.assertEqual(installer.shared_mcp_home(), configured)

    def test_launcher_requirements_include_allowed_base_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve() / "runtime-home"
            output = io.StringIO()

            with redirect_stdout(output):
                installer.print_mcp_launcher_requirements(home)

            rendered = output.getvalue()
            self.assertIn(f"CLEAN_CODE_INDEX_BASE={home}", rendered)
            self.assertIn(
                f"CLEAN_CODE_VECTOR_INDEX_PATH={home / 'clean-code-index.sqlite'}",
                rendered,
            )
            self.assertIn("search_clean_code_patterns", rendered)

    def test_register_codex_mcp_preserves_config_and_updates_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            config_path = project / ".codex" / "config.toml"
            config_path.parent.mkdir()
            config_path.write_text('model = "gpt-test"\n')
            first_home = project / "first-home"
            second_home = project / "second-home"

            result = installer.register_mcp_launcher(
                agent="codex", project=project, home=first_home
            )
            installer.register_mcp_launcher(agent="codex", project=project, home=second_home)

            self.assertEqual(result, config_path)
            parsed = tomllib.loads(config_path.read_text())
            self.assertEqual(parsed["model"], "gpt-test")
            server = parsed["mcp_servers"]["clean-code-tools"]
            self.assertEqual(server["command"], str(installer.runtime_python(second_home)))
            self.assertEqual(server["env"]["CLEAN_CODE_INDEX_BASE"], str(second_home))
            self.assertEqual(config_path.read_text().count(installer.CODEX_MCP_START), 1)

    def test_register_codex_mcp_refuses_unmanaged_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            config_path = project / ".codex" / "config.toml"
            config_path.parent.mkdir()
            config_path.write_text('[mcp_servers.clean-code-tools]\ncommand = "other"\n')

            with self.assertRaises(installer.InstallError):
                installer.register_mcp_launcher(
                    agent="codex", project=project, home=project / "runtime"
                )

    def test_register_claude_mcp_preserves_other_servers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            config_path = project / ".mcp.json"
            config_path.write_text(
                '{"mcpServers":{"remote":{"type":"http","url":"https://example.test/mcp"}},'
                '"customSetting":true}'
            )
            home = project / "runtime-home"

            result = installer.register_mcp_launcher(
                agent="claude", project=project, home=home
            )

            self.assertEqual(result, config_path)
            parsed = json.loads(config_path.read_text())
            self.assertEqual(parsed["mcpServers"]["remote"]["url"], "https://example.test/mcp")
            self.assertTrue(parsed["customSetting"])
            server = parsed["mcpServers"]["clean-code-tools"]
            self.assertEqual(server["command"], str(installer.runtime_python(home)))
            self.assertEqual(server["env"]["CLEAN_CODE_INDEX_BASE"], str(home))

    def test_runtime_python_uses_windows_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            with mock.patch.object(installer.os, "name", "nt"):
                self.assertEqual(
                    installer.runtime_python(home),
                    home / ".venv" / "Scripts" / "python.exe",
                )

    def test_fetch_skill_source_from_main_clones_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote"
            remote.mkdir()
            run_git(remote, "init", "-b", "main")
            run_git(remote, "config", "user.email", "test@example.com")
            run_git(remote, "config", "user.name", "Test User")
            skill = remote / "skills" / "clean-code-mcp-reviewer"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: clean-code-mcp-reviewer\ndescription: test\n---\n")
            run_git(remote, "add", "skills")
            run_git(remote, "commit", "-m", "skill")

            source = installer.fetch_skill_source_from_main(
                remote_url=str(remote),
                branch="main",
                workspace=root / "workspace",
                skill_name="clean-code-mcp-reviewer",
            )

            self.assertTrue((source / "SKILL.md").exists())

    def test_main_from_main_installs_latest_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote"
            remote.mkdir()
            run_git(remote, "init", "-b", "main")
            run_git(remote, "config", "user.email", "test@example.com")
            run_git(remote, "config", "user.name", "Test User")
            skill = remote / "skills" / "clean-code-mcp-reviewer"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: clean-code-mcp-reviewer\ndescription: from main\n---\n")
            run_git(remote, "add", "skills")
            run_git(remote, "commit", "-m", "skill")

            output = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "install_codex_skill.py",
                        "--agent",
                        "codex",
                        "--dest",
                        str(root / "codex" / "skills"),
                        "--from-main",
                        "--remote-url",
                        str(remote),
                        "--replace",
                        "--no-mcp-runtime",
                    ],
                ),
                redirect_stdout(output),
            ):
                installer.main()

            installed = root / "codex" / "skills" / "clean-code-mcp-reviewer" / "SKILL.md"
            self.assertIn("from main", installed.read_text())
            self.assertIn("Installed clean-code-mcp-reviewer", output.getvalue())

    def test_main_registers_mcp_for_selected_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root / "source-skill"
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n")
            home = root / "runtime-home"
            launcher = root / ".mcp.json"

            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "install_codex_skill.py",
                        "--agent",
                        "claude",
                        "--project",
                        str(root),
                        "--source",
                        str(source),
                    ],
                ),
                mock.patch.object(installer, "install_mcp_runtime"),
                mock.patch.object(installer, "shared_mcp_home", return_value=home),
                mock.patch.object(
                    installer, "register_mcp_launcher", return_value=launcher
                ) as register_mock,
            ):
                installer.main()

            register_mock.assert_called_once_with(agent="claude", project=root, home=home)

    def test_main_from_main_converts_git_failure_to_system_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "install_codex_skill.py",
                        "--dest",
                        str(root / "codex" / "skills"),
                        "--from-main",
                        "--remote-url",
                        str(root / "missing"),
                    ],
                ),
                self.assertRaises(SystemExit) as exit_error,
            ):
                installer.main()

            self.assertIn("Failed to fetch", str(exit_error.exception))

    def test_main_converts_install_error_to_system_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "install_codex_skill.py",
                        "--source",
                        str(root / "missing"),
                        "--dest",
                        str(root / "codex" / "skills"),
                    ],
                ),
                self.assertRaises(SystemExit) as exit_error,
            ):
                installer.main()

            self.assertIn("does not exist", str(exit_error.exception))


if __name__ == "__main__":
    unittest.main()
