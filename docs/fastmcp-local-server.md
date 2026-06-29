# FastMCP Local Server

This server exposes clean-code pattern lookup tools through FastMCP. Coding
agents should use the pattern-first tools for review/refactor decisions and keep
the lower-level chunk search for diagnostics.

## Install

```bash
bun install
uv sync
```

## Prepare Weaviate

```bash
bun run weaviate:dev:start
bun run weaviate:dev:smoke
bun run semantic:ingest -- --reset
```

If the default port is busy, use the same alternate port for all commands:

```bash
WEAVIATE_HTTP_PORT=38080 WEAVIATE_GRPC_PORT=35051 bun run weaviate:dev:start
WEAVIATE_HTTP_PORT=38080 bun run weaviate:dev:smoke
bun run semantic:ingest -- --url http://127.0.0.1:38080 --reset
```

## Run MCP

Stdio:

```bash
bun run mcp:stdio
```

HTTP:

```bash
bun run mcp:http
```

The HTTP server defaults to `http://127.0.0.1:8765`.

## Exposed Tools

- `clean_code_corpus_summary`: returns corpus chunk counts.
- `clean_code_weaviate_schema`: returns the `CleanCodeChunks` schema payload.
- `search_clean_code`: low-level compatibility search over populated Weaviate chunks.
- `search_clean_code_patterns`: pattern-first search for concrete code smells.
- `get_clean_code_pattern`: full canonical lookup by `CC-###` ID.
- `recommend_clean_code_lint_rules`: lint-rule candidate guidance for repeated smells.
- `list_clean_code_facets`: available filter values and counts.

Pattern-first search arguments:

```json
{
  "query": "typescript boolean parameter controls behavior",
  "language": "typescript",
  "lintability": ["high", "medium"],
  "limit": 5,
  "weaviate_url": "http://127.0.0.1:8080"
}
```

Full pattern lookup:

```json
{
  "pattern_id": "CC-043"
}
```

Lint-rule recommendation:

```json
{
  "query": "TODO comments without issue IDs",
  "language": "typescript",
  "targets": ["eslint", "semgrep"]
}
```

## Agent Workflow

Use the MCP after inspecting code and forming a concrete smell hypothesis. Send
short queries such as `python function mutates output argument and returns
status`, not whole files or full diffs.

Recommended review loop:

1. Read the changed code and nearby tests.
2. Identify one maintainability concern.
3. Query `search_clean_code_patterns` with language and narrow filters.
4. Fetch detail with `get_clean_code_pattern` only for a relevant result.
5. Use the pattern as support for a local code finding, not as the finding
   itself.
6. Suppress weak results or framework-idiomatic near-misses.

`search_clean_code_patterns` returns `confidence`, `score`, `match_reasons`,
and top-level `no_strong_match`. Treat `no_strong_match` as a signal to avoid
surfacing a clean-code recommendation unless the local code evidence is already
strong.
