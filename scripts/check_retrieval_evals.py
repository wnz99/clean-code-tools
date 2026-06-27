#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _mcp_app import load_semantic_module

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals" / "clean-code-retrieval.jsonl"


def main() -> None:
    semantic = load_semantic_module()
    cases = [json.loads(line) for line in EVALS.read_text().splitlines() if line.strip()]
    failures: list[str] = []
    metrics = empty_metrics()
    for case in cases:
        payload = local_search_payload(semantic, case)
        failures.extend(evaluate_case(case, payload, metrics))
    failures.extend(production_ranking_checks(semantic))

    if failures:
        raise SystemExit("\n".join(failures))
    print(
        "retrieval_eval_check=ok "
        f"cases={len(cases)} "
        f"top1={metrics['top1_correct']} "
        f"top5={metrics['top5_recall']} "
        f"strong_calibration={metrics['strong_calibration']} "
        f"duplicate_failures={metrics['duplicate_failures']} "
        f"markdown_pollution={metrics['markdown_pollution']}"
    )


def local_search_payload(semantic: Any, case: dict[str, Any]) -> dict[str, Any]:
    return semantic.rank_pattern_rows(
        query=str(case["query"]),
        vector_rows=mock_vector_rows(semantic, case),
        limit=8,
        language=str(case.get("language", "any")),
        source_kinds=("clean_code_pattern",),
    )


def mock_vector_rows(semantic: Any, case: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = {
        chunk.record_id: chunk
        for chunk in semantic.build_chunks()
        if chunk.chunk_kind == "pattern_record"
    }
    rows: list[dict[str, Any]] = []
    for index, pattern_id in enumerate(case.get("vector_ids", [])):
        chunk = chunks.get(pattern_id)
        if chunk is not None:
            rows.append(chunk.properties | {"_additional": {"id": chunk.object_id, "distance": 0.20 + index * 0.05}})
    return rows


def empty_metrics() -> dict[str, int]:
    return {
        "top1_correct": 0,
        "top5_recall": 0,
        "strong_calibration": 0,
        "duplicate_failures": 0,
        "markdown_pollution": 0,
    }


def evaluate_case(
    case: dict[str, Any],
    payload: dict[str, Any],
    metrics: dict[str, int],
) -> list[str]:
    results = payload["results"][:5]
    ids = [str(result["pattern_id"]) for result in results]
    expected = set(case["expected_top_ids"])
    failures: list[str] = []

    if expected and ids[:1] and ids[0] in expected:
        metrics["top1_correct"] += 1
    if not expected or expected & set(ids):
        metrics["top5_recall"] += 1
    if bool(case["should_strong_match"]) != bool(payload["no_strong_match"]):
        metrics["strong_calibration"] += 1
    if len(ids) != len(set(ids)):
        metrics["duplicate_failures"] += 1
        failures.append(f"{case['id']}: duplicate pattern IDs in top 5: {ids}")
    if any(result.get("source_kind") != "clean_code_pattern" for result in results):
        metrics["markdown_pollution"] += 1

    if case["should_strong_match"]:
        if not expected & set(ids[:3]):
            failures.append(f"{case['id']}: expected one of {sorted(expected)} in top 3, got {ids[:3]}")
        if payload["no_strong_match"]:
            failures.append(f"{case['id']}: expected strong match")
    elif not payload["no_strong_match"]:
        failures.append(f"{case['id']}: expected no_strong_match")
    if expected and not case["should_strong_match"] and not expected & set(ids):
        failures.append(f"{case['id']}: expected relevant pattern {sorted(expected)} in top 5, got {ids}")
    return failures


def production_ranking_checks(semantic: Any) -> list[str]:
    chunks = {chunk.chunk_id: chunk for chunk in semantic.build_chunks()}
    pattern = chunks["pattern:CC-043"]
    markdown = next(chunk for chunk in chunks.values() if chunk.source_kind == "markdown_doc")
    payload = semantic.rank_pattern_rows(
        query="typescript boolean flag argument",
        vector_rows=[
            markdown.properties | {"_additional": {"id": markdown.object_id, "distance": 0.01}},
            pattern.properties | {"_additional": {"id": pattern.object_id, "distance": 0.40}},
            pattern.properties | {"_additional": {"id": pattern.object_id, "distance": 0.10}},
        ],
        limit=5,
        language="typescript",
        source_kinds=("clean_code_pattern",),
    )
    ids = [result["pattern_id"] for result in payload["results"]]
    failures: list[str] = []
    if ids.count("CC-043") != 1:
        failures.append(f"production-ranking: expected deduped CC-043 once, got {ids}")
    if payload["results"][0]["source_kind"] != "clean_code_pattern":
        failures.append("production-ranking: markdown vector row was not filtered out")
    if payload["results"][0]["distance"] != 0.1:
        failures.append(f"production-ranking: expected best vector distance 0.1, got {payload['results'][0]['distance']}")
    return failures


if __name__ == "__main__":
    main()
