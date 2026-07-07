# Semantic sqlite-vec Search

This repo uses a local sqlite-vec index with self-provided vectors. Python
generates CPU embeddings with FastEmbed, stores vectors and chunk metadata in a
local SQLite file, and performs nearest-neighbor search in process.

## Local Setup

```bash
uv sync --group mcp
bun install
bun run semantic:ingest
```

The default index path is `.clean-code-index.sqlite`. Override it with
`CLEAN_CODE_VECTOR_INDEX_PATH` or `--index-path`.

## Ingest

```bash
bun run semantic:chunks
bun run semantic:ingest
bun run semantic:ingest -- --index-path .cache/clean-code.sqlite
```

The default embedding model is `BAAI/bge-small-en-v1.5`, running through
`fastembed/cpu`.

## Corpus Contract

`data/clean-code-patterns.jsonl` is the canonical source. Each line is one
structured JSON pattern record validated by `data/vector-record.schema.json`.
The sqlite index is only a derived search artifact.

During ingestion, `build_chunks()` derives:

- `chunkId`: stable chunk identity, such as `pattern:<id>`
- `objectId`: deterministic UUID from `chunkId`
- `embeddingText`: compact search text generated from structured fields
- `displayText`: readable text generated from structured fields
- `textHash`: hash of generated `embeddingText`

Keep source record `id` values stable. Rebuild the index after deleting or
renaming records so stale rows are removed.

## Search

```bash
bun run semantic:search -- "boolean flag argument"
bun run semantic:search -- "comments that explain bad code"
bun run semantic:search -- "train wreck deep property chain"
bun run semantic:search -- "too many function arguments"
```

The MCP pattern search builds on chunk search but adds a pattern-first retrieval
layer:

- overfetch semantic matches from sqlite-vec
- add local exact matches over pattern IDs, titles, aliases, and lint candidates
- filter by source kind, language, rule family, topic, and lintability
- rerank with transparent semantic, lexical, metadata, and context scores
- deduplicate by `record_id`
- return `no_strong_match` for weak or conservative contexts

Run the offline retrieval evals with:

```bash
bun run check:retrieval-evals
```

## Stored Data

The sqlite index contains:

- `vec_chunks`: sqlite-vec virtual table with `chunk_id` and `embedding`
- `chunk_metadata`: SQLite table with `chunk_id`, deterministic `object_id`,
  and serialized chunk properties
- `index_metadata`: SQLite table with the index schema version and vector
  dimensions

The index is safe to delete and rebuild from source files.
