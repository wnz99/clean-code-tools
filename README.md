# Clean Code Tools

Clean Code Tools helps teams and coding agents find maintainability problems
that ordinary formatters and type checkers do not catch. It combines three
layers:

- Static lint rules for JavaScript, TypeScript, and Python that flag concrete
  code shapes such as boolean flag arguments, output-argument mutation,
  commented-out code, noisy comments, train-wreck object navigation, business
  policy literals, long functions, deep nesting, and dependency drift.
- A review-candidate generator that turns lint output into structured
  `clean-code-review-candidates/v1` records. These records are deterministic
  tripwires: they tell an agent which files and rules deserve a closer look.
- A local FastMCP server backed by a clean-code pattern corpus. The MCP gives an
  agent searchable guidance for deciding whether a lint tripwire is a real
  design issue, what tradeoffs apply, and what refactor is likely to be useful.

The intended workflow is: run static checks first, send selected candidates to
an agent using the `clean-code-mcp-reviewer` skill when available, then apply
only the recommendations that match the actual code and project conventions.

The repo produces two package shapes:

- `clean-code-tools` on npm: ESLint plugin plus the recommended flat ESLint
  config for JavaScript and TypeScript.
- `clean-code-tools-python` on PyPI: Python Pylint plugin plus a reusable
  Ruff/Pylint config fragment. The shared Python config also includes Deptry,
  which consuming projects install as a development dependency.

It also includes the `clean-code-mcp-reviewer` Codex skill. Install the skill
first so Codex knows the workflow, then use its repo installer to detect a
target repo's languages, propose lint/dependency-check setup, install packages,
configure rules, and optionally add a local pre-push feedback hook.

Start with [docs/README.md](docs/README.md) for the full documentation index.

## What It Does

- Adds clean-code-oriented ESLint rules for TypeScript gaps such as boolean flag
  arguments, output argument mutation, noisy comments, commented-out code,
  business-policy literals, TODO format, and train-wreck object navigation.
- Adds Python clean-code Pylint messages that mirror the custom TypeScript rule
  families where Ruff/Pylint built-ins are not enough.
- Combines those custom rules with existing ESLint, Ruff, Pylint, SonarJS,
  Unicorn, Knip, Fallow, and Deptry checks.
- Converts deterministic lint output into `clean-code-review-candidates/v1`
  records for agent follow-up.
- Serves a local FastMCP HTTP or stdio server for clean-code pattern lookup over
  the corpus in `data/clean-code-patterns.jsonl`.

## Installation Workflow

There are two separate install steps:

1. Install the agent skill so Codex or Claude Code knows how to operate this
   tool safely.
2. Use the installed skill to inspect a target repo, propose clean-code package
   and config changes, and apply only the approved plan.

### 1. Install The Agent Skill

Clone this repo, then install the skill into the active agent's skills
directory.

For Codex:

```bash
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent codex
```

This installs `skills/clean-code-mcp-reviewer` into
`${CODEX_HOME:-~/.codex}/skills`.

For Claude Code:

```bash
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent claude
```

This installs the same skill into `~/.claude/skills`.

If the skill is already installed and you want to update it from a newer clone,
add `--replace`:

```bash
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent codex --replace
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent claude --replace
```

Restart the agent after installation so the skill is discovered.

Then ask the agent from inside the target repo:

```text
Use $clean-code-mcp-reviewer to inspect this repo and plan installation.
```

The expected result is a `Clean-Code Installation Plan`, not immediate file
changes. The plan should name the recommended root or target-package strategy,
the exact apply commands to run after approval, files/packages expected to
change, manual merge steps, deferred items, rollback, verification commands, and
any blocking questions.

In Claude Code, invoke the installed skill by name using the skill invocation
style supported by your Claude Code version, or ask Claude to use the
`clean-code-mcp-reviewer` skill explicitly.

### 2. Install The Clean-Code Tooling

The installed skill's first action should be a dry-run scan. The underlying
command is:

```bash
python3 /path/to/clean-code-tools/skills/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py
```

The default mode is a dry run. It reports detected languages, package managers,
files it would modify, commands it would run, and blockers that need manual
integration.

