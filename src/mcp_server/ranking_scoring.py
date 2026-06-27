#!/usr/bin/env python3
from __future__ import annotations

from src.mcp_server.models import Confidence, JsonDict
from src.mcp_server.text import (
    lexical_score,
    query_tokens,
    searchable_row_text,
    semantic_similarity,
)
from src.mcp_server.utils.unique_strings import unique_strings

CONSERVATIVE_CONTEXT_THRESHOLD = 0.80
HIGH_CONFIDENCE_THRESHOLD = 0.72
EXACT_HIGH_CONFIDENCE_THRESHOLD = 0.40
MEDIUM_CONFIDENCE_THRESHOLD = 0.45
EXACT_MATCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "be",
    "by",
    "code",
    "do",
    "for",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "thi",
    "this",
    "to",
    "when",
    "with",
}
NON_SPECIFIC_EXACT_ALIASES = {
    "clean code",
    "code smell",
    "comments",
    "error handling",
    "function smell",
    "functions",
    "function design",
    "planning guidance",
    "refactoring rule",
}
BROAD_CATEGORY_QUERY_TERMS = {
    "clean",
    "code",
    "comment",
    "comments",
    "error",
    "function",
    "handling",
    "guidance",
    "planning",
    "python",
    "refactoring",
    "rule",
    "smell",
    "typescript",
}
VAGUE_QUERY_TERMS = {"stuff", "thing", "things"}


def row_matches_filters(row: JsonDict, filters: JsonDict) -> bool:
    source_kinds = tuple(str(value) for value in filters["source_kinds"])
    if source_kinds and str(row.get("sourceKind", "")) not in source_kinds:
        return False

    language = str(filters["language"])
    languages = tuple(str(value) for value in row.get("languages", []))
    if language not in {"", "any", "both"} and language not in languages:
        return False
    if language == "both" and not {"typescript", "python"} <= set(languages):
        return False

    rule_families = {str(value) for value in filters["rule_families"]}
    if rule_families and str(row.get("ruleFamily", "")) not in rule_families:
        return False

    topics = {str(value) for value in filters["topics"]}
    if topics and str(row.get("topic", "")) not in topics:
        return False

    lintability = {str(value) for value in filters["lintability"]}
    return not lintability or str(row.get("lintability", "")) in lintability


def score_pattern_row(row: JsonDict, *, query: str, filters: JsonDict) -> JsonDict:
    query_terms = set(query_tokens(query))
    distance = distance_for(row)
    semantic_score = semantic_similarity(distance)
    keyword_score = lexical_score(query_terms, searchable_row_text(row))
    metadata_boost, match_reasons = metadata_boost_and_reasons(row, filters, query_terms)
    context_penalty, context_reasons = context_penalty_and_reasons(query_terms)
    match_reasons.extend(context_reasons)
    score = max(0.0, min(1.0, semantic_score * 0.60 + keyword_score * 0.25 + metadata_boost - context_penalty))
    confidence = confidence_for(score, match_reasons, semantic_score=semantic_score)
    return {
        "pattern_id": row.get("recordId", ""),
        "chunk_id": row.get("chunkId", ""),
        "title": row.get("title", ""),
        "topic": row.get("topic", ""),
        "rule_family": row.get("ruleFamily", ""),
        "lintability": row.get("lintability", ""),
        "languages": row.get("languages", []),
        "aliases": row.get("aliases", []),
        "lint_candidates": row.get("lintCandidates", []),
        "source_kind": row.get("sourceKind", ""),
        "chunk_kind": row.get("chunkKind", ""),
        "section_path": row.get("sectionPath", []),
        "score": round(score, 4),
        "confidence": confidence,
        "distance": distance,
        "match_reasons": match_reasons,
        "snippet": " ".join(str(row.get("contentText", "")).split())[:500],
        "source": {
            "source_file": row.get("sourceFile", ""),
            "source_kind": row.get("sourceKind", ""),
            "text_hash": row.get("textHash", ""),
        },
        "score_breakdown": {
            "semantic_score": round(semantic_score, 4),
            "keyword_score": round(keyword_score, 4),
            "metadata_boost": round(metadata_boost, 4),
            "context_penalty": round(context_penalty, 4),
        },
    }


