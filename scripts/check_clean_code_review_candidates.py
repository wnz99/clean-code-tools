#!/usr/bin/env python3
from __future__ import annotations

import re
import tomllib
from pathlib import Path

from clean_code_eslint_triggers import ESLINT_TRIGGERS
from clean_code_python_triggers import PYLINT_TRIGGERS, RUFF_TRIGGERS
from clean_code_review_candidates import (
    candidate_payload,
    eslint_candidates,
    markdown_payload,
    merge_candidates,
    pylint_candidates,
    ruff_candidates,
)

ROOT = Path(__file__).resolve().parents[1]
ESLINT_CONFIG = ROOT / "configs/eslint.clean-code.recommended.mjs"
PYTHON_CONFIG = ROOT / "configs/python.clean-code.pyproject.toml"
REPO_PYTHON_CONFIG = ROOT / "pyproject.toml"

EXPECTED_ESLINT_TRIGGERS = {
    "@typescript-eslint/consistent-type-imports",
    "@typescript-eslint/naming-convention",
    "@typescript-eslint/no-confusing-void-expression",
    "@typescript-eslint/no-magic-numbers",
    "@typescript-eslint/no-unnecessary-condition",
    "@typescript-eslint/no-unnecessary-type-assertion",
    "@typescript-eslint/no-unused-vars",
    "@typescript-eslint/prefer-nullish-coalescing",
    "@typescript-eslint/strict-boolean-expressions",
    "@typescript-eslint/switch-exhaustiveness-check",
    "clean-code/no-boolean-flag-arguments",
    "clean-code/no-business-policy-literals",
    "clean-code/no-commented-out-code",
    "clean-code/no-noisy-comments",
    "clean-code/no-output-argument-mutation",
    "clean-code/no-redundant-comment",
    "clean-code/no-train-wrecks",
    "clean-code/todo-format",
    "complexity",
    "max-depth",
    "max-lines",
    "max-lines-per-function",
    "max-params",
    "no-empty",
    "no-negated-condition",
    "no-nested-ternary",
    "no-restricted-syntax",
    "no-useless-return",
    "sonarjs/cognitive-complexity",
    "sonarjs/no-dead-store",
    "sonarjs/no-duplicate-string",
    "sonarjs/no-duplicated-branches",
    "sonarjs/no-identical-conditions",
    "sonarjs/no-identical-functions",
    "sonarjs/no-inverted-boolean-check",
    "unicorn/explicit-length-check",
    "unicorn/no-negated-condition",
    "unicorn/no-null",
}

ESLINT_SEMANTIC_EXCLUSIONS = {
    "@typescript-eslint/no-floating-promises",
    "@typescript-eslint/no-misused-promises",
    "eqeqeq",
    "spaced-comment",
}

EXPECTED_PYLINT_TRIGGERS = {
    "clean-code-boolean-flag-argument",
    "clean-code-business-policy-literal",
    "clean-code-commented-out-code",
    "clean-code-noisy-comment",
    "clean-code-output-argument-mutation",
    "clean-code-redundant-comment",
    "clean-code-todo-format",
    "clean-code-train-wreck",
    "cyclic-import",
    "duplicate-code",
    "too-few-public-methods",
    "too-many-ancestors",
    "too-many-arguments",
    "too-many-boolean-expressions",
    "too-many-branches",
    "too-many-instance-attributes",
    "too-many-lines",
    "too-many-locals",
    "too-many-nested-blocks",
    "too-many-public-methods",
    "too-many-return-statements",
    "too-many-statements",
}

PYLINT_SEMANTIC_EXCLUSIONS = {
    "import-error",
}

EXPECTED_RUFF_TRIGGERS = {
    "ARG001",
    "ARG002",
    "ERA001",
    "F401",
    "F841",
    "PLR0911",
    "PLR0912",
    "PLR0913",
    "PLR0914",
    "PLR0915",
    "PLR0916",
    "PLR1702",
    "PLR2004",
    "RET505",
    "RET506",
    "RET507",
    "RET508",
    "SIM102",
    "SIM103",
    "SIM108",
    "TD002",
    "TD003",
}

RUFF_CURATED_SELECT_PREFIXES = {
    "ARG",
    "ERA",
    "F",
    "PLR2004",
    "RET",
    "SIM",
    "TD",
}


def enabled_eslint_rules() -> set[str]:
    source = ESLINT_CONFIG.read_text()
    rule_pattern = re.compile(
        r'^\s*(?:"(?P<quoted>[^"]+)"|(?P<bare>[A-Za-z][\w/-]*)):\s*'
        r'(?:(?P<string>"(?:warn|error)")|\[\s*"(?P<array>warn|error)")',
        re.MULTILINE,
    )
    return {
        match.group("quoted") or match.group("bare")
        for match in rule_pattern.finditer(source)
    }


def python_lint_config(path: Path = PYTHON_CONFIG) -> dict:
    return tomllib.loads(path.read_text())


def enabled_pylint_rules() -> set[str]:
    return set(python_lint_config()["tool"]["pylint"]["messages control"]["enable"])


def selected_ruff_prefixes() -> set[str]:
    return set(python_lint_config()["tool"]["ruff"]["lint"]["select"])


