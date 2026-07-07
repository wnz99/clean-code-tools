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

This skill is self-contained. Do not assume separate language-specific
clean-code skills are installed. Use the language heuristics below when judging
Python, JavaScript, TypeScript, or React code.

## Installing Or Updating This Skill

When the user asks to install or update this Codex skill itself, do not run the
linting configurator. From a clone of `wnz99/clean-code-tools`, run:

```bash
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent codex --replace
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent claude --replace
```

To fetch and install the latest published skill from the repository `main`
branch, use the update command instead:

```bash
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent codex --replace --from-main
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent claude --replace --from-main
```

Choose the agent the user actually uses. The update command clones
`https://github.com/wnz99/clean-code-tools.git` at `main` into a temporary
directory and installs the skill from that checkout, so it does not depend on
the local clone being up to date. Then tell the user to restart the agent before
expecting the updated skill behavior.

## Installing Clean-Code Linting

When the user asks to install, configure, adopt, bootstrap, or integrate the
clean-code lint rules in another repository, use the bundled installer first.
It makes the static lint layer deterministic and leaves the MCP review layer for
semantic follow-up on the findings.

Run from the target repository:

```bash
python3 /path/to/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py
```

The default mode is a dry run. It detects JavaScript/TypeScript and Python,
identifies the package manager or installer, inspects existing ESLint,
Ruff, and Pylint configuration, and prints:

- languages detected
- packages that would be installed
- files that would be created or modified
- blockers that require a manual integration strategy
- warnings such as missing lint scripts
- recommended verification commands to run after applying

When the user asks to inspect or plan installation, finish with a concrete
`Clean-Code Installation Plan`. Do not end with a loose recommendation. The
plan must be specific enough that another LLM or operator can follow it without
reconstructing the scan.

Use this output shape:

```markdown
## Clean-Code Installation Plan

### Decision
<Apply root installer | target package/service | manual merge | defer>, with one
sentence explaining why.

### Evidence
- Repo shape: <monorepo/workspace/package layout found>
- Existing tooling: <package manager, lint configs, hooks, scripts>
- Installer dry runs: <commands run and statuses>

### Phase 1: Shared Tooling
- Goal: <what this phase installs/configures>
- Command(s):
  ```bash
  <exact dry-run or apply command>
  ```
- Expected files/packages: <specific files and dependencies>
- Requires approval before apply: yes

### Phase 2: Targeted Rollout
- Target: <package/service path>
- Action: <automatic installer apply | manual ESLint merge | manual Python merge>
- Command or edit:
  ```bash
  <exact command, or exact import/config snippet for manual merge>
  ```
- Verification:
  ```bash
  <target-specific lint/test/typecheck command>
  ```

### Deferred Or Skipped
- <hooks/runtime/root ESLint/Python policy/etc. and why>

### Rollback
- <backup branch/patch behavior or manual revert command>

### Open Questions
- <only questions that block applying the plan>
```

If multiple targets are appropriate, list each target as its own Phase 2 item.
If root dry-run says `status: safe to apply` but repo evidence shows a monorepo
or project-local lint policy, override the mechanical result in the plan and
recommend `--target` or manual merges instead.

Apply only when the plan says `status: safe to apply` and the user has asked to
proceed:

```bash
python3 /path/to/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --apply
```

`--apply` is still interactive by default. The installer asks before every
host-side action it offers: modifying lint config files, installing packages,
copying the local MCP runtime, starting local services, or installing Git
hooks. For non-interactive automation, pass `--yes` only after the user has
already approved the whole plan and each selected setup category is intentional.
When using `--apply --yes`, always pass an explicit hook decision:
`--git-hooks pre-push` for the recommended hook setup or `--git-hooks none` to
skip hooks intentionally. The installer treats an unresolved hook choice as a
blocker so hooks cannot be silently dropped.

After apply, read the installer's `apply summary` before reporting completion.
It lists applied categories and skipped categories, including skipped hooks,
skipped dependency installation, skipped runtime setup, and backup behavior.
Before applying, it creates a Git rollback point by default: a
`backup/clean-code-install-<timestamp>` branch, plus patch files under
`.git/clean-code-installer-backups/` when applying over a dirty worktree. Use
`--no-backup` only when the user explicitly declines that safety net.

