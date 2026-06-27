# ESLint Custom Clean-Code Rules

The local plugin lives at [src/eslint-plugin-clean-code.mjs](../src/eslint-plugin-clean-code.mjs). These rules cover TypeScript clean-code checks that are not well covered by common ESLint rule sets.

## Rules

### `clean-code/todo-format`

Requires TODO/FIXME/XXX comments to include an issue-like owner by default:

```ts
// TODO(BILL-412): remove fallback after migration.
```

Default pattern:

```text
^(TODO|FIXME|XXX)\([A-Z][A-Z0-9]+-\d+\):\s+\S
```

Corpus: `CC-068`

### `clean-code/no-commented-out-code`

Flags comments that look like disabled JavaScript or TypeScript code.

Corpus: `CC-083`

### `clean-code/no-boolean-flag-arguments`

Flags boolean literals passed at call sites and boolean selector parameters with mode-like names such as `dryRun`, `force`, `skip`, `include`, or `mode`.

Corpus: `CC-043`, `CC-208`, `CC-224`

### `clean-code/no-output-argument-mutation`

Flags assignments, updates, and common mutator calls that mutate function parameters.

Corpus: `CC-050`, `CC-207`

### `clean-code/no-redundant-comment`

Flags comments whose words heavily overlap the following line of code.

Corpus: `CC-071`, `CC-073`

### `clean-code/no-noisy-comments`

Flags separator comments, author/date byline comments, and comments after closing braces.

Corpus: `CC-080`, `CC-081`, `CC-082`

### `clean-code/no-business-policy-literals`

Flags hard-coded policy-looking literals outside named constants and allowlisted calls. The heuristic catches:

- numbers other than `-1`, `0`, and `1`
- all-caps string values
- ISO date strings
- common domain statuses such as `active`, `approved`, `draft`, `failed`, `pending`, and `rejected`

Corpus: `CC-002`, `CC-018`, `CC-234`

### `clean-code/no-train-wrecks`

Flags deep property chains beyond a configurable maximum depth.

Corpus: `CC-106`, `CC-107`, `CC-245`

## Recommended Config

The rules are enabled in [configs/eslint.clean-code.recommended.mjs](../configs/eslint.clean-code.recommended.mjs).

They are intentionally warnings because each rule is heuristic and should be tuned per repository.
