from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
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


class InstallCodexSkillTest(unittest.TestCase):
    def test_default_dest_root_uses_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex"
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
                self.assertEqual(installer.default_dest_root("codex"), codex_home / "skills")

    def test_default_dest_root_supports_claude(self) -> None:
        self.assertEqual(installer.default_dest_root("claude"), Path.home() / ".claude" / "skills")

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
