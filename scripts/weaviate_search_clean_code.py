#!/usr/bin/env python3
from __future__ import annotations

import argparse

from _mcp_app import load_semantic_module

semantic = load_semantic_module()
search_chunks = semantic.search_chunks


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", default=semantic.DEFAULT_WEAVIATE_URL)
    parser.add_argument("--collection", default=semantic.COLLECTION_NAME)
    parser.add_argument("--model", default=semantic.DEFAULT_EMBEDDING_MODEL)


def print_search_results(results: list[dict[str, object]]) -> None:
    for index, row in enumerate(results, start=1):
        additional = row.get("_additional") or {}
        distance = additional.get("distance", "?") if isinstance(additional, dict) else "?"
        print(
            f"{index}. {row.get('recordId') or row.get('chunkId')} "
            f"{row.get('title')} distance={distance}"
        )
        print(f"   source={row.get('sourceFile')} kind={row.get('chunkKind', row.get('sourceKind'))}")
        text = " ".join(str(row.get("contentText", "")).split())
        print(f"   {text[:280]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search clean-code semantic chunks in Weaviate.")
    add_common_args(parser)
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")
    results = search_chunks(
        query=args.query,
        url=args.url,
        collection_name=args.collection,
        model_name=args.model,
        limit=args.limit,
    )
    print_search_results(results)


if __name__ == "__main__":
    main()