def repo_selected_ruff_prefixes() -> set[str]:
    return set(python_lint_config(REPO_PYTHON_CONFIG)["tool"]["ruff"]["lint"]["select"])


def all_selected_ruff_prefixes() -> set[str]:
    return selected_ruff_prefixes() | repo_selected_ruff_prefixes()


def ruff_code_is_selected(code: str, selected_prefixes: set[str]) -> bool:
    return any(code.startswith(prefix) for prefix in selected_prefixes)


def main() -> None:
    assert set(ESLINT_TRIGGERS) == EXPECTED_ESLINT_TRIGGERS
    assert set(PYLINT_TRIGGERS) == EXPECTED_PYLINT_TRIGGERS
    assert set(RUFF_TRIGGERS) == EXPECTED_RUFF_TRIGGERS
    assert enabled_eslint_rules() <= set(ESLINT_TRIGGERS) | ESLINT_SEMANTIC_EXCLUSIONS
    assert enabled_pylint_rules() <= set(PYLINT_TRIGGERS) | PYLINT_SEMANTIC_EXCLUSIONS
    assert selected_ruff_prefixes() >= RUFF_CURATED_SELECT_PREFIXES
    assert all(ruff_code_is_selected(code, all_selected_ruff_prefixes()) for code in RUFF_TRIGGERS)

    eslint_results = [
        {
            "filePath": "/repo/src/pricing.ts",
            "messages": [
                {
                    "ruleId": "max-lines-per-function",
                    "message": "Function has too many lines.",
                    "line": 12,
                    "column": 1,
                },
                {
                    "ruleId": "clean-code/no-boolean-flag-arguments",
                    "message": "Boolean literal selects behavior.",
                    "line": 44,
                    "column": 22,
                },
                {
                    "ruleId": "semi",
                    "message": "Formatting-only rules are not semantic triggers.",
                    "line": 45,
                    "column": 1,
                },
            ],
        }
    ]
    pylint_results = [
        {
            "path": "sample-apps/python-app/src/smelly_pricing.py",
            "obj": "calculate_total",
            "line": 5,
            "column": 0,
            "symbol": "too-many-arguments",
            "message": "Too many arguments (6/5)",
        },
        {
            "path": "sample-apps/python-app/src/smelly_pricing.py",
            "obj": "calculate_total",
            "line": 7,
            "column": 4,
            "symbol": "clean-code-output-argument-mutation",
            "message": "Avoid mutating parameter 'order' as an output argument.",
        },
        {
            "path": "sample-apps/python-app/src/smelly_pricing.py",
            "obj": "calculate_total",
            "line": 5,
            "column": 0,
            "symbol": "missing-function-docstring",
            "message": "Not part of semantic trigger handoff.",
        },
    ]
    ruff_results = [
        {
            "filename": "sample-apps/python-app/src/smelly_pricing.py",
            "location": {"row": 12, "column": 8},
            "code": "PLR2004",
            "message": "Magic value used in comparison.",
        },
        {
            "filename": "sample-apps/python-app/src/smelly_pricing.py",
            "location": {"row": 18, "column": 5},
            "code": "TD003",
            "message": "Missing issue link for this TODO.",
        },
        {
            "filename": "sample-apps/python-app/src/smelly_pricing.py",
            "location": {"row": 20, "column": 1},
            "code": "E501",
            "message": "Formatting-only rules are not semantic triggers.",
        },
    ]

    candidates = merge_candidates(
        [
            *eslint_candidates(eslint_results),
            *pylint_candidates(pylint_results),
            *ruff_candidates(ruff_results),
        ]
    )
    payload = candidate_payload(candidates)

    assert payload["schema"] == "clean-code-review-candidates/v1"
    assert payload["candidate_count"] == 6

    assert {candidate["skill"] for candidate in payload["candidates"]} == {
        "clean-code-mcp-reviewer"
    }

    typescript_candidates = [
        candidate for candidate in payload["candidates"] if candidate["language"] == "typescript"
    ]
    python_candidates = [
        candidate for candidate in payload["candidates"] if candidate["language"] == "python"
    ]
    assert len(typescript_candidates) == 2
    assert {candidate["anchor"] for candidate in typescript_candidates} == {"line 12", "line 44"}
    assert any(candidate["symbol"] == "calculate_total" for candidate in python_candidates)
    assert any("too many arguments" in candidate["mcp_queries"][0] for candidate in python_candidates)
    assert any(
        trigger["tool"] == "pylint" and trigger["rule"] == "clean-code-output-argument-mutation"
        for candidate in python_candidates
        for trigger in candidate["triggers"]
    )
    assert any(
        trigger["tool"] == "ruff" and trigger["rule"] == "TD003"
        for candidate in python_candidates
        for trigger in candidate["triggers"]
    )

    markdown = markdown_payload(candidates)
    assert "Clean-Code Semantic Review Candidates" in markdown
    assert "clean-code/no-boolean-flag-arguments" in markdown
    assert "calculate_total" in markdown
    assert "ruff/PLR2004" in markdown

    print("clean_code_review_candidates_check=ok")


if __name__ == "__main__":
    main()
