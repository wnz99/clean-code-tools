#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from _mcp_app import load_semantic_module


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect clean-code semantic chunks.")
    parser.add_argument("--json", action="store_true", help="Print chunks as JSONL.")
    args = parser.parse_args()
    semantic = load_semantic_module()
    chunks = semantic.build_chunks()
    if args.json:
        for chunk in chunks:
            print(json.dumps(chunk.properties, sort_keys=True))
        return
    by_kind: dict[str, int] = {}
    for chunk in chunks:
        by_kind[chunk.chunk_kind] = by_kind.get(chunk.chunk_kind, 0) + 1
    print(json.dumps({"chunks": len(chunks), "by_kind": by_kind}, sort_keys=True))


if __name__ == "__main__":
    main()
