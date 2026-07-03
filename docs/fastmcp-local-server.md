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
- `get_clean_code_pattern`: full lookup by built-in `CC-###` or custom pattern ID.
- `recommend_clean_code_lint_rules`: lint-rule candidate guidance for repeated smells.
- `list_clean_code_facets`: available filter values and counts.
- `validate_clean_code_pattern`: validate a custom pattern payload without writing it.
- `list_custom_clean_code_patterns`: list custom pattern records from the configured JSONL store.
- `upsert_clean_code_pattern`: validate and store a custom pattern, optionally syncing Weaviate.
- `delete_custom_clean_code_pattern`: delete a custom pattern, optionally syncing Weaviate.

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

Custom pattern lookup:

```json
{
  "pattern_id": "CUSTOM-001",
  "custom_patterns_path": "data/custom-clean-code-patterns.jsonl"
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

Custom pattern validation:

```json
{
  "pattern": {
    "id": "CUSTOM-001",
    "title": "Prefer Named Payment States",
    "topic": "Domain Rules",
    "rule_family": "naming",
    "aliases": ["payment state", "named status", "domain constant"],
    "problem": "Raw payment status strings make policy drift hard to see.",
    "use_when": "Use when status checks express business policy.",
    "avoid_when": "Avoid when parsing external payloads at the boundary.",
    "good_examples": {
      "typescript": ["if (payment.status === PaymentStatus.Captured) settle(payment);"],
      "python": ["if payment.status is PaymentStatus.CAPTURED:\n    settle(payment)"]
    },
    "bad_examples": {
      "typescript": ["if (payment.status === 'captured') settle(payment);"],
      "python": ["if payment.status == 'captured':\n    settle(payment)"]
    },
    "lint_candidates": ["Flag raw payment status strings outside adapters."],
    "lintability": "high",
    "source": {"kind": "custom", "version": 1}
  }
}
```

Built-in `CC-###` records are read-only. Custom records must use `CUSTOM-###`
or a repository namespace such as `BILLING-001`. The default store is
`data/custom-clean-code-patterns.jsonl`; set `CLEAN_CODE_CUSTOM_PATTERNS_PATH`
or pass `custom_patterns_path` to use a repo-local file.

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
