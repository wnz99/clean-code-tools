#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from src.mcp_server.models import CleanCodeChunk
from src.mcp_server.utils.increment import increment


def facet_counts(chunks: list[CleanCodeChunk]) -> dict[str, dict[str, int]]:
    facets: dict[str, dict[str, int]] = {
        "topics": {},
        "rule_families": {},
        "lintability": {},
        "source_kinds": {},
        "languages": {},
        "chunk_kinds": {},
    }
    for chunk in chunks:
        increment(facets["topics"], chunk.topic)
        increment(facets["rule_families"], chunk.rule_family)
        increment(facets["lintability"], chunk.lintability)
        increment(facets["source_kinds"], chunk.source_kind)
        increment(facets["chunk_kinds"], chunk.chunk_kind)
        for language in chunk.languages:
            increment(facets["languages"], language)
    return facets


def search_result(row: dict[str, Any]) -> dict[str, Any]:
    additional = row.get("_additional") or {}
    content = " ".join(str(row.get("contentText", "")).split())
    return {
        "chunk_id": row.get("chunkId", ""),
        "record_id": row.get("recordId", ""),
        "title": row.get("title", ""),
        "topic": row.get("topic", ""),
        "source_file": row.get("sourceFile", ""),
        "source_kind": row.get("sourceKind", ""),
        "rule_family": row.get("ruleFamily", ""),
        "lintability": row.get("lintability", ""),
        "distance": additional.get("distance"),
        "snippet": content[:500],
    }


def lint_rule_recommendation(result: dict[str, Any], targets: list[str]) -> dict[str, Any]:
    return {
        "pattern_id": result["pattern_id"],
        "title": result["title"],
        "rule_family": result["rule_family"],
        "lintability": result["lintability"],
        "confidence": result["confidence"],
        "score": result["score"],
        "targets": targets,
        "static_signals": result.get("lint_candidates", []),
        "false_positive_risks": false_positive_risks(result),
        "suppression_strategy": suppression_strategy(targets),
        "autofix": "review required; only offer autofix for syntax-preserving local rewrites",
        "match_reasons": result.get("match_reasons", []),
    }


def default_lint_targets(language: str) -> list[str]:
    if language == "typescript":
        return ["eslint", "semgrep"]
    if language == "python":
        return ["ruff", "pylint", "semgrep"]
    return ["eslint", "ruff", "pylint", "semgrep"]


def false_positive_risks(result: dict[str, Any]) -> list[str]:
    risks = [
        "local project conventions may intentionally allow this shape",
        "tests, generated files, fixtures, and framework adapters may be safe contexts",
    ]
    if result.get("lintability") == "medium":
        risks.append("medium-lintability patterns need narrower project-specific allowlists")
    return risks


def suppression_strategy(targets: list[str]) -> str:
    return f"use the narrowest inline suppression supported by {', '.join(targets)} and require a reason"
