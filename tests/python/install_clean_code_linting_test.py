from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
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
    def test_run_raises_command_output_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as raised:
                installer.run(
                    [sys.executable, "-c", "print('boom'); raise SystemExit(7)"],
                    cwd=Path(tmp),
                )

            self.assertIn("boom", str(raised.exception))

    def test_target_must_stay_inside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()

            with self.assertRaises(SystemExit):
                installer.resolve_target_repo(repo, "../outside")

            self.assertEqual(installer.resolve_target_repo(repo, None), repo)
            with self.assertRaises(SystemExit):
                installer.resolve_target_repo(repo, "missing")

    def test_non_git_helpers_return_conservative_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()

            self.assertEqual(installer.git_root_for(repo), repo)
            self.assertFalse(installer.is_git_dirty(repo))
            self.assertEqual(installer.create_rollback_point(repo), ["No Git repository found; no rollback point was created."])
            self.assertIsNone(installer.package_manager_root(repo, ("package.json",)))

    def test_package_manager_and_json_detection_branches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / "package.json").write_text("{not json")
            self.assertEqual(installer.package_json(repo), {})
            self.assertEqual(installer.package_json_scripts(repo), {})
            (repo / "package.json").write_text(json.dumps({"scripts": []}))
            self.assertEqual(installer.package_json_scripts(repo), {})

            for lockfile, manager in (
                ("bun.lock", "bun"),
                ("pnpm-lock.yaml", "pnpm"),
                ("yarn.lock", "yarn"),
                ("package-lock.json", "npm"),
            ):
                for path in repo.iterdir():
                    if path.name != "package.json":
                        path.unlink()
                (repo / lockfile).write_text("")
                self.assertEqual(installer.detect_js_package_manager(repo), manager)

            self.assertEqual(installer.js_install_command("bun", workspace_root=False)[:3], ["bun", "add", "-d"])
            self.assertEqual(installer.js_install_command("yarn", workspace_root=False)[:3], ["yarn", "add", "-D"])
            self.assertIn("-w", installer.js_install_command("pnpm", workspace_root=True))

    def test_python_install_detection_branches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/uv"):
                (repo / "main.py").write_text("print('x')\n")
                self.assertEqual(installer.detect_python_install_command(repo)[0], "uv")
            (repo / "main.py").unlink()
            (repo / "poetry.lock").write_text("")
            with mock.patch.object(installer.shutil, "which", return_value=None):
                self.assertEqual(installer.detect_python_install_command(repo)[:2], ["poetry", "add"])
            (repo / "poetry.lock").unlink()
            (repo / "requirements-dev.txt").write_text("")
            with mock.patch.object(installer.shutil, "which", return_value=None):
                self.assertEqual(installer.detect_python_install_command(repo)[:3], [sys.executable, "-m", "pip"])
            (repo / "requirements-dev.txt").unlink()
            (repo / "pyproject.toml").write_text("[project]\n")
            with mock.patch.object(installer.shutil, "which", return_value=None):
                self.assertEqual(installer.detect_python_install_command(repo)[:3], [sys.executable, "-m", "pip"])
            (repo / "pyproject.toml").unlink()
            with mock.patch.object(installer.shutil, "which", return_value=None):
                self.assertIsNone(installer.detect_python_install_command(repo))

    def test_plan_js_config_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
            (repo / "package-lock.json").write_text("{}\n")

            cases = [
                ("eslint.config.mjs", 'import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";\nexport default cleanCode;\n', "eslint already configured"),
                ("eslint.config.cjs", "module.exports = [];\n", "CommonJS"),
                ("eslint.config.mjs", "export default [js.configs.recommended];\n", "modify eslint.config.mjs"),
                ("eslint.config.mjs", "export default defineConfig([]);\n", "not a simple"),
            ]
            for filename, content, expected in cases:
                for config in repo.glob("eslint.config.*"):
                    config.unlink()
                (repo / filename).write_text(content)
                plan = installer.Plan(repo=repo, git_root=repo)
                with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/npm"):
                    installer.plan_js(repo, plan)
                text = "\n".join([change.label for change in plan.changes] + plan.blockers)
                self.assertIn(expected, text)

            for config in repo.glob("eslint.config.*"):
                config.unlink()
            with mock.patch.object(installer.shutil, "which", return_value=None):
                plan = installer.Plan(repo=repo, git_root=repo)
                installer.plan_js(repo, plan)
            self.assertTrue(any("not installed" in blocker for blocker in plan.blockers))

    def test_plan_js_respects_existing_fallow_jsonc_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
            (repo / "package-lock.json").write_text("{}\n")
            (repo / ".fallowrc.jsonc").write_text('{\n  // project-specific fallow config\n  "ignorePatterns": []\n}\n')

            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/npm"):
                plan = installer.Plan(repo=repo, git_root=repo)
                installer.plan_js(repo, plan)

            labels = [change.label for change in plan.changes]
            self.assertIn("fallow already configured", labels)
            self.assertNotIn(f"create {installer.FALLOW_CONFIG_NAME}", labels)

    def test_plan_python_config_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            plan = installer.Plan(repo=repo, git_root=repo)
            installer.plan_python(repo, plan)
            self.assertEqual(plan.languages, [])

            (repo / "app.py").write_text("print('x')\n")
            with mock.patch.object(installer.shutil, "which", return_value=None):
                plan = installer.Plan(repo=repo, git_root=repo)
                installer.plan_python(repo, plan)
            self.assertIn("create pyproject.toml", [change.label for change in plan.changes])

            (repo / "app.py").unlink()
            (repo / "pyproject.toml").write_text("[tool.ruff]\n")
            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/uv"):
                plan = installer.Plan(repo=repo, git_root=repo)
                installer.plan_python(repo, plan)
            self.assertTrue(any("manual" in blocker for blocker in plan.blockers))

            (repo / "pyproject.toml").write_text("[project]\n")
            plan = installer.Plan(repo=repo, git_root=repo)
            installer.plan_python(repo, plan)
            labels = [change.label for change in plan.changes]
            self.assertIn("append pyproject.toml deptry section", labels)
            self.assertIn("append pyproject.toml lint sections", labels)

            (repo / "pyproject.toml").write_text("[tool.deptry]\nclean_code_tools_pylint\nclean-code-todo-format\n")
            plan = installer.Plan(repo=repo, git_root=repo)
            installer.plan_python(repo, plan)
            self.assertIn("python lint already configured", [change.label for change in plan.changes])

    def test_verification_runtime_and_hook_planning_branches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            plan = installer.Plan(repo=repo, git_root=repo)
            installer.add_verification_plan(plan)
            self.assertTrue(any("No obvious" in warning for warning in plan.warnings))

            (repo / "pyproject.toml").write_text("[project]\n")
            plan = installer.Plan(repo=repo, git_root=repo)
            installer.add_verification_plan(plan)
            self.assertEqual(plan.verification[0].command, ["ruff", "check", "."])

            installer.plan_mcp_runtime(repo, plan, start=False)
            self.assertTrue(any(installer.MCP_RUNTIME_TARGET in change.label for change in plan.changes))
            with mock.patch.object(installer, "missing_runtime_modules", return_value=[]):
                env = {installer.MCP_RUNTIME_PORT_ENV: "9999"}
                with mock.patch.dict(installer.os.environ, env, clear=False):
                    start_plan = installer.Plan(repo=repo, git_root=repo)
                    installer.plan_mcp_runtime(repo, start_plan, start=True)
            self.assertEqual(start_plan.commands[0].command[-1], "9999")
            with mock.patch.object(installer, "missing_runtime_modules", return_value=["fastmcp"]):
                blocked_plan = installer.Plan(repo=repo, git_root=repo)
                installer.plan_mcp_runtime(repo, blocked_plan, start=True)
            self.assertTrue(any("Cannot start" in blocker for blocker in blocked_plan.blockers))
            (repo / installer.MCP_RUNTIME_TARGET).mkdir()
            installer.plan_mcp_runtime(repo, plan, start=True)
            self.assertTrue(any("already exists" in blocker for blocker in plan.blockers))

            self.assertEqual(installer.selected_hooks("both"), ("pre-commit", "pre-push"))
            self.assertEqual(installer.selected_hooks("none"), ())
            self.assertIn("default", installer.describe_hook_selection("ask", apply=True, assume_yes=False))
            self.assertIn("none selected", installer.describe_hook_selection("none", apply=True, assume_yes=True))
            self.assertIn("pre-push", installer.describe_hook_selection("pre-push", apply=False, assume_yes=False))

    def test_hook_planning_and_apply_branches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            plan = installer.Plan(repo=repo, git_root=repo)
            installer.plan_git_hooks(repo, plan, choice="none", mode="advisory")
            self.assertTrue(any("not selected" in warning for warning in plan.warnings))

            installer.plan_git_hooks(repo, plan, choice="pre-push", mode="advisory")
            self.assertTrue(any("not a Git working tree" in blocker for blocker in plan.blockers))

            run_git(repo, "init")
            hooks_dir = installer.git_hooks_dir(repo)
            hooks_dir.mkdir(parents=True, exist_ok=True)
            (hooks_dir / "pre-push").write_text("#!/bin/sh\necho existing\n")
            plan = installer.Plan(repo=repo, git_root=repo)
            installer.plan_git_hooks(repo, plan, choice="pre-push", mode="advisory")
            self.assertTrue(any("already exists" in blocker for blocker in plan.blockers))

            (hooks_dir / "pre-push").write_text(installer.hook_wrapper("pre-push", mode="advisory"))
            plan = installer.Plan(repo=repo, git_root=repo)
            installer.plan_git_hooks(repo, plan, choice="pre-push", mode="blocking")
            self.assertIn("install pre-push hook", [change.label for change in plan.changes])

            installer.apply_git_hooks(repo, choice="none", mode="advisory")
            installer.apply_git_hooks(repo, choice="pre-push", mode="blocking")
            pre_push_text = (hooks_dir / "pre-push").read_text()
            self.assertIn("--mode", pre_push_text)
            self.assertIn("--changed-since", pre_push_text)
            self.assertNotIn("--changed-since", installer.hook_wrapper("pre-commit", mode="advisory"))
            self.assertTrue((hooks_dir / installer.HOOK_SCRIPT_NAME).exists())

    def test_apply_config_helpers_write_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / "package.json").write_text(json.dumps({"scripts": []}))
            installer.apply_js(repo)
            self.assertTrue((repo / "eslint.config.mjs").exists())
            self.assertTrue((repo / installer.KNIP_CONFIG_NAME).exists())
            self.assertTrue((repo / installer.FALLOW_CONFIG_NAME).exists())
            scripts = json.loads((repo / "package.json").read_text())["scripts"]
            self.assertIn("check:knip", scripts)

            installer.apply_js(repo)
            (repo / "eslint.config.mjs").write_text("export default [];\n")
            installer.apply_js(repo)
            self.assertIn("...cleanCode", (repo / "eslint.config.mjs").read_text())

            no_package = repo / "no-package"
            no_package.mkdir()
            installer.apply_js_quality_config(no_package)
            self.assertTrue((no_package / installer.KNIP_CONFIG_NAME).exists())

            jsonc_repo = repo / "jsonc-fallow"
            jsonc_repo.mkdir()
            (jsonc_repo / ".fallowrc.jsonc").write_text('{"ignorePatterns": []}\n')
            installer.apply_js_quality_config(jsonc_repo)
            self.assertTrue((jsonc_repo / ".fallowrc.jsonc").exists())
            self.assertFalse((jsonc_repo / installer.FALLOW_CONFIG_NAME).exists())

            installer.apply_python(no_package)
            self.assertTrue((no_package / "pyproject.toml").exists())
            (no_package / "pyproject.toml").write_text("clean_code_tools_pylint\nclean-code-todo-format\n")
            installer.apply_python(no_package)
            self.assertIn("[tool.deptry]", (no_package / "pyproject.toml").read_text())
            self.assertEqual(installer.ensure_deptry_config("[tool.deptry]\n"), "[tool.deptry]\n")

    def test_apply_approval_helpers_track_declines_and_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            plan = installer.Plan(repo=repo, git_root=repo)
            summary = installer.ApplySummary()
            installer.apply_lint_config_if_approved(plan, assume_yes=True, summary=summary)
            self.assertIn("lint configuration: no supported languages detected", summary.skipped)

            plan.languages.append("javascript/typescript")
            with mock.patch.object(installer, "confirm", return_value=False):
                installer.apply_lint_config_if_approved(plan, assume_yes=False, summary=summary)
                installer.apply_runtime_if_approved(repo, wants_mcp_runtime=True, assume_yes=False, summary=summary)
                installer.apply_hooks_if_approved(repo, hook_choice="pre-push", mode="advisory", assume_yes=False, summary=summary)
                installer.install_packages_if_approved(plan, skip_install=False, assume_yes=False, summary=summary)
            self.assertTrue(any("approval declined" in item for item in summary.skipped))

            command = installer.PlannedCommand("echo", ["echo", "ok"], "dependency-install", repo)
            plan.commands.append(command)
            with mock.patch.object(installer, "run") as run_mock:
                installer.run_planned_commands(plan, category="dependency-install")
            run_mock.assert_called_once()
            self.assertTrue(installer.has_commands(plan, "dependency-install"))
            self.assertFalse(installer.has_commands(plan, "mcp-runtime"))

            output = StringIO()
            with redirect_stdout(output):
                installer.print_apply_summary(installer.ApplySummary())
            self.assertIn("applied: none", output.getvalue())

    def test_apply_approval_helpers_track_successes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            plan = installer.Plan(repo=repo, git_root=repo)
            plan.commands.extend(
                [
                    installer.PlannedCommand("install", ["echo", "install"], "dependency-install", repo),
                    installer.PlannedCommand("start", ["echo", "start"], "mcp-runtime", repo),
                ]
            )
            summary = installer.ApplySummary()
            with (
                mock.patch.object(installer, "confirm", return_value=True),
                mock.patch.object(installer, "apply_mcp_runtime") as runtime_mock,
                mock.patch.object(installer, "apply_git_hooks") as hooks_mock,
                mock.patch.object(installer, "run_planned_commands") as commands_mock,
            ):
                installer.apply_runtime_if_approved(repo, wants_mcp_runtime=True, assume_yes=False, summary=summary)
                installer.apply_hooks_if_approved(repo, hook_choice="pre-push", mode="advisory", assume_yes=False, summary=summary)
                installer.install_packages_if_approved(plan, skip_install=False, assume_yes=False, summary=summary)
                installer.start_runtime_if_approved(plan, assume_yes=False, summary=summary)

            runtime_mock.assert_called_once_with(repo)
            hooks_mock.assert_called_once()
            self.assertEqual(commands_mock.call_count, 2)
            self.assertIn(f"{installer.MCP_RUNTIME_TARGET}/ runtime files", summary.applied)
            self.assertIn("Git hooks (pre-push, advisory)", summary.applied)
            self.assertIn("development dependencies", summary.applied)
            self.assertIn("local MCP runtime start", summary.applied)

    def test_apply_requested_setup_rejects_empty_plan_and_prints_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            empty_plan = installer.Plan(repo=repo, git_root=repo)
            with self.assertRaises(SystemExit):
                installer.apply_requested_setup(
                    empty_plan,
                    installer.ApplyOptions(
                        wants_mcp_runtime=False,
                        hook_choice="none",
                        hook_mode="advisory",
                        assume_yes=True,
                        skip_install=True,
                        create_backup=False,
                    ),
                )

            run_git(repo, "init")
            run_git(repo, "config", "user.email", "test@example.com")
            run_git(repo, "config", "user.name", "Test User")
            (repo / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
            (repo / "package-lock.json").write_text("{}\n")
            run_git(repo, "add", "package.json", "package-lock.json")
            run_git(repo, "commit", "-m", "initial")
            plan = installer.Plan(
                repo=repo,
                git_root=repo,
                languages=["javascript/typescript"],
                changes=[installer.Change("noop", "test")],
            )
            output = StringIO()
            with mock.patch.object(installer, "apply_lint_config"), redirect_stdout(output):
                installer.apply_requested_setup(
                    plan,
                    installer.ApplyOptions(
                        wants_mcp_runtime=False,
                        hook_choice="none",
                        hook_mode="advisory",
                        assume_yes=True,
                        skip_install=True,
                        create_backup=True,
                    ),
                )
            self.assertIn("rollback point:", output.getvalue())
            self.assertIn("rollback point", output.getvalue())

    def test_main_prints_plan_and_blocks_unresolved_yes_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
            (repo / "package-lock.json").write_text("{}\n")

            output = StringIO()
            argv = [
                "install_clean_code_linting.py",
                "--repo",
                str(repo),
                "--apply",
                "--yes",
                "--no-backup",
            ]
            with (
                mock.patch.object(installer.sys, "argv", argv),
                mock.patch.object(installer.shutil, "which", return_value="/usr/bin/npm"),
                redirect_stdout(output),
                self.assertRaises(SystemExit),
            ):
                installer.main()

            text = output.getvalue()
            self.assertIn("--apply --yes requires an explicit hook decision", text)
            self.assertIn("No changes were applied.", text)

    def test_main_applies_explicit_no_hook_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
            (repo / "package-lock.json").write_text("{}\n")
            argv = [
                "install_clean_code_linting.py",
                "--repo",
                str(repo),
                "--apply",
                "--yes",
                "--no-backup",
                "--skip-install",
                "--git-hooks",
                "none",
            ]
            output = StringIO()
            with (
                mock.patch.object(installer.sys, "argv", argv),
                mock.patch.object(installer.shutil, "which", return_value="/usr/bin/npm"),
                redirect_stdout(output),
            ):
                installer.main()

            self.assertIn("Git hook selection: none selected.", output.getvalue())
            self.assertIn("apply summary:", output.getvalue())

    def test_confirm_and_parser_branches(self) -> None:
        self.assertTrue(installer.confirm("x", assume_yes=True))
        with mock.patch.object(installer.sys, "stdin") as stdin:
            stdin.isatty.return_value = False
            self.assertFalse(installer.confirm("x", assume_yes=False))
        with mock.patch.object(installer.sys, "stdin") as stdin, mock.patch("builtins.input", return_value="yes"):
            stdin.isatty.return_value = True
            self.assertTrue(installer.confirm("x", assume_yes=False))
        args = installer.parser().parse_args(["--git-hooks", "both", "--git-hook-mode", "blocking"])
        self.assertEqual(args.git_hooks, "both")
        self.assertEqual(args.git_hook_mode, "blocking")

    def test_apply_mcp_runtime_copies_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            installer.apply_mcp_runtime(repo)
            runtime = repo / installer.MCP_RUNTIME_TARGET
            self.assertTrue((runtime / "runtime").is_dir())


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

    def test_noninteractive_apply_requires_explicit_hook_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            run_git(repo, "init")
            (repo / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
            (repo / "package-lock.json").write_text("{}\n")

            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/npm"):
                plan = installer.build_plan(repo, allow_dirty=True)

            installer.add_noninteractive_hook_blocker(
                plan,
                apply=True,
                assume_yes=True,
                hook_choice="ask",
            )

            self.assertTrue(any("--apply --yes requires an explicit hook decision" in blocker for blocker in plan.blockers))
            self.assertIn(
                "unresolved",
                installer.describe_hook_selection("ask", apply=True, assume_yes=True),
            )

    def test_dry_run_prints_hook_selection_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            run_git(repo, "init")
            (repo / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
            (repo / "package-lock.json").write_text("{}\n")

            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/npm"):
                plan = installer.build_plan(repo, allow_dirty=True)
            plan.warnings.append(
                f"Git hook selection: {installer.describe_hook_selection('ask', apply=False, assume_yes=False)}."
            )

            output = StringIO()
            with redirect_stdout(output):
                installer.print_plan(plan)

            self.assertIn("Git hook selection:", output.getvalue())
            self.assertIn("--git-hooks pre-push", output.getvalue())

    def test_apply_summary_names_intentionally_skipped_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            run_git(repo, "init")
            run_git(repo, "config", "user.email", "test@example.com")
            run_git(repo, "config", "user.name", "Test User")
            (repo / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
            (repo / "package-lock.json").write_text("{}\n")
            run_git(repo, "add", "package.json", "package-lock.json")
            run_git(repo, "commit", "-m", "initial")

            with mock.patch.object(installer.shutil, "which", return_value="/usr/bin/npm"):
                plan = installer.build_plan(repo, allow_dirty=True)

            options = installer.ApplyOptions(
                wants_mcp_runtime=False,
                hook_choice="none",
                hook_mode="advisory",
                assume_yes=True,
                skip_install=True,
                create_backup=False,
            )
            output = StringIO()
            with redirect_stdout(output):
                installer.apply_requested_setup(plan, options)

            text = output.getvalue()
            self.assertIn("apply summary:", text)
            self.assertIn("Git hooks: choice was none", text)
            self.assertIn("package installation: --skip-install was passed", text)

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
