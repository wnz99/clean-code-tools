#!/usr/bin/env python3
from __future__ import annotations

import argparse

from _mcp_app import load_semantic_module

semantic = load_semantic_module()
DEFAULT_BATCH_SIZE = semantic.DEFAULT_BATCH_SIZE
build_chunks = semantic.build_chunks
ingest_chunks = semantic.ingest_chunks
reset_collection = semantic.reset_collection


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", default=semantic.DEFAULT_WEAVIATE_URL)
    parser.add_argument("--collection", default=semantic.COLLECTION_NAME)
    parser.add_argument("--model", default=semantic.DEFAULT_EMBEDDING_MODEL)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest clean-code semantic chunks into Weaviate.")
    add_common_args(parser)
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the collection first.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1")
    if args.reset:
        reset_collection(url=args.url, collection_name=args.collection)
    chunks = build_chunks()
    inserted = ingest_chunks(
        chunks=chunks,
        url=args.url,
        collection_name=args.collection,
        model_name=args.model,
        batch_size=args.batch_size,
    )
    print(f"ingested={inserted} collection={args.collection}")


if __name__ == "__main__":
    main()