Use `--repo /path/to/repo` when the current directory is not the target repo.
Use `--target path/to/package` for monorepos when the clean-code config belongs
to a nested package or app inside `--repo`.
At a detected monorepo root, the installer should report a blocker rather than
`status: safe to apply`. Prefer a targeted package/service plan. Use
`--allow-root-monorepo` only after the user explicitly approves root-level
configuration.
Use `--skip-install` only for dry integration tests or when the user wants file
changes but will install dependencies separately. Use `--allow-dirty` only when
the user explicitly accepts applying changes over an uncommitted worktree.

Installer behavior:

- For JavaScript/TypeScript, install `clean-code-tools` plus its ESLint peer
  dependencies, `knip`, and `fallow` as dev dependencies using the detected
  package manager (`bun`, `pnpm`, `yarn`, or `npm`).
- In a monorepo, prefer `--target` for package-local config. The installer can
  detect package managers from ancestor workspace roots, warns when the root
  workspace may not be the intended target, and uses the package manager's root
  as the install command working directory when needed.
- For a repo with no ESLint config, create `eslint.config.mjs` that exports the
  recommended clean-code preset.
- For a simple flat ESLint `export default [...]` config, import the preset and
  spread it at the start of the exported array.
- Create `knip.json` and `.fallowrc.json` when they do not already exist.
- Add `check:knip`, `check:fallow`, and non-blocking
  `inspect:fallow-health` package scripts when those names are free.
- For complex ESLint config shapes, CommonJS configs, or framework-specific
  configs that are not safe to rewrite mechanically, stop and explain the
  manual integration: import
  `clean-code-tools/configs/eslint.clean-code.recommended.mjs` and spread
  `...cleanCode` before local overrides.
- For Python, install `clean-code-tools-python` and `deptry` as development dependencies
  using the detected installer (`uv`, `poetry`, or `pip` fallback).
- For a repo with no `pyproject.toml`, create one with the clean-code Ruff and
  Pylint sections plus a conservative `deptry` section.
- For a `pyproject.toml` with no existing Ruff or Pylint sections, append the
  clean-code lint sections.
- For a `pyproject.toml` with existing clean-code lint sections but no
  `[tool.deptry]`, append the conservative `deptry` section.
- For existing Ruff or Pylint configuration, stop and recommend a manual merge
  instead of overwriting local lint policy.

After applying, run the recommended verification commands printed by the
installer, then run any broader repo CI checks the project expects. If the new
static rules produce maintainability candidates, use the MCP workflow below to
decide which findings deserve refactors.

`check:knip`, `check:fallow`, and `deptry` are deterministic tripwires:

- Knip catches unused JS/TS files, exports, binaries, and dependency drift.
- Fallow's default installed check runs dead-code and duplication analysis.
- `inspect:fallow-health` intentionally does not fail the command; use its
  complexity and hotspot output as MCP review input.
- Deptry catches missing, unused, transitive, and misplaced Python dependencies.

### Optional Git Hook Feedback

The installer can also set up local Git hooks that run deterministic lint
checks before push and print clean-code MCP review candidates back
to the agent. This is useful when the user wants a static check to trigger a
semantic follow-up review automatically.

Interactive apply mode asks whether hooks should be installed. Recommend
`pre-push` first because the lint feedback can take long enough to be disruptive
before every commit. To plan the recommended hook explicitly:

```bash
python3 /path/to/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --git-hooks pre-push
```

To apply after approval:

```bash
python3 /path/to/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --apply --git-hooks pre-push
```

Hook choices are `none`, `pre-commit`, `pre-push`, or `both`. The default hook
mode is `advisory`, which prints feedback without blocking Git. Use
`--git-hook-mode blocking` only when the user wants candidate findings to fail
the hook until reviewed. A local run can bypass hooks intentionally with:

```bash
CLEAN_CODE_AGENT_HOOK=0 git commit
```

or force advisory behavior for one command with:

```bash
CLEAN_CODE_AGENT_HOOK_MODE=advisory git push
```

