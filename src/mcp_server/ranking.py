#!/usr/bin/env python3
from __future__ import annotations

from src.mcp_server.corpus import build_chunks
from src.mcp_server.models import DEFAULT_EMBEDDING_MODEL, JsonDict
from src.mcp_server.ranking_scoring import (
    dedupe_pattern_results,
    distance_for,
    row_matches_filters,
    score_pattern_row,
)
from src.mcp_server.text import (
    lexical_score,
    query_tokens,
)
from src.mcp_server.weaviate import COLLECTION_NAME, search_chunks


def search_pattern_records(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-locals
    *,
    query: str,
    url: str,
    collection_name: str = COLLECTION_NAME,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    limit: int = 8,
    language: str = "any",
    rule_families: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    lintability: tuple[str, ...] = (),
    source_kinds: tuple[str, ...] = ("clean_code_pattern",),
) -> JsonDict:
    vector_limit = max(limit * 4, 25)
    vector_rows = search_chunks(
        query=query,
        url=url,
        collection_name=collection_name,
        model_name=model_name,
        limit=vector_limit,
    )
    return rank_pattern_rows(
        query=query,
        vector_rows=vector_rows,
        limit=limit,
        language=language,
        rule_families=rule_families,
        topics=topics,
        lintability=lintability,
        source_kinds=source_kinds,
    )


def rank_pattern_rows(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-locals
    *,
    query: str,
    vector_rows: list[JsonDict],
    limit: int = 8,
    language: str = "any",
    rule_families: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    lintability: tuple[str, ...] = (),
    source_kinds: tuple[str, ...] = ("clean_code_pattern",),
) -> JsonDict:
    rows_by_chunk_id: dict[str, JsonDict] = {}
    for row in [*vector_rows, *local_keyword_rows(query)]:
        chunk_id = str(row.get("chunkId", ""))
        if chunk_id:
            rows_by_chunk_id[chunk_id] = merge_search_rows(rows_by_chunk_id.get(chunk_id), row)

    filters = {
        "language": language,
        "rule_families": rule_families,
        "topics": topics,
        "lintability": lintability,
        "source_kinds": source_kinds,
    }
    ranked: list[JsonDict] = []
    for row in rows_by_chunk_id.values():
        if not row_matches_filters(row, filters):
            continue
        ranked.append(score_pattern_row(row, query=query, filters=filters))

    ranked.sort(key=lambda item: float(item["score"]), reverse=True)
    deduped = dedupe_pattern_results(ranked)
    results = deduped[:limit]
    return {
        "query": query,
        "filters_applied": filters,
        "results": results,
        "no_strong_match": not results or results[0]["confidence"] != "high",
    }


def local_keyword_rows(query: str) -> list[JsonDict]:
    query_terms = set(query_tokens(query))
    if not query_terms:
        return []
    matches: list[JsonDict] = []
    for chunk in build_chunks():
        haystack = " ".join(
            (
                chunk.record_id,
                chunk.title,
                chunk.topic,
                chunk.rule_family,
                chunk.lintability,
                " ".join(chunk.aliases),
                " ".join(chunk.lint_candidates),
                chunk.content_text[:600],
            )
        )
        if lexical_score(query_terms, haystack) > 0:
            matches.append(chunk.properties | {"_additional": {"id": chunk.object_id}})
    return matches


def merge_search_rows(existing: JsonDict | None, row: JsonDict) -> JsonDict:
    if existing is None:
        return row
    existing_distance = distance_for(existing)
    row_distance = distance_for(row)
    if existing_distance is None:
        return row
    if row_distance is None:
        return existing
    return row if row_distance < existing_distance else existing
