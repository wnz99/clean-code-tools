# Semantic Weaviate Search

This repo uses local Weaviate with self-provided vectors. Weaviate stores chunks and performs vector search; Python generates CPU embeddings with FastEmbed.

## Local Setup

```bash
uv sync
npm run weaviate:dev:start
npm run weaviate:dev:smoke
```

If port `8080` is busy:

```bash
WEAVIATE_HTTP_PORT=18080 WEAVIATE_GRPC_PORT=15051 npm run weaviate:dev:start
WEAVIATE_HTTP_PORT=18080 npm run weaviate:dev:smoke
```

## Ingest

```bash
npm run semantic:chunks
npm run semantic:ingest -- --reset
```

The default collection is `CleanCodeChunks`. The default embedding model is `BAAI/bge-small-en-v1.5`, running through `fastembed/cpu`.

## Search

```bash
npm run semantic:search -- "boolean flag argument"
npm run semantic:search -- "comments that explain bad code"
npm run semantic:search -- "train wreck deep property chain"
npm run semantic:search -- "too many function arguments"
```

Expected useful matches include:

- `boolean flag argument`: `CC-043`, `CC-208`, `CC-224`
- `comments that explain bad code`: `CC-060`, `CC-071`, `CC-073`
- `train wreck deep property chain`: `CC-107`, `CC-245`
- `too many function arguments`: `CC-041`, `CC-045`, `CC-206`

The MCP pattern search builds on this chunk search but adds a pattern-first
retrieval layer:

- overfetch semantic matches from Weaviate
- add local exact matches over pattern IDs, titles, aliases, and lint candidates
- filter by source kind, language, rule family, topic, and lintability
- rerank with transparent semantic, lexical, metadata, and context scores
- deduplicate by `record_id`
- return `no_strong_match` for weak or conservative contexts

Run the offline retrieval evals with:

```bash
npm run check:retrieval-evals
```

## Chunking

The ingestion builds two chunk families:

- `pattern_record`: one chunk per canonical `clean-code-patterns.jsonl` record
- `markdown_section`: one chunk per heading section in markdown docs

Markdown parsing is code-fence aware and preserves code blocks with the nearest semantic section. Oversized sections are split by paragraph/code-block groups instead of arbitrary character windows.

## Schema

The collection uses a named self-provided vector:

```text
collection: CleanCodeChunks
vector: content
vectorizer: none
```

Stored properties include source identity, section path, clean-code rule metadata, lintability, language hints, `contentText`, `embeddingText`, `textHash`, `chunkerVersion`, `embeddingModel`, and `embeddingProvider`.