The hook runs ESLint and Ruff by default. Pylint is intentionally skipped by
default to keep pushes responsive; enable deeper Python hook feedback with
`CLEAN_CODE_AGENT_HOOK_PYLINT=1 git push`.

Hook output is a tripwire, not a final review result. When a hook prints
candidate locations and suggested MCP queries, read the named files first, use
this skill, query the MCP narrowly, and decide whether each candidate is a real
maintainability issue in context.

## Installing The Local MCP Runtime

When the user wants the clean-code MCP copied into another repo or host folder,
use the bundled local Python runtime. It includes:

- `runtime/`: bundled MCP server source, ingest script, and clean-code corpus

Plan the runtime install from the target repo or host folder:

```bash
python3 /path/to/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --mcp-runtime
```

Apply after the user accepts the plan:

```bash
python3 /path/to/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --mcp-runtime --apply
```

This creates `.clean-code-mcp/` in the target folder. To start the MCP server
after copying, use:

```bash
python3 /path/to/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --start-mcp-runtime --apply
```

The stack exposes:

- Clean-code MCP HTTP: `http://127.0.0.1:8765`

The runtime start path requires `pydantic`, `fastmcp`, `fastembed`, and
`sqlite-vec` in the Python interpreter running the installer. The installer
blocks `--start-mcp-runtime` during planning when those modules are missing.
Use `CLEAN_CODE_MCP_PORT` when the default port is occupied.

The sqlite-vec index is a regular local SQLite file. Build it before searching:

```bash
python .clean-code-mcp/runtime/scripts/sqlite_vec_ingest_clean_code.py
```

Manual command after copy-only install:

```bash
python .clean-code-mcp/runtime/scripts/clean_code_mcp_server.py --transport http --host 127.0.0.1 --port 8765
```

## Refactor Discipline

- Read formatter, linter, type-checker, framework, tests, and nearby files
  before applying generic advice.
- Name the concrete smell before proposing a cleanup.
- Keep the refactor local unless the user asks for a broader redesign.
- Preserve public APIs, return shapes, exception behavior, async boundaries,
  mutability expectations, and framework contracts.
- Prefer the smallest useful change: rename, flatten control flow, extract one
  cohesive helper, introduce a stable data shape, or clarify an error boundary.
- Avoid class hierarchies, speculative abstractions, trivial wrappers, and
  extraction that hides the main logic.
- Optimize for the call site: the best boundary makes the caller obviously
  correct.
- Verify that tests, lint, types, and the relevant runtime contract still hold.

## When To Use The MCP

Use the MCP when you have a specific clean-code concern:

- following up deterministic lint triggers emitted as clean-code review
  candidates
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

When a repo provides `clean-code-review-candidates/v1` input, treat each
candidate as a deterministic tripwire, not as a finding. Read the file plus the
symbol or anchor named by the candidate, check whether the listed semantic
questions are actually supported by the code, then run only the relevant MCP
queries. A candidate may produce `no strong clean-code match`, an advisory note,
or a targeted refactor plan.

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

## Language Heuristics

For Python:

- Prefer Pythonic clarity over abstract purity.
- Use plain functions when data flow is simple.
- Use `TypedDict` for stable mapping-shaped data, `dataclass` for value-like
  data, and richer models only when validation, serialization, or invariants
  justify them.
- Use keyword-only parameters when they improve call-site clarity.
- Preserve the local failure style: exceptions, `None`, result objects, or
  framework responses.
- Separate parsing, validation, transformation, and side effects when they are
  tangled.
- Do not add docstrings to every private helper; comments should explain why,
  constraints, or surprising behavior.

For JavaScript and TypeScript:

- Prefer domain names over implementation names; drop vague suffixes like
  `Data`, `Info`, `Manager`, or `Helper` unless they distinguish real concepts.
- Use boolean names that read like questions: `isReady`, `hasAccess`,
  `shouldRetry`.
- Prefer stronger TypeScript types over explanatory comments.
- Narrow external data early and keep internal code on trusted shapes.
- Use discriminated unions when the code already branches on variants.
- Prefer object parameters when several values travel together, but do not
  introduce options objects only to satisfy an arbitrary parameter count.
- Follow the existing error boundary style: throw, result object, or
  framework-specific response.

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
