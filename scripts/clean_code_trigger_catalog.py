from __future__ import annotations

import json
from pathlib import Path

from clean_code_review_models import TriggerRule

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = (
    ROOT
    / "skills"
    / "clean-code-mcp-reviewer"
    / "catalog"
    / "clean_code_review_triggers.json"
)


def load_trigger_catalog(path: Path = CATALOG_PATH) -> dict[str, dict[str, TriggerRule]]:
    payload = json.loads(path.read_text())
    return {
        section: {
            rule_id: TriggerRule(
                questions=tuple(str(item) for item in rule_payload["questions"]),
                mcp_query=str(rule_payload["mcp_query"]),
            )
            for rule_id, rule_payload in rules.items()
        }
        for section, rules in payload.items()
        if section != "schema"
    }
