# ESLint Recommended Clean-Code Config

This config combines mature existing ESLint rule sets with a small local clean-code plugin for the TypeScript gaps that are not well covered elsewhere.

## Target

Use [configs/eslint.clean-code.recommended.mjs](../configs/eslint.clean-code.recommended.mjs) in TypeScript projects that already run ESLint flat config.

This preset currently targets Node `^22.13.0 || >=24`, matching the tested ESLint 10/plugin stack.

For this local/private package, install from the workspace path or from a packed tarball:

```bash
npm install --save-dev /path/to/clean-code-tools eslint @eslint/js typescript-eslint eslint-plugin-sonarjs eslint-plugin-unicorn
```

Then import the preset from the consuming project's `eslint.config.mjs`:

```js
import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";

export default cleanCode;
```

If a project already has a config, spread this preset before project-specific overrides:

```js
import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";

export default [
  ...cleanCode,
  {
    rules: {
      "max-lines-per-function": ["warn", { max: 120, skipBlankLines: true, skipComments: true }],
    },
  },
];
```

## TypeScript Project Setup

The config uses type-aware `typescript-eslint` rules with `projectService: true` for TypeScript files. Linted `*.ts`, `*.tsx`, `*.mts`, and `*.cts` files must be included by the consuming project's `tsconfig.json`.

If a project intentionally lints generated files, config files, or one-off scripts outside `tsconfig.json`, add a project-specific override rather than broadening this preset globally.

The package declares these peer dependencies:

- `eslint@^10.4.0`
- `@eslint/js@^10.0.0`
- `typescript-eslint@^8.0.0`
- `eslint-plugin-sonarjs@^4.0.0`
- `eslint-plugin-unicorn@^69.0.0`

## Existing Rule Coverage

| Corpus area | Existing ESLint coverage |
| --- | --- |
| Small functions and complexity, `CC-033..CC-059`, `CC-206` | `complexity`, `max-depth`, `max-lines-per-function`, `max-params`, `sonarjs/cognitive-complexity` |
| Magic numbers and repeated literals, `CC-018`, `CC-234` | `@typescript-eslint/no-magic-numbers`, `sonarjs/no-duplicate-string` |
| TODO/FIXME visibility, `CC-068` | `clean-code/todo-format` |
| Duplicate conditions and branches, `CC-160`, `CC-214` | `sonarjs/no-duplicated-branches`, `sonarjs/no-identical-conditions`, `sonarjs/no-identical-functions` |
| Complex and negative conditionals, `CC-237`, `CC-238` | `no-nested-ternary`, `no-negated-condition`, `sonarjs/no-inverted-boolean-check`, `unicorn/no-negated-condition` |
| Null avoidance, `CC-118`, `CC-119` | `unicorn/no-null`, `@typescript-eslint/no-unnecessary-condition`, `@typescript-eslint/prefer-nullish-coalescing` |
| Dead and redundant code, `CC-209`, `CC-218`, `CC-221` | `@typescript-eslint/no-unused-vars`, `no-empty`, `no-useless-return`, `sonarjs/no-dead-store` |
| Long import lists, `CC-246` | `no-restricted-syntax` custom selector over `ImportDeclaration[specifiers.length>10]` |
| Naming consistency, `CC-011`, `CC-025`, `CC-249..CC-255` | `@typescript-eslint/naming-convention` |
| Async precision and type clarity, `CC-235` | `@typescript-eslint/no-floating-promises`, `@typescript-eslint/no-misused-promises`, `@typescript-eslint/switch-exhaustiveness-check`, `eqeqeq` |

## Custom Gap Coverage

These corpus candidates are implemented by the local clean-code plugin:

- commented-out TypeScript code detection: `clean-code/no-commented-out-code`, `CC-083`
- TODO format such as `TODO(PROJ-123): ...`: `clean-code/todo-format`, `CC-068`
- boolean literal arguments at call sites and boolean selector parameters: `clean-code/no-boolean-flag-arguments`, `CC-043`, `CC-208`
- output argument mutation: `clean-code/no-output-argument-mutation`, `CC-207`
- comments that restate the following line: `clean-code/no-redundant-comment`, `CC-071`, `CC-073`
- byline/date comments, separator comments, and closing-brace comments: `clean-code/no-noisy-comments`, `CC-080..CC-082`
- business-policy string/date/status literals: `clean-code/no-business-policy-literals`, `CC-002`, `CC-234`
- Law of Demeter / train-wreck chains: `clean-code/no-train-wrecks`, `CC-106`, `CC-107`, `CC-245`

See [eslint-custom-rules.md](./eslint-custom-rules.md) for rule details.

## Python Config

Python projects should use the Ruff + Pylint config in [python-lint-recommended-config.md](./python-lint-recommended-config.md).