In monorepos, treat the dry run as a scan-first planning step. The installer
blocks root-level workspace changes by default because creating root
`eslint.config.mjs`, `knip.json`, `.fallowrc.json`, or Python lint sections can
conflict with package-local policy. Prefer a package or service target:

```bash
python3 /path/to/clean-code-tools/skills/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --target apps/example-app
```

Use `--allow-root-monorepo` only after explicitly deciding that root-level
configuration is wanted.

After reviewing the plan, ask the agent to apply the approved changes. The
underlying apply command is:

```bash
python3 /path/to/clean-code-tools/skills/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --apply
```

`--apply` is interactive by default. It asks before modifying config files,
installing packages, copying the Docker MCP runtime, starting Docker services,
or installing Git hooks. For automation, use `--yes` only after the plan is
already approved. Non-interactive applies must make hook intent explicit:
use `--git-hooks pre-push` for the recommended hook setup or `--git-hooks none`
to skip hooks intentionally. The installer prints an `apply summary` showing
which categories were applied and skipped.

For a monorepo target, apply the same `--target` that was used during planning:

```bash
python3 /path/to/clean-code-tools/skills/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --target apps/example-app --apply
```

Recommended hook setup:

```bash
python3 /path/to/clean-code-tools/skills/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --apply --git-hooks pre-push
```

The hook runs ESLint and Ruff by default and prints MCP review candidates without
blocking Git unless configured otherwise. Enable deeper Python hook feedback
with `CLEAN_CODE_AGENT_HOOK_PYLINT=1 git push`.

The installer currently adds:

- JavaScript/TypeScript: `clean-code-tools`, ESLint peer dependencies, `knip`,
  and `fallow`.
- Python: `clean-code-tools-python` and `deptry`.
- Config files: `eslint.config.mjs`, `knip.json`, `.fallowrc.json`, and
  clean-code Ruff/Pylint/Deptry sections where safe.
- Scripts: `check:knip`, `check:fallow`, and non-blocking
  `inspect:fallow-health` when those package script names are free.

If a project already has complex ESLint, Ruff, or Pylint configuration, the
installer stops and explains the manual merge instead of overwriting local
policy.

## Use The Packages Directly

### JavaScript / TypeScript

```bash
npm install --save-dev clean-code-tools eslint @eslint/js typescript-eslint eslint-plugin-sonarjs eslint-plugin-unicorn
```

Then import the recommended flat config:

```js
import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";

export default cleanCode;
```

The npm package targets Node `^22.13.0 || >=24`. See
[docs/eslint-recommended-config.md](docs/eslint-recommended-config.md) and
[docs/eslint-custom-rules.md](docs/eslint-custom-rules.md).

### Python

```bash
python -m pip install clean-code-tools-python deptry
```

Merge the packaged Ruff/Pylint/Deptry config into `pyproject.toml`, then run:

```bash
ruff check .
pylint .
deptry . --no-ansi
```

See [docs/python-lint-recommended-config.md](docs/python-lint-recommended-config.md)
and [docs/python-pylint-custom-rules.md](docs/python-pylint-custom-rules.md).

## Run The MCP Locally

This repo includes a FastMCP server in `src/python/mcp_server` for local
clean-code pattern search.

```bash
uv sync
bun install
bun run weaviate:dev:start
bun run weaviate:dev:smoke
bun run semantic:ingest -- --reset
bun run mcp:http
```

Useful checks:

```bash
bun run check:fastmcp
bun run check:retrieval-evals
bun run check
```

The HTTP server defaults to `http://127.0.0.1:8765`. The agent-facing tools are
documented in [docs/fastmcp-local-server.md](docs/fastmcp-local-server.md).

### MCP Capabilities

The MCP server gives coding agents a semantic review layer on top of the static
lint checks:

- Inspect the available corpus and Weaviate schema with
  `clean_code_corpus_summary` and `clean_code_weaviate_schema`.
- Search clean-code guidance with `search_clean_code` for low-level chunk
  retrieval or `search_clean_code_patterns` for pattern-first results with
  confidence, scores, match reasons, and filters for language, topic, rule
  family, lintability, and source kind.
