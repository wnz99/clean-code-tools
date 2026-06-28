# Static Trigger to Semantic Review

This repo uses deterministic lint rules as tripwires for deeper clean-code
review. The static layer stays fast and reproducible; the semantic layer decides
whether a finding is a real maintainability issue and what refactor would be
safe.

## Flow

```text
ESLint / Pylint / Ruff
  -> clean-code review candidates
  -> clean-code-mcp-reviewer skill
  -> clean-code MCP pattern lookup
  -> advisory finding or refactor plan
  -> normal tests and lint verification
```

The scanner output uses schema `clean-code-review-candidates/v1`. Each
candidate contains:

- `language`
- `file`
- `symbol`
- `anchor`
- `skill`
- deterministic `triggers`
- `semantic_questions`
- suggested `mcp_queries`

## Run

From lint JSON files:

```bash
bun run clean-code:candidates -- \
  --eslint-json eslint-report.json \
  --pylint-json pylint-report.json \
  --ruff-json ruff-report.json
```

From lint commands:

```bash
bun run clean-code:candidates -- \
  --pylint-command "uv run --group lint pylint src/python/mcp_server --output-format=json" \
  --ruff-command "uv run --group lint ruff check src/python/mcp_server --output-format=json"
```

Markdown is useful for agent prompts:

```bash
bun run clean-code:candidates -- \
  --pylint-command "uv run --group lint pylint src/python/mcp_server --output-format=json" \
  --ruff-command "uv run --group lint ruff check src/python/mcp_server --output-format=json" \
  --format markdown
```

## Trigger Policy

Only rules with a strong relationship to maintainability are promoted into
semantic candidates. Formatting and ordinary style rules are intentionally
ignored.

Good triggers include:

- large files, functions, or classes
- high complexity or nesting
- too many arguments, locals, statements, branches, or public methods
- duplicated branches or functions
- boolean flag arguments
- output argument mutation
- TODO/comment hygiene, commented-out code, and traceable technical debt
- policy literals, magic values, duplicate strings, and repeated domain values
- train-wreck object navigation, broad imports, and dependency cycles
- dead stores, unused symbols, and incomplete cleanup

The trigger is not the recommendation. For example, `max-lines` means "inspect
this file for mixed responsibilities"; it does not mean "split the file."

## Agent Contract

`skill` is always `clean-code-mcp-reviewer`. The candidate does not name
language-specific skills because consuming systems may only install this repo's
MCP reviewer skill.

Agents should:

1. Read the candidate's file plus its `symbol` or `anchor` first.
2. Confirm or reject the semantic questions using local code evidence.
3. Query the MCP narrowly with the suggested query or a refined one.
4. Suppress weak matches.
5. Produce a scoped refactor plan only when it preserves behavior and follows
   local conventions.

This keeps the deterministic check useful without turning clean-code guidance
into noisy doctrine.
