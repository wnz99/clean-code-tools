# Python Custom Clean-Code Rules

The local Pylint plugin lives at
[src/python/clean_code_tools_pylint/](../src/python/clean_code_tools_pylint/). These rules
mirror the project-owned ESLint clean-code rules where Python syntax gives us a
reasonably precise static signal.

## Rules

### `clean-code-todo-format`

Requires TODO/FIXME/XXX comments to include an issue-like owner by default:

```python
# TODO(BILL-412): remove fallback after migration.
```

Corpus: `CC-068`

### `clean-code-commented-out-code`

Flags comments that look like disabled Python code.

Corpus: `CC-083`

### `clean-code-boolean-flag-argument`

Flags boolean literals passed at call sites and boolean selector parameters with
mode-like names such as `dry_run`, `force`, `skip`, `include`, or `mode`.

Corpus: `CC-043`, `CC-208`, `CC-224`

### `clean-code-output-argument-mutation`

Flags assignments, updates, and common mutator calls that mutate function
parameters.

Corpus: `CC-050`, `CC-207`

### `clean-code-redundant-comment`

Flags comments whose words heavily overlap the following line of code.

Corpus: `CC-071`, `CC-073`

### `clean-code-noisy-comment`

Flags separator comments and author/date byline comments.

Corpus: `CC-080`, `CC-081`

### `clean-code-business-policy-literal`

Flags hard-coded policy-looking literals outside named constants and allowlisted
calls. The heuristic catches:

- numbers other than `-1`, `0`, and `1`
- all-caps string values
- ISO date strings
- common domain statuses such as `active`, `approved`, `draft`, `failed`,
  `pending`, and `rejected`

Corpus: `CC-002`, `CC-018`, `CC-234`

### `clean-code-train-wreck`

Flags deep attribute chains beyond the default maximum depth.

Corpus: `CC-106`, `CC-107`, `CC-245`

## Recommended Config

The plugin is loaded and these messages are enabled in
[configs/python.clean-code.pyproject.toml](../configs/python.clean-code.pyproject.toml).

They are intentionally warnings/design signals because each rule is heuristic
and should be tuned per repository.
