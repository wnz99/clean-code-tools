#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from typing import Any, cast

from _mcp_app import load_server_module


async def main() -> None:
    try:
        from fastmcp import Client
    except ImportError as exc:
        raise SystemExit(
            "Install FastMCP to run this check: python3 -m pip install 'fastmcp>=2.0.0'"
        ) from exc

    mcp_server = cast(Any, load_server_module())

    def fake_search_pattern_records(**_: object) -> dict[str, object]:
        return {
            "query": "stub",
            "filters_applied": {},
            "no_strong_match": False,
            "results": [
                {
                    "pattern_id": "CC-043",
                    "chunk_id": "pattern:CC-043",
                    "title": "Flag Arguments",
                    "topic": "Chapter 3: Functions",
                    "rule_family": "functions",
                    "lintability": "high",
                    "languages": ["typescript", "python"],
                    "aliases": ["flag argument", "boolean parameter"],
                    "lint_candidates": ["Replace boolean modes with named functions."],
                    "source_kind": "clean_code_pattern",
                    "chunk_kind": "pattern_record",
                    "score": 0.91,
                    "confidence": "high",
                    "distance": 0.09,
                    "match_reasons": ["matched exact terms: flag argument"],
                }
            ],
        }

    mcp_server.search_pattern_records = fake_search_pattern_records

    async with Client(mcp_server.mcp) as client:
        tools = await client.list_tools()
        tool_names = {tool.name for tool in tools}
        assert {
            "clean_code_corpus_summary",
            "clean_code_weaviate_schema",
            "search_clean_code",
            "search_clean_code_patterns",
            "get_clean_code_pattern",
            "recommend_clean_code_lint_rules",
            "list_clean_code_facets",
            "validate_clean_code_pattern",
            "upsert_clean_code_pattern",
            "delete_custom_clean_code_pattern",
            "list_custom_clean_code_patterns",
        } <= tool_names

        resources = await client.list_resources()
        resource_uris = {str(resource.uri) for resource in resources}
        assert "clean-code://corpus/summary" in resource_uris
        assert "clean-code://weaviate/schema" in resource_uris

        summary = await client.call_tool("clean_code_corpus_summary", {})
        summary_data = summary.data
        assert summary_data["chunks"] >= 300
        assert summary_data["by_kind"]["pattern_record"] == 264

        schema = await client.call_tool("clean_code_weaviate_schema", {})
        schema_data = schema.data
        assert schema_data["class"] == "CleanCodeChunks"
        assert schema_data["vectorConfig"]["content"]["vectorizer"] == {"none": {}}

        pattern = await client.call_tool("get_clean_code_pattern", {"pattern_id": "CC-043"})
        pattern_data = pattern.data
        assert pattern_data["id"] == "CC-043"
        assert "flag argument" in " ".join(pattern_data["aliases"])

        facets = await client.call_tool("list_clean_code_facets", {})
        facet_data = facets.data
        assert facet_data["rule_families"]["functions"] >= 1
        assert facet_data["languages"]["typescript"] >= 1

        search = await client.call_tool(
            "search_clean_code_patterns",
            {"query": "typescript boolean flag argument", "language": "typescript"},
        )
        search_data = search.data
        assert search_data["results"][0]["pattern_id"] == "CC-043"
        assert search_data["no_strong_match"] is False

        recommendations = await client.call_tool(
            "recommend_clean_code_lint_rules",
            {"query": "typescript boolean flag argument", "language": "typescript"},
        )
        recommendation_data = recommendations.data
        assert recommendation_data["results"][0]["pattern_id"] == "CC-043"
        assert recommendation_data["results"][0]["targets"] == ["eslint", "semgrep"]

    print("fastmcp_server_check=ok")


if __name__ == "__main__":
    asyncio.run(main())
