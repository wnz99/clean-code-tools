from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = REPO_ROOT / "skills" / "clean-code-mcp-reviewer" / "SKILL.md"
README = REPO_ROOT / "README.md"


class SkillDocsTest(unittest.TestCase):
    def test_installation_plan_template_is_documented_in_skill(self) -> None:
        content = SKILL_MD.read_text()

        required_fragments = [
            "## Clean-Code Installation Plan",
            "### Decision",
            "### Evidence",
            "### Phase 1: Shared Tooling",
            "### Phase 2: Targeted Rollout",
            "### Deferred Or Skipped",
            "### Rollback",
            "### Open Questions",
            "If root dry-run says `status: safe to apply`",
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, content)

    def test_readme_tells_agents_to_return_installation_plan(self) -> None:
        content = README.read_text()

        self.assertIn("Clean-Code Installation Plan", content)
        self.assertIn("exact apply commands", content)
        self.assertIn("rollback", content)


if __name__ == "__main__":
    unittest.main()
