# Python Ruff Custom Rules Research

Status: research note before creating any Python recommended config.

## Finding

Ruff is not a custom-rule host in the same way ESLint, Flake8, or Pylint are.

The Ruff FAQ says Ruff implements rules natively and does not support custom or third-party rules:

- https://docs.astral.sh/ruff/faq/

Ruff's contributing guide documents how to add a new lint rule to Ruff itself, not how to load project-local plugins:

- https://docs.astral.sh/ruff/contributing/

Ruff's rules and linter docs are still useful for a recommended Python config because Ruff covers many existing rule families and supports normal `select`, `ignore`, `extend-select`, `per-file-ignores`, and `noqa` workflows:

- https://docs.astral.sh/ruff/rules/
- https://docs.astral.sh/ruff/linter/
- https://docs.astral.sh/ruff/settings/

## Implication

For Python, the likely split is:

1. Use Ruff for existing built-in coverage.
2. Use Pylint or Flake8 only if project-local custom rules are required.
3. Avoid building a custom Ruff plugin because Ruff does not currently expose that extension model.
4. Consider contributing generally useful checks upstream to Ruff only when they are broadly applicable and not project-specific.

## Clean-Code Rule Fit

Likely Ruff-first coverage:

- commented-out code: `ERA`
- TODO / FIXME structure: `FIX`, `TD`
- too many arguments / branches / statements: `PLR`, `C901`
- magic values: `PLR2004`
- unused code: `F`, `ARG`, `B`
- import ordering and style: `I`, `F401`

Likely non-Ruff/custom coverage:

- project-specific TODO format such as `TODO(PROJ-123): ...`
- output-argument mutation as a clean-code smell
- comments that semantically restate the next line
- Law of Demeter / train-wreck navigation with project-specific allowlists
- business-policy literals beyond generic magic values

## Next Python Step

Before creating a Python config, map the clean-code candidates to Ruff rule selectors first, then decide whether the uncovered rules justify Pylint or Flake8 custom plugins.
