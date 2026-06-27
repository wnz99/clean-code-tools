#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

MAX_SEARCH_LIMIT = 25


def load_semantic_module() -> Any:
    module_name = "clean_code_mcp_semantic"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    module_path = Path(__file__).with_name("semantic.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load semantic module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


semantic = load_semantic_module()
COLLECTION_NAME = semantic.COLLECTION_NAME
DEFAULT_EMBEDDING_MODEL = semantic.DEFAULT_EMBEDDING_MODEL
DEFAULT_WEAVIATE_URL = semantic.DEFAULT_WEAVIATE_URL
build_chunks = semantic.build_chunks
create_schema_payload = semantic.create_schema_payload
get_pattern_record = semantic.get_pattern_record
search_pattern_records = semantic.search_pattern_records
search_chunks = semantic.search_chunks


try:
    from fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised by CLI users without deps
    raise SystemExit(
        "Install FastMCP to run the server: python3 -m pip install 'fastmcp>=2.0.0'"
    ) from exc


mcp = FastMCP("clean-code-tools")


@mcp.resource("clean-code://corpus/summary")
def corpus_summary() -> str:
    """Return a compact summary of the local clean-code semantic corpus."""

    chunks = build_chunks()
    by_kind: dict[str, int] = {}
    for chunk in chunks:
        by_kind[chunk.chunk_kind] = by_kind.get(chunk.chunk_kind, 0) + 1
    return json.dumps(
        {
            "chunks": len(chunks),
            "by_kind": by_kind,
            "default_collection": COLLECTION_NAME,
            "default_embedding_model": DEFAULT_EMBEDDING_MODEL,
        },
        sort_keys=True,
    )


@mcp.resource("clean-code://weaviate/schema")
def weaviate_schema() -> str:
    """Return the Weaviate schema payload used by the ingest script."""

    return json.dumps(create_schema_payload(), sort_keys=True, indent=2)


@mcp.resource("clean-code://patterns/{pattern_id}")
def clean_code_pattern_resource(pattern_id: str) -> str:
    """Return one canonical clean-code pattern by ID."""

    return json.dumps(pattern_by_id(pattern_id), sort_keys=True, indent=2)


@mcp.tool
def clean_code_corpus_summary() -> dict[str, Any]:
    """Return chunk counts for the local clean-code corpus."""

    return json.loads(corpus_summary())


@mcp.tool
def clean_code_weaviate_schema() -> dict[str, Any]:
    """Return the Weaviate collection schema used for clean-code search."""

    return create_schema_payload()


@mcp.tool
def search_clean_code(
    query: str,
    limit: int = 8,
    weaviate_url: str = DEFAULT_WEAVIATE_URL,
    collection: str = COLLECTION_NAME,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[dict[str, Any]]:
    """Search the local Weaviate clean-code collection.

    Requires a running Weaviate instance populated with
    `scripts/weaviate_ingest_clean_code.py --reset`.
    """

    if not query.strip():
        raise ValueError("query must not be empty")
    if limit < 1 or limit > MAX_SEARCH_LIMIT:
        raise ValueError("limit must be between 1 and 25")
    rows = search_chunks(
        query=query,
        url=weaviate_url,
        collection_name=collection,
        model_name=model,
        limit=limit,
    )
    return [search_result(row) for row in rows]


@mcp.tool
# pylint: disable-next=too-many-arguments
def search_clean_code_patterns(
    query: str,
    limit: int = 8,
    language: str = "any",
    rule_families: list[str] | None = None,
    topics: list[str] | None = None,
    lintability: list[str] | None = None,
    source_kinds: list[str] | None = None,
    weaviate_url: str = DEFAULT_WEAVIATE_URL,
    collection: str = COLLECTION_NAME,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> dict[str, Any]:
    """Find canonical clean-code patterns relevant to a concrete code concern."""

    if not query.strip():
        raise ValueError("query must not be empty")
    if limit < 1 or limit > MAX_SEARCH_LIMIT:
        raise ValueError("limit must be between 1 and 25")
    return search_pattern_records(
        query=query,
        url=weaviate_url,
        collection_name=collection,
        model_name=model,
        limit=limit,
        language=language,
        rule_families=tuple(rule_families or ()),
        topics=tuple(topics or ()),
        lintability=tuple(lintability or ()),
        source_kinds=tuple(source_kinds or ("clean_code_pattern",)),
    )


@mcp.tool
def get_clean_code_pattern(pattern_id: str) -> dict[str, Any]:
    """Return the full canonical clean-code pattern record for a `CC-###` ID."""

    return pattern_by_id(pattern_id)


@mcp.tool
# pylint: disable-next=too-many-arguments
def recommend_clean_code_lint_rules(
    query: str,
    language: str = "any",
    targets: list[str] | None = None,
    limit: int = 8,
    weaviate_url: str = DEFAULT_WEAVIATE_URL,
    collection: str = COLLECTION_NAME,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> dict[str, Any]:
    """Recommend lint-rule candidates for repeated clean-code concerns."""

    search_payload = search_clean_code_patterns(
        query=query,
        limit=limit,
        language=language,
        lintability=["high", "medium"],
        source_kinds=["clean_code_pattern"],
        weaviate_url=weaviate_url,
        collection=collection,
        model=model,
    )
    requested_targets = targets or default_lint_targets(language)
    if search_payload["no_strong_match"]:
        return {
            "query": query,
            "language": language,
            "targets": requested_targets,
            "results": [],
            "no_strong_match": True,
            "no_recommendation": "No high-confidence lint-rule candidate matched this query.",
        }
    return {
        "query": query,
        "language": language,
        "targets": requested_targets,
        "results": [lint_rule_recommendation(result, requested_targets) for result in search_payload["results"]],
        "no_strong_match": search_payload["no_strong_match"],
    }


@mcp.tool
def list_clean_code_facets() -> dict[str, Any]:
    """Return available filter facets for clean-code pattern search."""

    chunks = build_chunks()
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


def pattern_by_id(pattern_id: str) -> dict[str, Any]:
    normalized = pattern_id.strip().upper()
    if not semantic.CC_ID_RE.fullmatch(normalized):
        raise ValueError("pattern_id must use the CC-### format")
    record = get_pattern_record(normalized)
    if record is None:
        raise ValueError(f"pattern not found: {normalized}")
    return record


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


def increment(counter: dict[str, int], value: str) -> None:
    if value:
        counter[value] = counter.get(value, 0) + 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the clean-code FastMCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse"),
        default="stdio",
        help="FastMCP transport to run.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.transport == "stdio":
        mcp.run()
        return
    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
