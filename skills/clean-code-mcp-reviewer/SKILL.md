---
name: clean-code-mcp-reviewer
description: Use this skill whenever reviewing, refactoring, or designing lint checks for TypeScript, JavaScript, Python, or React code where clean-code patterns may help. This skill teaches agents how to use the clean-code MCP interactively: read code first, form concrete smell hypotheses, query the MCP narrowly, suppress weak matches, and apply only guidance anchored to local code evidence. Use it for maintainability reviews, readability concerns, refactor planning, and clean-code lint-rule design, even when the user does not explicitly mention MCP.
---

# Clean-Code MCP Reviewer

Use the clean-code MCP as decision support, not as a generic style rulebook. The
tool is valuable when a concrete code shape creates a maintainability decision:
function boundaries, arguments, naming, side effects, comments, duplication,
tests, error handling, literals, or object navigation.

## Operating Principle

Read the code before querying. A good MCP query starts from observed local
evidence, not from the task title or a generic desire to "make it cleaner." The
agent remains responsible for judging whether retrieved guidance fits the local
framework, public API, tests, performance constraints, and project conventions.

## When To Use The MCP

Use the MCP when you have a specific clean-code concern:

- reviewing a possible maintainability finding
- planning a behavior-preserving refactor
- deciding whether a pattern is lintable
- comparing alternative extraction, naming, or argument-shape choices
- checking whether a repeated smell should become an ESLint, Ruff, Pylint, or
  Semgrep rule

Do not query for:

- formatting-only edits
- dependency bumps
- obvious build/type errors
- purely mechanical renames
- generated files or migrations unless the user explicitly asks
- code where local conventions or framework idioms already settle the decision

## Query Workflow

1. Inspect the changed code, nearby tests, and local conventions.
2. Identify one concrete concern at a time.
3. Summarize the concern as a smell hypothesis.
4. Query `search_clean_code_patterns` with language and relevant filters.
5. If a result looks useful, call `get_clean_code_pattern` for full detail.
6. Use the pattern only when it matches a concrete code anchor.
7. Say there is no strong clean-code match when results are generic or weak.

Prefer concise queries over whole-file or whole-diff input.

If the pattern-first tools are not available yet, use the lower-level
`search_clean_code` tool as a fallback and be more conservative: treat mixed
markdown/chunk results as supporting context only, and do not claim full pattern
applicability without a canonical pattern record.

Good query examples:

```text
typescript function boolean parameter controls behavior in calculatePrice
python function mutates output argument and also returns status
react component mixes data normalization conditional rendering and side effects
typescript review lint candidate TODO comment without tracked issue id
python long parameter list configuration values passed positionally
```

Poor query examples:

```text
make this cleaner
review this entire diff
clean code suggestions for app.tsx
```

## Result Handling

Treat MCP results as candidates. Before using a result, check:

- Does the result match the language or framework?
- Does the result describe the observed code shape?
- Does `avoid_when` apply?
- Is the pattern lintable, review-only, or context-dependent?
- Would applying it preserve the public API and behavior?
- Is the match specific enough to mention in a review or plan?

Use at most 1-3 selected matches in visible output. Do not decorate every
review finding with pattern IDs. Cite a pattern ID only when it materially
changed the recommendation.

## Review Output

When writing code-review findings, lead with local evidence. Use MCP guidance as
supporting context.

Preferred shape:

```text
Finding: `calculatePrice(user, includeDiscounts)` uses a boolean selector that
changes behavior, so callers must understand two execution modes from one
signature.

Clean-code support: CC-043 applies because the boolean argument selects behavior
rather than representing plain data. A safer remediation is to introduce
intention-revealing functions while keeping a compatibility wrapper if the API
is public.
```

Avoid findings that say only "Clean code says..." or "Pattern CC-043 says...".
The issue must stand on the code.

## Refactor Output

When planning a refactor, translate selected patterns into constraints:

- what behavior must stay unchanged
- what code shape should change
- what compatibility wrapper is needed, if any
- what tests or checks should verify the change

Keep the refactor small unless the user asks for a broader rewrite.

## Lint-Rule Design

For lint-rule work, filter toward high and medium lintability. If the MCP accepts
a list, pass `["high", "medium"]`; if it accepts only one value, run separate
queries or use the lint-rule recommendation tool. Keep
`review_only` patterns out of automated lint checks unless there is a narrow,
low-false-positive signal.

A lint recommendation should include:

- target tool: ESLint, Ruff, Pylint, Semgrep, or review-only
- static signal
- likely false positives
- safe contexts to ignore
- suppression strategy
- autofix feasibility

## Weak-Match Policy

Suppress weak or generic MCP results. Say `no strong clean-code match` when:

- the top results are broad clean-code advice without a local code anchor
- the result depends on context the agent has not verified
- the code is idiomatic for the framework
- the evidence comes from generated, fixture, migration, or test-helper code
- applying the pattern would conflict with stable public API constraints

Missing a weak suggestion is better than producing a noisy style finding.