- Fetch built-in `CC-###` guidance or custom pattern details with
  `get_clean_code_pattern`.
- Ask `recommend_clean_code_lint_rules` whether a repeated smell has a practical
  ESLint, Ruff, Pylint, or Semgrep rule candidate.
- Discover available filter values with `list_clean_code_facets`.
- Validate and manage repo-specific custom patterns with
  `validate_clean_code_pattern`, `upsert_clean_code_pattern`,
  `delete_custom_clean_code_pattern`, and `list_custom_clean_code_patterns`.

Built-in `CC-###` records are read-only. Custom patterns use `CUSTOM-###` or a
repo namespace such as `BILLING-001`, are validated with Pydantic before writes,
and can optionally be synced into the local Weaviate collection.

## Dockerized MCP Runtime

The skill can copy a self-contained Docker runtime into a target repo or host
folder:

```bash
python3 /path/to/clean-code-tools/skills/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --mcp-runtime --apply
```

To copy the runtime files, build the images, initialize Weaviate, and start the
MCP server:

```bash
python3 /path/to/clean-code-tools/skills/clean-code-mcp-reviewer/scripts/install_clean_code_linting.py --start-mcp-runtime --apply
```

This creates `.clean-code-mcp/`. The Compose stack initializes Weaviate by
ingesting the bundled corpus before starting the FastMCP HTTP server.

Default ports:

- Weaviate HTTP: `http://127.0.0.1:8080`
- Weaviate gRPC: `127.0.0.1:50051`
- Clean-code MCP HTTP: `http://127.0.0.1:8765`

Override ports with `WEAVIATE_HTTP_PORT`, `WEAVIATE_GRPC_PORT`, and
`CLEAN_CODE_MCP_PORT`.

## Static Triggers To Semantic Review

Use deterministic lint output as the first pass, then hand selected
maintainability tripwires to an agent or MCP-backed review:

```bash
bun run clean-code:candidates -- \
  --eslint-command "bunx eslint . --format json" \
  --pylint-command "uv run --group lint pylint src/python/mcp_server --output-format=json" \
  --ruff-command "uv run --group lint ruff check src/python/mcp_server --output-format=json"
```

The workflow and `clean-code-review-candidates/v1` schema are documented in
[docs/static-trigger-semantic-review.md](docs/static-trigger-semantic-review.md).

## Corpus

For vector database ingestion, use `data/clean-code-patterns.jsonl`. It contains
264 source records with aliases, problem statements, use/avoid guidance, good
and bad examples, lintability, and source metadata. The expected record shape is
documented in `data/vector-record.schema.json`.

The JSONL corpus is the source of truth. Weaviate data is a derived index:
ingestion generates compact `embeddingText` and readable `displayText` from the
structured fields, then stores those generated values in Weaviate. Formatting or
key-order changes in the JSONL do not matter, but `id` values are stable object
identity and field names must keep matching the schema.

Suggested vector metadata fields:

- `id`
- `topic`
- `language`
- `title`
- `description`
- `lint_candidates`

## Development

Requirements:

- Bun `1.3.13`
- uv
- Docker, when running Weaviate or the Dockerized MCP runtime
- Node `^22.13.0 || >=24` for the ESLint package stack
- Python `>=3.12` for the Python package and local MCP tooling

Install dependencies:

```bash
bun install
uv sync
```

Run the full check:

```bash
bun run check
```

Focused checks:

```bash
bun run test
bun run check:deptry
bun run check:knip
bun run check:fallow
bun run inspect:fallow-health
bun run check:packages
```

`inspect:fallow-health` is intentionally non-blocking. It reports complexity and
hotspot candidates that are useful input for MCP-backed review.

## Publishing

The npm and Python packages are versioned together. Every push or merge to
`develop` runs the version workflow, bumps the patch version, commits the
version update, and creates a matching `vX.Y.Z` tag. Publishing happens from
`main`: merge `develop` into `main` after the version commit and tag exist, then
the publish workflow verifies the tag and publishes npm `latest` plus the PyPI
release.

See [docs/publishing.md](docs/publishing.md) for registry setup, trusted
publisher configuration, and release details.
