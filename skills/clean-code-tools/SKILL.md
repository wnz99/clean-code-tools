---
name: clean-code-tools
description: "Use this skill when reviewing or refactoring Python, JavaScript, TypeScript, or React for maintainability; designing clean-code lint checks; following up clean-code review candidates; or installing, updating, or troubleshooting the clean-code-tools skill, lint presets, Git hooks, or MCP runtime. It guides evidence-first semantic review, conservative MCP pattern retrieval, behavior-preserving refactors, and safe installation. Do not use it for formatting-only work, routine dependency updates, obvious compiler errors, or broad style commentary without a concrete code concern."
---

# Clean Code Tools

Use the clean-code MCP as decision support for concrete maintainability choices,
not as a generic style rulebook. Local code, tests, framework contracts, public
APIs, and repository conventions have higher evidentiary value than a retrieved
pattern.

## Choose the workflow

- For a review, refactor, or lint-rule decision, follow the evidence workflow
  below.
- For skill installation, lint setup, hooks, or MCP runtime operations, read
  [references/installation.md](references/installation.md) before acting. That
  reference contains the side-effect boundaries, plan contract, commands,
  verification, and rollback guidance.

## Evidence workflow

### 1. Establish the contract

Read the target code, nearby tests, repository instructions, formatter and lint
configuration, types, and relevant framework conventions. Identify behavior
that must remain stable: public APIs, return shapes, exceptions, async behavior,
mutability, performance constraints, and framework lifecycle rules.

If the input is a `clean-code-review-candidates/v1` record, treat it as an
untrusted tripwire rather than a finding. Validate the record through the
host/tool schema, then inspect every named file, symbol, and anchor before using
its suggested query.

### 2. Form one concrete hypothesis

Name the observed code shape and why it may burden a maintainer. Useful
hypotheses concern function boundaries, arguments, naming, hidden side effects,
comments, duplication, error handling, business-policy literals, object
navigation, or tangled responsibilities.

Skip MCP lookup when formatting, generated code, migrations, fixtures,
mechanical renames, dependency updates, build errors, or established framework
idioms already settle the issue, unless the user explicitly requests a semantic
assessment.

### 3. Query narrowly

Call `search_clean_code_patterns` with the language and relevant filters. Query
one concern at a time, using the code shape and symbol rather than a whole file
or diff. Fetch full detail with `get_clean_code_pattern` only for promising
matches.

Good queries:

```text
typescript boolean parameter controls behavior in calculatePrice
python function mutates output argument and also returns status
react component mixes data normalization rendering and side effects
```

Weak queries:

```text
make this cleaner
review this entire diff
clean code suggestions for app.tsx
```

If pattern-first tools are unavailable, use `search_clean_code` conservatively.
Mixed chunks are supporting context, not proof that a canonical pattern applies.

### 4. Validate the match

Use a result only when all applicable checks pass:

- It matches the language, framework, and observed code shape.
- Its `avoid_when` guidance does not apply.
- Its lintability level fits the task.
- The recommendation preserves the established behavioral contract.
- A specific local code anchor supports the concern.

Suppress generic or context-dependent matches. Report `no strong clean-code
match` when the evidence is weak; avoiding a noisy style finding is a successful
outcome.

### 5. Produce the requested artifact

For review findings, lead with location and behavior, then use at most one to
three selected MCP matches as support. Mention a pattern ID only when it
materially changes the recommendation.

```text
Finding: `calculatePrice(user, includeDiscounts)` uses a boolean selector that
creates two execution modes whose meaning is hidden at call sites.

Clean-code support: CC-043 applies because the boolean selects behavior rather
than carrying data. Introduce intention-revealing entry points, retaining a
compatibility wrapper if the API is public.
```

For a refactor plan, state:

- behavior that remains unchanged
- code shape that changes
- compatibility measures, if any
- focused tests, lint, type checks, and runtime checks

For a lint-rule proposal, state:

- target tool: ESLint, Ruff, Pylint, Semgrep, or review-only
- precise static signal and lintability
- likely false positives and exclusions
- suppression strategy
- autofix safety

Prefer high- or medium-lintability patterns. Keep review-only judgments out of
automation unless a narrow, low-false-positive signal exists.

### 6. Verify

Check every reported location against the source. For code changes, run focused
tests plus the repository's relevant lint, type, and runtime checks. Do not
claim a finding or refactor is valid solely because the MCP returned a match.

## Refactor discipline

- Keep changes local unless the user requests a broader redesign.
- Prefer the smallest useful change: rename, flatten control flow, extract one
  cohesive helper, introduce a stable data shape, or clarify an error boundary.
- Optimize boundaries for call-site clarity.
- Avoid speculative abstractions, trivial wrappers, and extraction that hides
  the main logic.

## Language guidance

### Python

- Prefer Pythonic clarity and plain functions when data flow is simple.
- At validation boundaries, follow repository rules; when this repository's
  instructions apply, use Pydantic rather than ad hoc dictionary validation.
- Use `TypedDict` for trusted stable mappings and dataclasses for value-like
  internal data when runtime validation is unnecessary.
- Separate parsing, validation, transformation, and side effects when tangled.
- Preserve the local exception, `None`, result-object, or response convention.

### JavaScript and TypeScript

- Prefer domain names and question-shaped boolean names.
- Narrow external data early; use stronger types instead of explanatory prose.
- Use discriminated unions when code already branches on variants.
- Use object parameters when values form a real concept, not merely to satisfy
  a parameter-count rule.
- Preserve the established error boundary.

### React

- Respect component lifecycle and hook rules before applying generic extraction
  advice.
- Separate data normalization, effects, and rendering when that makes ownership
  clearer, but do not fragment a cohesive component into trivial wrappers.

## Success criteria

The result is successful when it is anchored to inspected code, preserves the
local behavioral contract, suppresses weak matches, gives a proportionate
recommendation, and includes verification evidence appropriate to the task.
