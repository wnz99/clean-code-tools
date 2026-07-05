from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "clean-code-mcp-reviewer"
    / "scripts"
    / "install_clean_code_linting.py"
)


def load_installer():
    spec = importlib.util.spec_from_file_location("install_clean_code_linting", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


installer = load_installer()


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)  # noqa: S603,S607


class CleanCodeInstallerTest(unittest.TestCase):
    def test_target_must_stay_inside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()

            with self.assertRaises(SystemExit):
                installer.resolve_target_repo(repo, "../outside")

    def test_nested_package_uses_ancestor_pnpm_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            run_git(repo, "init")
            (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
            (repo / "package.json").write_text(json.dumps({"workspaces": ["packages/*"]}))
            app = repo / "packages" / "app"
            app.mkdir(parents=True)
            (app / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))

            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/pnpm"):
                plan = installer.build_plan(app, allow_dirty=True)

            self.assertEqual(plan.languages, ["javascript/typescript"])
            self.assertEqual(plan.commands[0].cwd, repo)
            self.assertEqual(plan.commands[0].command[:3], ["pnpm", "add", "-D"])
            self.assertEqual(plan.verification[0].command, ["pnpm", "run", "lint"])
            self.assertIn("ancestor", plan.warnings[0])

    def test_workspace_root_requires_explicit_monorepo_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            run_git(repo, "init")
            (repo / "pnpm-workspace.yaml").write_text("packages:\n  - packages/*\n")
            (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
            (repo / "package.json").write_text(json.dumps({"scripts": {"test": "node test.js"}}))

            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/pnpm"):
                plan = installer.build_plan(repo, allow_dirty=True)

            self.assertTrue(any("Root monorepo detected" in blocker for blocker in plan.blockers))
            self.assertIn("-w", plan.commands[0].command)
            self.assertTrue(any("workspace root" in warning for warning in plan.warnings))

    def test_workspace_root_can_be_explicitly_approved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            run_git(repo, "init")
            (repo / "pnpm-workspace.yaml").write_text("packages:\n  - packages/*\n")
            (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
            (repo / "package.json").write_text(json.dumps({"scripts": {"test": "node test.js"}}))

            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/pnpm"):
                plan = installer.build_plan(
                    repo,
                    allow_dirty=True,
                    allow_root_monorepo=True,
                )

            self.assertFalse(any("Root monorepo detected" in blocker for blocker in plan.blockers))
            self.assertIn("-w", plan.commands[0].command)

    def test_rollback_point_creates_branch_and_dirty_patch_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            run_git(repo, "init")
            run_git(repo, "config", "user.email", "test@example.com")
            run_git(repo, "config", "user.name", "Test User")
            tracked_file = repo / "tracked.txt"
            tracked_file.write_text("before\n")
            run_git(repo, "add", "tracked.txt")
            run_git(repo, "commit", "-m", "initial")

            tracked_file.write_text("after\n")

            notes = installer.create_rollback_point(repo)

            branches = subprocess.run(
                ["git", "branch", "--list", "backup/clean-code-install-*"],  # noqa: S607
                cwd=repo,
                check=True,
                text=True,
                capture_output=True,
            ).stdout
            self.assertIn("backup/clean-code-install-", branches)
            self.assertTrue(any("backup branch" in note for note in notes))
            patch_dirs = list((repo / ".git" / "clean-code-installer-backups").iterdir())
            self.assertEqual(len(patch_dirs), 1)
            self.assertIn("after", (patch_dirs[0] / "unstaged.patch").read_text())


if __name__ == "__main__":
    unittest.main()
