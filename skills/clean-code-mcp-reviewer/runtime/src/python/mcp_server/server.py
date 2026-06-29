#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from mcp_server import semantic
from mcp_server.custom_pattern_tools import (
    delete_custom_clean_code_pattern_payload,
    list_custom_clean_code_pattern_payload,
    upsert_clean_code_pattern_payload,
    validate_clean_code_pattern_payload,
)
from mcp_server.pattern_lookup import pattern_by_id
from mcp_server.server_payloads import (
    default_lint_targets,
    facet_counts,
    lint_rule_recommendation,
    search_result,
)

MAX_SEARCH_LIMIT = 25
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
        source_kinds=tuple(source_kinds or semantic.DEFAULT_PATTERN_SOURCE_KINDS),
    )


@mcp.tool
def get_clean_code_pattern(
    pattern_id: str,
    custom_patterns_path: str | None = None,
) -> dict[str, Any]:
    """Return the full built-in or custom clean-code pattern record."""

    return pattern_by_id(pattern_id, custom_patterns_path=custom_patterns_path)


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

    return facet_counts(build_chunks())


@mcp.tool
def validate_clean_code_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    return validate_clean_code_pattern_payload(pattern)


@mcp.tool
def list_custom_clean_code_patterns(
    custom_patterns_path: str | None = None,
) -> dict[str, Any]:
    return list_custom_clean_code_pattern_payload(custom_patterns_path)


@mcp.tool
# pylint: disable-next=too-many-arguments
def upsert_clean_code_pattern(
    pattern: dict[str, Any],
    custom_patterns_path: str | None = None,
    *,
    sync_weaviate: bool = True,
    weaviate_url: str = DEFAULT_WEAVIATE_URL,
    collection: str = COLLECTION_NAME,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> dict[str, Any]:
    return upsert_clean_code_pattern_payload(
        {
            "pattern": pattern,
            "custom_patterns_path": custom_patterns_path,
            "sync_weaviate": sync_weaviate,
            "weaviate_url": weaviate_url,
            "collection": collection,
            "model": model,
        }
    )


@mcp.tool
def delete_custom_clean_code_pattern(
    pattern_id: str,
    custom_patterns_path: str | None = None,
    *,
    sync_weaviate: bool = True,
    weaviate_url: str = DEFAULT_WEAVIATE_URL,
    collection: str = COLLECTION_NAME,
) -> dict[str, Any]:
    return delete_custom_clean_code_pattern_payload(
        pattern_id,
        custom_patterns_path,
        sync_weaviate=sync_weaviate,
        weaviate_url=weaviate_url,
        collection=collection,
    )


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
