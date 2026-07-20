from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any
from unittest import mock

HOOK_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "clean-code-tools"
    / "hooks"
    / "clean_code_agent_feedback.py"
)


def load_hook():
    spec = importlib.util.spec_from_file_location("clean_code_agent_feedback", HOOK_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hook = load_hook()


class CleanCodeAgentFeedbackTest(unittest.TestCase):
    def test_json_catalog_query_package_manager_and_relative_helpers(self) -> None:
        original_catalog = hook.CATALOG
        hook.CATALOG = {
            "schema": {"ignored": True},
            "eslint": {"clean-code/noisy-comment": {"mcp_query": "typescript noisy comment"}},
            "ruff": {"F401": {"mcp_query": "python unused import"}},
        }
        try:
            self.assertEqual(hook.query_for("eslint", "clean-code/noisy-comment"), "typescript noisy comment")
            self.assertIsNone(hook.query_for("eslint", "missing"))
        finally:
            hook.CATALOG = original_catalog

        self.assertIsNone(hook.load_json(""))
        self.assertIsNone(hook.load_json("{not json"))
        self.assertEqual(hook.load_json('{"ok": true}'), {"ok": True})
        self.assertEqual(hook.optional_int(7), 7)
        self.assertIsNone(hook.optional_int("7"))

        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp).resolve()
            self.assertIsNone(hook.package_manager(repo))
            for lockfile, expected in (
                ("bun.lock", "bun"),
                ("pnpm-lock.yaml", "pnpm"),
                ("yarn.lock", "yarn"),
                ("package-lock.json", "npm"),
            ):
                for child in repo.iterdir():
                    child.unlink()
                (repo / lockfile).write_text("")
                self.assertEqual(hook.package_manager(repo), expected)

            path = repo / "src" / "app.py"
            path.parent.mkdir()
            path.write_text("")
            self.assertEqual(hook.relative(repo, str(path)), "src/app.py")
            self.assertEqual(hook.relative(repo, ""), "")
            self.assertEqual(hook.relative(repo, "/outside.py"), "/outside.py")

    def test_changed_files_filters_git_diff_to_existing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp)
            (repo / "src").mkdir()
            (repo / "src" / "app.ts").write_text("const ok = true;\n")

            def fake_run(command: list[str], **_: Any) -> object:
                self.assertEqual(command[:4], ["git", "diff", "--name-only", "--diff-filter=ACMR"])
                return types.SimpleNamespace(
                    returncode=0,
                    stdout="src/app.ts\nsrc/deleted.ts\n\n",
                )

            original_run = hook.run
            hook.run = fake_run
            try:
                self.assertEqual(hook.changed_files(repo, "origin/develop"), ["src/app.ts"])
            finally:
                hook.run = original_run

    def test_changed_files_returns_empty_when_git_diff_fails(self) -> None:
        original_run = hook.run
        hook.run = lambda *_args, **_kwargs: types.SimpleNamespace(returncode=1, stdout="")
        try:
            self.assertEqual(hook.changed_files(Path.cwd(), "missing"), [])
        finally:
            hook.run = original_run

    def test_changed_file_commands_pass_only_matching_extensions(self) -> None:
        self.assertEqual(
            hook.eslint_command("bun", ["src/app.ts", "src/view.tsx"]),
            ["bunx", "eslint", "src/app.ts", "src/view.tsx", "--format", "json"],
        )
        self.assertEqual(
            hook.eslint_command("pnpm", ["src/app.js"]),
            ["pnpm", "exec", "eslint", "src/app.js", "--format", "json"],
        )
        self.assertEqual(
            hook.eslint_command("yarn", ["src/app.jsx"]),
            ["yarn", "eslint", "src/app.jsx", "--format", "json"],
        )
        self.assertEqual(
            hook.eslint_command("npm", ["src/app.mjs"]),
            ["npx", "eslint", "src/app.mjs", "--format", "json"],
        )
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp)
            (repo / "pyproject.toml").write_text("[project]\n")
            with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/uv"):
                self.assertEqual(
                    hook.python_command(repo, "ruff", ["src/app.py"]),
                    ["uv", "run", "ruff", "check", "src/app.py", "--output-format=json"],
                )
                self.assertEqual(
                    hook.python_command(repo, "pylint", ["src/app.py"]),
                    ["uv", "run", "pylint", "src/app.py", "--output-format=json"],
                )
            with mock.patch.object(hook.shutil, "which", return_value=None):
                self.assertEqual(
                    hook.python_command(repo, "ruff", ["src/app.py"])[:5],
                    [sys.executable, "-m", "ruff", "check", "src/app.py"],
                )
                self.assertEqual(
                    hook.python_command(repo, "pylint", ["src/app.py"])[:4],
                    [sys.executable, "-m", "pylint", "src/app.py"],
                )

    def test_findings_skip_tools_when_changed_files_do_not_match_language(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str], **_: Any) -> object:
            calls.append(command)
            return types.SimpleNamespace(returncode=0, stdout="[]")

        original_run = hook.run
        hook.run = fake_run
        try:
            with tempfile.TemporaryDirectory() as raw_tmp:
                repo = Path(raw_tmp)
                (repo / "package.json").write_text("{}\n")
                (repo / "pyproject.toml").write_text("[project]\n")
                (repo / "bun.lock").write_text("")

                self.assertEqual(hook.eslint_findings(repo, timeout=1, files=["README.md"]), [])
                self.assertEqual(hook.ruff_findings(repo, timeout=1, files=["README.md"]), [])
        finally:
            hook.run = original_run

        self.assertEqual(calls, [])

    def test_lint_findings_parse_json_payloads(self) -> None:
        original_catalog = hook.CATALOG
        original_run = hook.run
        hook.CATALOG = {
            "eslint": {"clean-code/noisy-comment": {"mcp_query": "typescript noisy comment"}},
            "ruff": {"F401": {"mcp_query": "python unused import"}},
            "pylint": {"too-many-branches": {"mcp_query": "python branch complexity"}},
        }

        def fake_run(command: list[str], **_: Any) -> object:
            command_text = " ".join(command)
            if "eslint" in command_text:
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        [
                            "ignored",
                            {
                                "filePath": "src/app.ts",
                                "messages": [
                                    "ignored",
                                    {"ruleId": None},
                                    {
                                        "ruleId": "clean-code/noisy-comment",
                                        "line": 3,
                                        "message": "noisy",
                                    },
                                ],
                            },
                        ]
                    )
                )
            if "ruff" in command_text:
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        [
                            "ignored",
                            {
                                "code": "F401",
                                "filename": "src/app.py",
                                "location": {"row": 4},
                                "message": "unused import",
                            },
                            {"code": None},
                        ]
                    )
                )
            return types.SimpleNamespace(
                stdout=json.dumps(
                    [
                        "ignored",
                        {
                            "symbol": "too-many-branches",
                            "path": "src/app.py",
                            "line": 5,
                            "message": "branchy",
                        },
                        {"symbol": None},
                    ]
                )
            )

        hook.run = fake_run
        try:
            with tempfile.TemporaryDirectory() as raw_tmp:
                repo = Path(raw_tmp)
                (repo / "package.json").write_text("{}\n")
                (repo / "bun.lock").write_text("")
                (repo / "pyproject.toml").write_text("[project]\n")

                eslint_findings = hook.eslint_findings(repo, timeout=1, files=["src/app.ts"])
                ruff_findings = hook.ruff_findings(repo, timeout=1, files=["src/app.py"])
                pylint_findings = hook.pylint_findings(repo, timeout=1, files=["src/app.py"])
        finally:
            hook.CATALOG = original_catalog
            hook.run = original_run

        self.assertEqual(eslint_findings[0].query, "typescript noisy comment")
        self.assertEqual(ruff_findings[0].line, 4)
        self.assertEqual(pylint_findings[0].message, "branchy")

    def test_lint_findings_ignore_missing_tools_and_invalid_json(self) -> None:
        original_run = hook.run
        try:
            with tempfile.TemporaryDirectory() as raw_tmp:
                repo = Path(raw_tmp)
                self.assertEqual(hook.eslint_findings(repo, timeout=1), [])
                self.assertEqual(hook.ruff_findings(repo, timeout=1), [])

                (repo / "package.json").write_text("{}\n")
                hook.run = lambda *_args, **_kwargs: None
                self.assertEqual(hook.eslint_findings(repo, timeout=1), [])
                hook.run = lambda *_args, **_kwargs: types.SimpleNamespace(stdout="{}")
                self.assertEqual(hook.eslint_findings(repo, timeout=1), [])

                (repo / "main.py").write_text("print('x')\n")
                hook.run = lambda *_args, **_kwargs: None
                self.assertEqual(hook.ruff_findings(repo, timeout=1), [])
                self.assertEqual(hook.pylint_findings(repo, timeout=1), [])
                hook.run = lambda *_args, **_kwargs: types.SimpleNamespace(stdout="{}")
                self.assertEqual(hook.ruff_findings(repo, timeout=1), [])
                self.assertEqual(hook.pylint_findings(repo, timeout=1), [])
        finally:
            hook.run = original_run

    def test_print_feedback_and_include_pylint(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            hook.print_feedback([], hook_name="pre-push", limit=10, blocking=False)
        self.assertIn("no semantic review candidates", output.getvalue())

        findings = [
            hook.Finding(
                tool="ruff",
                rule="F401",
                file="src/app.py",
                line=2,
                message="unused",
                query="python unused import",
            ),
            hook.Finding(
                tool="eslint",
                rule="x",
                file="src/app.ts",
                line=None,
                message="issue",
                query="typescript issue",
            ),
        ]
        output = StringIO()
        with redirect_stdout(output):
            hook.print_feedback(findings, hook_name="pre-push", limit=1, blocking=True)
        text = output.getvalue()
        self.assertIn("2 semantic review candidate", text)
        self.assertIn("src/app.py:2", text)
        self.assertIn("1 more candidate", text)
        self.assertIn("Blocking mode is enabled", text)

        with mock.patch.dict(os.environ, {"CLEAN_CODE_AGENT_HOOK_PYLINT": "yes"}):
            self.assertTrue(hook.include_pylint())
        with mock.patch.dict(os.environ, {"CLEAN_CODE_AGENT_HOOK_PYLINT": "0"}):
            self.assertFalse(hook.include_pylint())

    def test_main_uses_changed_files_and_blocks_in_blocking_mode(self) -> None:
        original_argv = sys.argv
        original_repo_root = hook.repo_root
        original_changed_files = hook.changed_files
        original_eslint = hook.eslint_findings
        original_ruff = hook.ruff_findings
        original_pylint = hook.pylint_findings
        original_include_pylint = hook.include_pylint
        calls: dict[str, object] = {}

        def current_repo_root() -> Path:
            return Path.cwd()

        def fake_eslint_findings(_repo: Path, **kwargs: Any) -> list[object]:
            calls["eslint_files"] = kwargs["files"]
            return []

        def fake_ruff_findings(_repo: Path, **kwargs: Any) -> list[object]:
            calls["ruff_files"] = kwargs["files"]
            return []

        def fake_pylint_findings(_repo: Path, **_kwargs: Any) -> list[object]:
            return [hook.Finding("pylint", "too-many-branches", "src/app.py", 1, "branchy", "query")]

        hook.repo_root = current_repo_root
        hook.changed_files = lambda _repo, base: ["src/app.ts", "src/app.py"] if base == "origin/main" else []
        hook.eslint_findings = fake_eslint_findings
        hook.ruff_findings = fake_ruff_findings
        hook.pylint_findings = fake_pylint_findings
        hook.include_pylint = lambda: True
        sys.argv = [
            "hook",
            "--hook",
            "pre-push",
            "--mode",
            "blocking",
            "--changed-since",
            "origin/main",
        ]
        try:
            with self.assertRaises(SystemExit):
                hook.main()
        finally:
            sys.argv = original_argv
            hook.repo_root = original_repo_root
            hook.changed_files = original_changed_files
            hook.eslint_findings = original_eslint
            hook.ruff_findings = original_ruff
            hook.pylint_findings = original_pylint
            hook.include_pylint = original_include_pylint

        self.assertEqual(calls["eslint_files"], ["src/app.ts", "src/app.py"])
        self.assertEqual(calls["ruff_files"], ["src/app.ts", "src/app.py"])


if __name__ == "__main__":
    unittest.main()
