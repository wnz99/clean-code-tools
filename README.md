# Clean Code Pattern Examples

This directory contains a vectorization-friendly corpus of clean-code examples inspired by the major topics in *Clean Code*. It does not copy the book text. Each entry is written as original guidance with paired TypeScript and Python examples.

Use `clean-code-examples.md` as the first source for an MCP knowledge base. It currently contains 264 entries covering the named chapter points from the contents plus the Chapter 17 smell/heuristic list. The headings are stable chunk boundaries, and every entry includes:

- a stable ID
- a short description
- one TypeScript example
- one Python example
- candidate lint or static-analysis rules

Non-guidance headings such as bibliographies and generic conclusion sections are intentionally excluded because they do not map to a searchable coding pattern.

For vector database ingestion, prefer `clean-code-patterns.jsonl`. It is generated from the markdown by `build_vector_records.py` and enriches each entry with aliases, problem statements, use/avoid guidance, good and bad examples, lintability, and embedding/display text. The expected record shape is documented in `vector-record.schema.json`.

Suggested vector metadata fields:

- `id`
- `topic`
- `language`
- `title`
- `description`
- `lint_candidates`

## Local MCP

This repo includes a uv-backed FastMCP server in `src/mcp_server` for local
clean-code pattern search.

```bash
uv sync
npm run weaviate:dev:start
npm run semantic:ingest -- --reset
npm run mcp:http
```

Useful checks:

```bash
npm run check:fastmcp
npm run check:retrieval-evals
npm run check
```

The agent-facing tools are documented in `docs/fastmcp-local-server.md`.

## Static Triggers to Semantic Review

Use deterministic lint output as the first pass, then hand selected
maintainability tripwires to an agent or MCP-backed review:

```bash
npm run clean-code:candidates -- \
  --pylint-command "uv run --group lint pylint src/mcp_server --output-format=json" \
  --ruff-command "uv run --group lint ruff check src/mcp_server --output-format=json"
```

The workflow and `clean-code-review-candidates/v1` schema are documented in
`docs/static-trigger-semantic-review.md`.