def dedupe_pattern_results(rows: list[JsonDict]) -> list[JsonDict]:
    by_record_id: dict[str, JsonDict] = {}
    for row in rows:
        record_id = str(row.get("pattern_id") or row.get("chunk_id"))
        if record_id not in by_record_id or float(row["score"]) > float(by_record_id[record_id]["score"]):
            by_record_id[record_id] = row
    return sorted(by_record_id.values(), key=lambda item: float(item["score"]), reverse=True)


def metadata_boost_and_reasons(
    row: JsonDict,
    filters: JsonDict,
    query_terms: set[str],
) -> tuple[float, list[str]]:
    boost = 0.0
    reasons: list[str] = []
    source_kind = str(row.get("sourceKind", ""))
    if source_kind == "clean_code_pattern":
        boost += 0.05
        reasons.append("canonical clean-code pattern")

    language = str(filters["language"])
    languages = {str(value) for value in row.get("languages", [])}
    if language not in {"", "any"} and (language == "both" or language in languages):
        boost += 0.05
        reasons.append(f"language matched: {language}")

    lintability = str(row.get("lintability", ""))
    if lintability and lintability in set(filters["lintability"]):
        boost += 0.05
        reasons.append(f"lintability matched: {lintability}")

    exact_terms = exact_match_terms(row, query_terms)
    if exact_terms:
        boost += 0.15
        reasons.append(f"matched exact terms: {', '.join(exact_terms[:4])}")

    if not reasons:
        reasons.append("semantic similarity")
    return min(boost, 0.30), reasons


def context_penalty_and_reasons(query_terms: set[str]) -> tuple[float, list[str]]:
    safe_context_terms = {"generated", "fixture", "fixtures", "test", "tests"}
    matched = sorted(query_terms & safe_context_terms)
    reasons: list[str] = []
    if matched:
        reasons.append(f"conservative context: {', '.join(matched)}")
    meaningful_terms = query_terms - EXACT_MATCH_STOPWORDS
    if meaningful_terms and meaningful_terms <= BROAD_CATEGORY_QUERY_TERMS:
        reasons.append("conservative context: broad category query")
    if meaningful_terms and meaningful_terms <= VAGUE_QUERY_TERMS:
        reasons.append("conservative context: vague query")
    if {"todo", "tracked", "issue"} <= query_terms:
        reasons.append("conservative context: compliant tracked TODO")
    if not reasons:
        return 0.0, []
    return 0.35, reasons


def exact_match_terms(row: JsonDict, query_terms: set[str]) -> list[str]:
    values = [
        str(row.get("recordId", "")),
        str(row.get("title", "")),
        *[str(value) for value in row.get("aliases", [])],
        *[str(value) for value in row.get("lintCandidates", [])],
    ]
    matched: list[str] = []
    for value in values:
        normalized_value = " ".join(query_tokens(value))
        if normalized_value in NON_SPECIFIC_EXACT_ALIASES:
            continue
        terms = set(query_tokens(value))
        meaningful_terms = terms - EXACT_MATCH_STOPWORDS
        if terms and meaningful_terms and terms <= query_terms:
            matched.append(value)
    return unique_strings(matched)


def distance_for(row: JsonDict) -> float | None:
    additional = row.get("_additional")
    if not isinstance(additional, dict):
        return None
    distance = additional.get("distance")
    return float(distance) if isinstance(distance, int | float) else None


def confidence_for(score: float, match_reasons: list[str], *, semantic_score: float) -> Confidence:
    if any(reason.startswith("conservative context") for reason in match_reasons):
        return "low" if score < CONSERVATIVE_CONTEXT_THRESHOLD else "medium"
    has_exact = any(reason.startswith("matched exact terms") for reason in match_reasons)
    if score >= HIGH_CONFIDENCE_THRESHOLD or (
        has_exact and semantic_score > 0 and score >= EXACT_HIGH_CONFIDENCE_THRESHOLD
    ):
        return "high"
    if score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"
