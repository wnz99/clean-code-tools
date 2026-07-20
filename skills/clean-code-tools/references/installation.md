# Installation and Runtime Operations

Read this reference only when installing, updating, configuring, or removing
the skill, lint presets, Git hooks, or shared MCP runtime. These operations
write to a project or shared runtime, so inspect first, present the plan, and
perform only the categories the user authorized.

## Install or update the skill

Install into the target project rather than a user-level skills directory:

```bash
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent codex --replace
python3 /path/to/clean-code-tools/scripts/install_codex_skill.py --agent claude --replace
```

Use `--from-main` to fetch the published `main` branch. Select only the agent
the user uses. The installer registers the shared MCP runtime in
`.codex/config.toml` or `.mcp.json` while preserving unrelated configuration.
Tell the user to restart the agent after installation.

The default runtime home is `${CLEAN_CODE_TOOLS_HOME:-~/.clean-code-tools}`.
Runtime files, dependencies, indexes, and logs stay outside the target project.
After restart, call `clean_code_index_info`, then make a narrow
`search_clean_code_patterns` query. Installation is complete only when both
calls succeed and search returns patterns.

## Inspect lint installation

Run the bundled installer without `--apply` first:

```bash
python3 /path/to/clean-code-tools/scripts/install_clean_code_linting.py
```

Use `--repo /path/to/repo` when needed and `--target path/to/package` for a
monorepo package. The dry run reports detected languages, dependency commands,
file edits, blockers, warnings, and verification commands. Prefer targeted
installation at monorepo roots; use `--allow-root-monorepo` only after explicit
approval.

Return this contract after inspection:

```markdown
## Clean-Code Installation Plan

### Decision
<Apply root installer | target package/service | manual merge | defer>, with a reason.

### Evidence
- Repo shape: <workspace/package layout>
- Existing tooling: <package manager, lint configs, hooks, scripts>
- Installer dry runs: <commands and statuses>

### Phase 1: Shared Tooling
- Goal: <installed or configured capability>
- Commands: <exact dry-run/apply commands>
- Expected files/packages: <specific changes>
- Requires approval before apply: yes

### Phase 2: Targeted Rollout
- Target: <package or service>
- Action: <automatic apply or manual merge>
- Command or edit: <exact command or configuration snippet>
- Verification: <target-specific commands>

### Deferred Or Skipped
- <category and reason>

### Rollback
- <backup or revert procedure>

### Open Questions
- <only questions blocking apply>
```

If root dry-run says `status: safe to apply` but repository evidence shows a
monorepo or package-local policy, prefer `--target` or a manual merge.

## Apply safely

Apply only after authorization and a safe plan:

```bash
python3 /path/to/clean-code-tools/scripts/install_clean_code_linting.py --apply
```

Interactive apply asks before each write or install. Use `--yes` only when the
whole plan is already approved, and pair it with an explicit
`--git-hooks pre-push` or `--git-hooks none`. Preserve the default rollback
branch and dirty-worktree patches; use `--no-backup` or `--allow-dirty` only
when the user explicitly accepts that tradeoff.

Complex existing ESLint, Ruff, or Pylint policies require a manual merge rather
than mechanical overwrite. After apply, read the apply summary and run every
recommended verification command plus relevant repository CI checks.

## Optional Git hooks

Recommend `pre-push` first because semantic feedback can be slow. Plan and
apply explicitly:

```bash
python3 /path/to/clean-code-tools/scripts/install_clean_code_linting.py --git-hooks pre-push
python3 /path/to/clean-code-tools/scripts/install_clean_code_linting.py --apply --git-hooks pre-push
```

Choices are `none`, `pre-commit`, `pre-push`, and `both`. Advisory mode is the
default. Use blocking mode only when the user wants candidate findings to fail
Git operations. Hook output remains a tripwire: inspect its code anchors and
validate suggested MCP queries before reporting findings.

## Shared MCP runtime

The normal installer copies an isolated runtime and builds its SQLite vector
index. Start it explicitly when requested:

```bash
python3 /path/to/clean-code-tools/scripts/install_clean_code_linting.py --start-mcp-runtime --apply
```

The default HTTP endpoint is `http://127.0.0.1:8765`; use
`CLEAN_CODE_MCP_PORT` if occupied. The launcher must set the same absolute
runtime directory for `CLEAN_CODE_INDEX_BASE` and the parent of
`CLEAN_CODE_VECTOR_INDEX_PATH`, otherwise pattern search can reject the index
as outside its allowed scope.

Use `--no-mcp-runtime` only when the user opts out. Removal deletes the shared
runtime home and therefore requires explicit authorization:

```bash
python3 /path/to/clean-code-tools/scripts/install_clean_code_linting.py --uninstall-mcp-runtime --apply
```
