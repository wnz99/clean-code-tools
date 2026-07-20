#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from clean_code_eslint_triggers import ESLINT_TRIGGERS
from clean_code_python_triggers import PYLINT_TRIGGERS, RUFF_TRIGGERS
from clean_code_review_io import load_json_file, run_json_command
from clean_code_review_models import LintTrigger, ReviewCandidate, TriggerInput, TriggerRule

ROOT = Path(__file__).resolve().parents[1]
JsonDict = dict[str, Any]


def eslint_candidates(results: list[JsonDict]) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []
    for result in results:
        file_path = result.get("filePath")
        if not isinstance(file_path, str):
            continue
        for message in result.get("messages", []):
            if not isinstance(message, dict):
                continue
            rule_id = message.get("ruleId")
            if not isinstance(rule_id, str) or rule_id not in ESLINT_TRIGGERS:
                continue
            candidates.append(
                review_candidate(
                    TriggerInput(
                        language="typescript",
                        file=file_path,
                        symbol=None,
                        anchor=line_anchor(optional_int(message.get("line"))),
                        tool="eslint",
                        rule=rule_id,
                        message=str(message.get("message", "")),
                        line=optional_int(message.get("line")),
                        column=optional_int(message.get("column")),
                    ),
                    trigger_rule=ESLINT_TRIGGERS[rule_id],
                )
            )
    return candidates


def ruff_candidates(messages: list[JsonDict]) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []
    for message in messages:
        code = message.get("code")
        if not isinstance(code, str) or code not in RUFF_TRIGGERS:
            continue
        location = message.get("location", {})
        if not isinstance(location, dict):
            location = {}
        row = optional_int(location.get("row"))
        candidates.append(
            review_candidate(
                TriggerInput(
                    language="python",
                    file=str(message.get("filename", "")),
                    symbol=None,
                    anchor=line_anchor(row),
                    tool="ruff",
                    rule=code,
                    message=str(message.get("message", "")),
                    line=row,
                    column=optional_int(location.get("column")),
                ),
                trigger_rule=RUFF_TRIGGERS[code],
            )
        )
    return candidates


def pylint_candidates(messages: list[JsonDict]) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []
    for message in messages:
        symbol = message.get("symbol")
        if not isinstance(symbol, str) or symbol not in PYLINT_TRIGGERS:
            continue
        candidates.append(
            review_candidate(
                TriggerInput(
                    language="python",
                    file=str(message.get("path", "")),
                    symbol=optional_str(message.get("obj")),
                    anchor=line_anchor(optional_int(message.get("line"))),
                    tool="pylint",
                    rule=symbol,
                    message=str(message.get("message", "")),
                    line=optional_int(message.get("line")),
                    column=optional_int(message.get("column")),
                ),
                trigger_rule=PYLINT_TRIGGERS[symbol],
            )
        )
    return candidates


def optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def line_anchor(line: int | None) -> str | None:
    if line is None:
        return None
    return f"line {line}"


def review_candidate(
    trigger_input: TriggerInput,
    *,
    trigger_rule: TriggerRule,
) -> ReviewCandidate:
    return ReviewCandidate(
        language=trigger_input.language,
        file=normalize_file(trigger_input.file),
        symbol=trigger_input.symbol,
        anchor=trigger_input.anchor,
        skill="clean-code-tools",
        triggers=(
            LintTrigger(
                tool=trigger_input.tool,
                rule=trigger_input.rule,
                message=trigger_input.message,
                line=trigger_input.line,
                column=trigger_input.column,
            ),
        ),
        semantic_questions=trigger_rule.questions,
        mcp_queries=(trigger_rule.mcp_query,),
    )


def normalize_file(path: str) -> str:
    if not path:
        return path
    raw_path = Path(path)
    try:
        return str(raw_path.resolve().relative_to(ROOT))
    except ValueError:
        return path


