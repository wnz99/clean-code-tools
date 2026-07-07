#!/usr/bin/env python3
from __future__ import annotations

import argparse

from _mcp_app import load_semantic_module

semantic = load_semantic_module()
DEFAULT_BATCH_SIZE = semantic.DEFAULT_BATCH_SIZE
build_chunks = semantic.build_chunks
ingest_chunks = semantic.ingest_chunks
BATCH_SIZE_ERROR = "--batch-size must be at least 1"


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--index-path", default=semantic.DEFAULT_INDEX_PATH)
    parser.add_argument("--model", default=semantic.DEFAULT_EMBEDDING_MODEL)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local sqlite-vec clean-code index.")
    add_common_args(parser)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Insert or update chunks without recreating the index file first.",
    )
    args = parser.parse_args()

    if args.batch_size < 1:
        raise SystemExit(BATCH_SIZE_ERROR)
    chunks = build_chunks()
    inserted = ingest_chunks(
        chunks=chunks,
        index_path=args.index_path,
        model_name=args.model,
        batch_size=args.batch_size,
        reset=not args.no_reset,
    )
    print(f"indexed={inserted} index={args.index_path}")


if __name__ == "__main__":
    main()
