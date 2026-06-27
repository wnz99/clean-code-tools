# Codex Handoff: Clean Code Tools

## Goal

Build a clean-code pattern corpus and use it as the foundation for a RAG-backed MCP server that helps agents discover good TypeScript and Python clean-code examples during planning, review, and lint-rule design.

## Current Folder

This folder is the working destination:

```text
/Users/davidfava/Projects/Personal/clean-code-tools
```

The files were copied here from `/Users/davidfava/Projects/Mode/ms-trade/docs/clean-code-patterns`, and the source copy was removed from that repo.

## Files

```text
README.md
clean-code-examples.md
clean-code-patterns.jsonl
build_vector_records.py
vector-record.schema.json
rag-mcp-design.md
CODEX_HANDOFF.md
```

## Corpus

`clean-code-examples.md` is the human-readable corpus.

It contains 264 entries based on the named chapter points from *Clean Code* plus the Chapter 17 smell/heuristic list. It intentionally excludes non-guidance headings such as bibliographies and generic conclusion sections.

Each markdown entry has:

- stable `CC-###` ID
- title
- topic
- short description
- TypeScript example
- Python example
- lint/static-analysis candidate

The examples and guidance are original; the book text was not copied.

## Vector Ingestion Artifact

`clean-code-patterns.jsonl` is the preferred vector database ingestion source.

Each JSONL record includes:

- `id`
- `title`
- `topic`
- `rule_family`
- `aliases`
- `problem`
- `use_when`
- `avoid_when`
- `good_examples.typescript`
- `good_examples.python`
- `bad_examples.typescript`
- `bad_examples.python`
- `lint_candidates`
- `lintability`
- `embedding_text`
- `display_text`
- `source`

`embedding_text` is designed for vector search. `display_text` is designed for MCP/tool responses.

## Generator

`build_vector_records.py` deterministically regenerates `clean-code-patterns.jsonl` from `clean-code-examples.md`.

Run:

```bash
python3 build_vector_records.py
```

The script validates required fields, unique IDs, alias count, and a minimum embedding text size before writing output.

## Schema

`vector-record.schema.json` documents the intended JSONL record shape.

Formal schema validation was not run in the original workspace because `jsonschema` was not installed locally. The generator still performs local structural validation.

## Last Validation Results

Validation from this folder passed:

```text
records=264
unique_ids=264
embed_words_min=151 median=183 max=242
under_120_embedding_words=0
```

Earlier markdown validation also passed:

```text
sections=264
unique_ids=264
type_script_blocks=264
python_blocks=264
missing_required_markers=[]
```

## RAG/MCP Design

`rag-mcp-design.md` contains the architecture proposal.

Core design:

- Use the JSONL corpus as canonical ingestion data.
- Use hybrid dense+sparse retrieval, because clean-code search includes both semantic queries and exact terms like `flag arguments`, `G28`, `Law of Demeter`, and `command query separation`.
- Expose an MCP server with:
  - resources for browsing patterns and topics
  - tools for semantic/hybrid search
  - prompts for planning and review workflows
- Make agents search the corpus during planning when tasks involve refactoring, maintainability, naming, tests, comments, architecture, or linting.
- Track repeated selected patterns as lint-rule candidates.

Suggested initial MCP tool:

```json
{
  "name": "search_clean_code_patterns",
  "description": "Find clean-code patterns and examples relevant to a code smell, planning question, or lint-rule idea."
}
```

Suggested first resources:

```text
clean-code://patterns
clean-code://patterns/{id}
clean-code://topics
clean-code://topics/{topic}
clean-code://rules/lint-candidates
```

Suggested prompts:

```text
plan_with_clean_code_patterns
review_code_with_clean_code_patterns
draft_lint_rule_from_pattern
```

## Important Design Notes

- Do not embed the whole markdown file as one chunk.
- Embed one JSONL record per pattern.
- Prefer `embedding_text` for embeddings.
- Return `display_text` or selected fields to the agent.
- Keep pattern IDs in all MCP responses so plans can cite stable guidance.
- Treat local project conventions as higher priority than generic clean-code rules.
- Lint rules should be promoted from repeated evidence, not created from one retrieval.

## Suggested Next Steps

1. Initialize this folder as a small project if needed.
2. Add a minimal package setup for the MCP server.
3. Choose storage:
   - local JSONL-only search for prototype
   - SQLite + FTS for simple hybrid search
   - Qdrant for dense+sparse vector search
   - OpenAI vector stores if staying inside OpenAI hosted retrieval
4. Implement a loader that reads `clean-code-patterns.jsonl`.
5. Implement `search_clean_code_patterns`.
6. Add a small retrieval evaluation set:
   - "boolean parameter changes function behavior"
   - "chain of nested object property access"
   - "test has too many assertions"
   - "comment repeats the code"
   - "magic number used in pricing logic"
   - "async code updates shared cache"
7. Build MCP resources after search works.
8. Add prompt templates for planning and review.
9. Add lint-rule candidate tracking.

## Source State

The original repo `/Users/davidfava/Projects/Mode/ms-trade` still has unrelated uncommitted changes that were present before this work. The clean-code pattern directory was removed from that repo after copying here.

