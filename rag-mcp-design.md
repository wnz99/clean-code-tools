# RAG MCP Design For Clean-Code Pattern Discovery

## Reader And Goal

Reader: an engineer building an agent-facing knowledge system for clean-code examples.

Post-read action: implement an MCP server that lets an agent discover relevant clean-code patterns during planning, retrieve examples in TypeScript and Python, and turn repeated retrieval results into candidate lint rules.

## Design Summary

Build a small RAG service behind an MCP server.

The corpus is the clean-code pattern set. Each entry is indexed as a standalone chunk with metadata for topic, title, language coverage, rule family, and lintability. The MCP server exposes:

- resources for browsing the corpus and individual pattern records
- tools for semantic, keyword, and hybrid search
- prompts for planning workflows that ask the agent to search before proposing code changes

The agent should use the MCP during planning, not only during final review. The expected workflow is:

1. The agent inspects the target code or task.
2. The agent calls `search_clean_code_patterns` with the concrete smell or design decision.
3. The RAG service returns 5-10 ranked pattern records with TS/Python examples and lint candidates.
4. The agent incorporates the relevant rules into its plan.
5. If the same pattern is repeatedly useful, the system records it as a lint-rule candidate.

## Source Signals From Current Docs

MCP is designed to connect AI applications to external systems, including data sources, tools, and specialized prompts. MCP resources expose contextual data by URI, tools can be discovered and invoked by models, and prompts are user-controlled templates for structured workflows.

OpenAI retrieval docs describe semantic search over vector stores, query rewriting, attribute filtering, and configurable chunking. Qdrant documents hybrid dense+sparse search and result fusion, which is important here because clean-code lookup needs both semantic matching and exact term matching, such as `flag arguments`, `train wrecks`, `G28`, or `command query separation`.

Useful source docs:

- MCP intro: https://modelcontextprotocol.io/docs/getting-started/intro
- MCP resources: https://modelcontextprotocol.io/specification/2025-06-18/server/resources
- MCP tools: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- MCP prompts: https://modelcontextprotocol.io/specification/2025-06-18/server/prompts
- OpenAI retrieval and vector stores: https://developers.openai.com/api/docs/guides/retrieval
- Qdrant hybrid search: https://qdrant.tech/documentation/search/hybrid-queries/
- LlamaIndex ingestion pipeline: https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/

## Data Model

Use one canonical record per clean-code entry.

```json
{
  "id": "CC-014",
  "title": "Avoid Flag Arguments",
  "topic": "Chapter 3: Functions",
  "description": "Replace boolean mode switches with separate functions that reveal intent.",
  "languages": ["typescript", "python"],
  "rule_family": "function_arguments",
  "smell_terms": ["flag argument", "boolean parameter", "selector argument"],
  "lintability": "high",
  "ts_example": "...",
  "python_example": "...",
  "lint_candidates": ["flag boolean literals passed to function calls outside tests"],
  "source_kind": "original_example",
  "version": 1
}
```

Recommended metadata:

- `id`: stable pattern ID
- `topic`: chapter or heuristic group
- `rule_family`: normalized grouping, such as `naming`, `comments`, `tests`, `concurrency`
- `language`: `typescript`, `python`, or `both`
- `smell_terms`: searchable aliases
- `lintability`: `high`, `medium`, `low`, or `review_only`
- `example_kind`: `positive`, `negative`, or `paired`
- `version`: increment when examples or lint notes materially change

Do not embed the entire corpus as one document. Embed each pattern as a separate record. Optionally create additional language-specific child chunks if retrieval needs to return TS-only or Python-only snippets.

## Ingestion Pipeline

The ingestion pipeline should be deterministic.

1. Parse the markdown corpus into pattern records.
2. Validate that every record has an ID, title, topic, description, TS example, Python example, and lint candidate.
3. Normalize aliases:
   - `flag argument`, `selector argument`, `boolean mode`
   - `train wreck`, `message chain`, `transitive navigation`
   - `magic number`, `unnamed constant`