def merge_candidates(candidates: list[ReviewCandidate]) -> list[ReviewCandidate]:
    grouped: dict[tuple[str, str, str | None, str | None, str], list[ReviewCandidate]] = {}
    for candidate in candidates:
        key = (
            candidate.language,
            candidate.file,
            candidate.symbol,
            candidate.anchor,
            candidate.skill,
        )
        grouped.setdefault(key, []).append(candidate)

    merged: list[ReviewCandidate] = []
    for (language, file, symbol, anchor, skill), group in grouped.items():
        triggers = tuple(trigger for candidate in group for trigger in candidate.triggers)
        questions = unique_items(
            question for candidate in group for question in candidate.semantic_questions
        )
        queries = unique_items(query for candidate in group for query in candidate.mcp_queries)
        merged.append(
            ReviewCandidate(
                language=language,
                file=file,
                symbol=symbol,
                anchor=anchor,
                skill=skill,
                triggers=triggers,
                semantic_questions=questions,
                mcp_queries=queries,
            )
        )
    return sorted(merged, key=candidate_sort_key)


def candidate_sort_key(candidate: ReviewCandidate) -> tuple[str, str, int]:
    first_line = min(
        (trigger.line for trigger in candidate.triggers if trigger.line is not None),
        default=0,
    )
    return (candidate.file, candidate.symbol or candidate.anchor or "", first_line)


def unique_items(items: Any) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return tuple(unique)


def candidates_from_sources(args: argparse.Namespace) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []
    if args.eslint_json:
        candidates.extend(eslint_candidates(load_json_file(args.eslint_json)))
    if args.eslint_command:
        candidates.extend(eslint_candidates(run_json_command(args.eslint_command)))
    if args.pylint_json:
        candidates.extend(pylint_candidates(load_json_file(args.pylint_json)))
    if args.pylint_command:
        candidates.extend(pylint_candidates(run_json_command(args.pylint_command)))
    if args.ruff_json:
        candidates.extend(ruff_candidates(load_json_file(args.ruff_json)))
    if args.ruff_command:
        candidates.extend(ruff_candidates(run_json_command(args.ruff_command)))
    return merge_candidates(candidates)


def candidate_payload(candidates: list[ReviewCandidate]) -> JsonDict:
    return {
        "schema": "clean-code-review-candidates/v1",
        "candidate_count": len(candidates),
        "candidates": [asdict(candidate) for candidate in candidates],
    }


def markdown_payload(candidates: list[ReviewCandidate]) -> str:
    if not candidates:
        return "No clean-code semantic review candidates found.\n"

    lines = ["# Clean-Code Semantic Review Candidates", ""]
    for candidate in candidates:
        location = candidate.file
        if candidate.symbol:
            location = f"{location}::{candidate.symbol}"
        elif candidate.anchor:
            location = f"{location}::{candidate.anchor}"
        lines.extend(
            [
                f"## {location}",
                "",
                f"- language: `{candidate.language}`",
                f"- skill: `{candidate.skill}`",
                "- triggers:",
            ]
        )
        for trigger in candidate.triggers:
            line = f"  - `{trigger.tool}/{trigger.rule}`"
            if trigger.line is not None:
                line = f"{line} at line {trigger.line}"
            if trigger.message:
                line = f"{line}: {trigger.message}"
            lines.append(line)
        lines.append("- semantic questions:")
        for question in candidate.semantic_questions:
            lines.extend([f"  - {question}"])
        lines.append("- MCP queries:")
        for query in candidate.mcp_queries:
            lines.extend([f"  - `{query}`"])
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert deterministic lint findings into clean-code semantic review candidates."
    )
    parser.add_argument("--eslint-json", type=Path)
    parser.add_argument("--eslint-command")
    parser.add_argument("--pylint-json", type=Path)
    parser.add_argument("--pylint-command")
    parser.add_argument("--ruff-json", type=Path)
    parser.add_argument("--ruff-command")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = candidates_from_sources(args)
    if args.format == "markdown":
        print(markdown_payload(candidates))
    else:
        print(json.dumps(candidate_payload(candidates), indent=2))


if __name__ == "__main__":
    main()
