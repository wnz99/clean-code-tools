# Clean Code Tools

This repository contains clean-code lint packages, a local MCP server for
pattern lookup, and the production clean-code pattern corpus.

Start with [docs/README.md](docs/README.md) for the documentation index.

For vector database ingestion, use `data/clean-code-patterns.jsonl`. It contains
264 records with aliases, problem statements, use/avoid guidance, good and bad
examples, lintability, and embedding/display text. The expected record shape is
documented in `data/vector-record.schema.json`.

Suggested vector metadata fields:

- `id`
- `topic`
- `language`
- `title`
- `description`
- `lint_candidates`

## Local MCP

This repo includes a uv-backed FastMCP server in `src/python/mcp_server` for local
clean-code pattern search.

```bash
uv sync
bun run weaviate:dev:start
bun run semantic:ingest -- --reset
bun run mcp:http
```

Useful checks:

```bash
bun run check:fastmcp
bun run check:retrieval-evals
bun run check
```

The agent-facing tools are documented in `docs/fastmcp-local-server.md`.

## Static Triggers to Semantic Review

Use deterministic lint output as the first pass, then hand selected
maintainability tripwires to an agent or MCP-backed review:

```bash
bun run clean-code:candidates -- \
  --pylint-command "uv run --group lint pylint src/python/mcp_server --output-format=json" \
  --ruff-command "uv run --group lint ruff check src/python/mcp_server --output-format=json"
```

The workflow and `clean-code-review-candidates/v1` schema are documented in
`docs/static-trigger-semantic-review.md`.

## Packages

The ESLint plugin/config is distributed through npm, and the Python Pylint
plugin/config is distributed through PyPI. Packaging checks are documented in
`docs/publishing.md` and run through:

```bash
bun run check:packages
```