4. Generate two text fields:
   - `embedding_text`: title, topic, description, smell terms, and lint candidate
   - `display_text`: full entry with both code examples
5. Store metadata and display text in the vector database.
6. Store a checksum so unchanged records are not re-embedded.

Example `embedding_text` shape:

```text
Avoid Flag Arguments
Topic: Chapter 3: Functions
Description: Replace boolean mode switches with separate functions that reveal intent.
Smell terms: flag argument, boolean parameter, selector argument
Lint candidate: flag boolean literals passed to function calls outside tests
Languages: typescript, python
```

## Retrieval Strategy

Use hybrid retrieval as the default.

Dense vector search is good for vague planning queries:

- "this function does too much"
- "how should I name this variable"
- "what pattern helps avoid hidden mutation"

Sparse or keyword search is good for exact clean-code terms:

- `G28`
- `F3`
- `flag arguments`
- `Law of Demeter`
- `Javadocs in nonpublic code`

Recommended ranking pipeline:

1. Query rewrite: convert task context into a concise smell query.
2. Metadata filter: restrict by language, topic, or lintability when known.
3. Hybrid search: combine dense and sparse results.
4. Rerank: prefer entries matching the requested language and the current task phase.
5. Diversify: avoid returning ten near-duplicate naming rules.
6. Return compact results first; include full examples only for selected entries.

Suggested retrieval defaults:

- initial search limit: 20
- reranked result limit: 8
- planning prompt context: top 5
- lint-rule generation context: top 10 with `lintability = high | medium`

## MCP Surface

### Resources

Expose stable corpus resources.

```text
clean-code://patterns
clean-code://patterns/{id}
clean-code://topics
clean-code://topics/{topic}
clean-code://rules/lint-candidates
```

Use resources when a client or user wants to browse known material. Resources should be read-only.

### Tools

Expose model-invoked tools for planning and review.

```json
{
  "name": "search_clean_code_patterns",
  "description": "Find clean-code patterns and examples relevant to a code smell, planning question, or lint-rule idea.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string" },
      "language": { "type": "string", "enum": ["typescript", "python", "both"] },
      "topic": { "type": "string" },
      "lintability": { "type": "string", "enum": ["high", "medium", "low", "review_only"] },
      "limit": { "type": "integer", "minimum": 1, "maximum": 20 }
    },
    "required": ["query"]
  }
}
```

Add two narrower tools after the first version works:

```text
recommend_lint_rules
find_examples_by_code_smell
```

`recommend_lint_rules` should return lint candidates, false-positive risks, and suggested implementation targets, such as ESLint, Ruff, Semgrep, or custom AST checks.

`find_examples_by_code_smell` should return concise examples only, for use in planning prompts.

### Prompts

Expose prompts for user-triggered workflows.

```text
plan_with_clean_code_patterns
review_code_with_clean_code_patterns
draft_lint_rule_from_pattern
```

`plan_with_clean_code_patterns` should ask the agent to:

1. summarize the task
2. identify likely smell families
3. call `search_clean_code_patterns`
4. select applicable rules
5. produce a plan that cites the selected pattern IDs

## Planning Session Workflow

The planning workflow should make retrieval mandatory only when useful. Avoid forcing pattern search for tiny edits.

Trigger search when:

- the task mentions refactoring, maintainability, naming, tests, comments, linting, or architecture
- the agent detects a large function, vague name, boolean argument, deep chain, duplicated condition, broad class, hidden side effect, or weak test
- the user asks for a plan, review, lint rule, or clean-code guidance

Example planning protocol:

```text
Before proposing code changes:
1. Identify up to three likely clean-code concerns.
2. Search the clean-code MCP for those concerns.
3. Include only pattern IDs that directly affect the plan.
4. Do not apply a pattern mechanically if local project conventions conflict.
```

Example tool call:

```json
{
  "query": "function takes a boolean parameter that changes behavior",
  "language": "typescript",
  "lintability": "high",
  "limit": 8
}
```

Example result shape:

```json
{
  "results": [
    {
      "id": "CC-014",
      "title": "Avoid Flag Arguments",
      "score": 0.91,
      "why": "Matches boolean mode switch and has high lintability.",
      "description": "Replace boolean mode switches with separate intention-revealing functions.",
      "ts_example": "sendInvoiceEmail(invoice);\\nsendInvoiceReminder(invoice);",
      "python_example": "send_invoice_email(invoice)\\nsend_invoice_reminder(invoice)",
      "lint_candidates": ["flag boolean literals passed to function calls outside tests"]
    }
  ]
}
```

## Learning Loop For Lint Rules

Treat lint rules as products of repeated evidence, not one-off suggestions.

Record every planning retrieval event:

```json
{
  "timestamp": "2026-06-26T18:00:00Z",
  "task_kind": "refactor",
  "query": "boolean parameter changes behavior",
  "selected_pattern_ids": ["CC-014", "CC-255"],
  "language": "typescript",
  "accepted_by_agent": true,
  "used_in_final_plan": true,
  "false_positive_note": null
}
```

Promote a lint candidate when:

- the same pattern is selected repeatedly across real tasks
- the smell can be detected with AST or static analysis
- false positives can be suppressed with a clear allowlist
- the rule has useful autofix guidance or review guidance

Rule maturity levels:

- `idea`: retrieved from corpus but not validated
- `candidate`: seen in multiple planning sessions
- `prototype`: implemented in a local rule or Semgrep pattern
- `active`: enabled in project lint config
- `retired`: too noisy or replaced by a better rule

## Lint Rule Targets

Use different tools for different rule types.

TypeScript:

- ESLint custom rules for AST-level checks
- TypeScript compiler API for type-aware checks
- Semgrep for simple syntactic patterns

Python:

- Ruff custom rules where appropriate
- flake8 plugin for project-specific checks
- pylint plugin for semantic rules
- Semgrep for language-independent structural checks

High-value first rules:

- boolean literal passed to a non-test function call
- function over configured length threshold
- too many parameters
- repeated numeric literals
- complex condition with three or more boolean operators
- deep property chain
- commented-out code
- TODO without issue ID
- environment variable read outside configuration module

## Evaluation

Evaluate retrieval quality before building many lint rules.

Create a small benchmark with queries like:

- "boolean parameter changes function behavior"
- "chain of nested object property access"
- "test has too many assertions"
- "comment repeats the code"
- "magic number used in pricing logic"
- "async code updates shared cache"

For each query, define expected pattern IDs. Track:

- top-1 accuracy
- top-5 recall
- language-filter accuracy
- duplicate-result rate
- whether returned examples are directly usable in planning

The MCP should fail closed: if retrieval confidence is low, return "no strong match" and suggest broader search terms instead of forcing weak guidance into the plan.

## Build Plan

1. Convert the markdown corpus into JSONL records.
2. Add metadata normalization and checksum-based incremental ingestion.
3. Index records in a vector store with dense embeddings and keyword/sparse fields.
4. Implement `search_clean_code_patterns` as the first MCP tool.
5. Add read-only resources for browsing patterns by ID and topic.
6. Add `plan_with_clean_code_patterns` prompt.
7. Add retrieval evaluation queries and expected pattern IDs.
8. Add logging for selected pattern IDs during planning sessions.
9. Promote repeated high-confidence lint candidates into prototype lint rules.

## Key Design Decisions

- Use hybrid search by default because clean-code queries mix semantic intent and exact named rules.
- Keep MCP tools read-only at first. Lint-rule promotion should write to a separate reviewable artifact later.
- Return pattern IDs in every result so agent plans can cite durable guidance.
- Keep examples original and short so retrieved context is safe to include in prompts.
- Treat local project conventions as higher priority than generic clean-code advice.

