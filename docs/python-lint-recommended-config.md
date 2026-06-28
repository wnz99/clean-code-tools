# Python Recommended Clean-Code Config

Use [configs/python.clean-code.pyproject.toml](../configs/python.clean-code.pyproject.toml) as a reusable `pyproject.toml` fragment for Python projects that want clean-code-oriented linting.

The config intentionally mixes Ruff and Pylint:

- Ruff owns fast local checks: syntax/correctness, imports, bug-prone patterns, simple refactors, commented-out code, TODO shape, unused arguments, return-flow cleanup, magic-value comparisons, and Ruff-specific quality checks.
- Pylint owns broader design pressure: too many module lines, arguments, locals, branches, returns, statements, nested blocks, public methods, instance attributes, duplicate code, cyclic imports, and the custom Python clean-code plugin.

## Install

```bash
python -m pip install clean-code-tools-python
```

Copy the config into a project root as `pyproject.toml`, or merge its `[tool.ruff]`, `[tool.ruff.lint]`, and `[tool.pylint.*]` sections into an existing `pyproject.toml`.

The Python package installs Ruff, Pylint, and the custom Pylint plugin module
`clean_code_tools_pylint`. The canonical reusable config is packaged as
`clean_code_tools_pylint/configs/python.clean-code.pyproject.toml`; this repo
also keeps a copy at [configs/python.clean-code.pyproject.toml](../configs/python.clean-code.pyproject.toml)
for local and JavaScript-package consumers.

Run:

```bash
ruff check .
pylint .
```

## Clean-Code Coverage

| Corpus area | Tool coverage |
| --- | --- |
| Commented-out code, `CC-083` | Ruff `ERA` |
| TODO/FIXME visibility and tracking, `CC-068` | Ruff `TD` |
| Magic numbers / named constants, `CC-018`, `CC-234` | Ruff `PLR2004` |
| Dead and unused code, `CC-209`, `CC-218`, `CC-221` | Ruff `F`, `ARG`, `B` |
| Import readability and ordering, `CC-246` | Ruff `I`, `F401` |
| Return-flow cleanup, `CC-237`, `CC-238` adjacent | Ruff `RET`, `SIM` |
| File, function, and class size pressure, `CC-033..CC-059`, `CC-137..CC-142`, `CC-206` | Pylint `too-many-lines` plus design messages |
| Duplication and coupling signals, `CC-004`, `CC-160`, `CC-214` | Pylint `duplicate-code`, `cyclic-import` |
| Custom clean-code gaps matching the TypeScript plugin, `CC-043`, `CC-050`, `CC-068`, `CC-071`, `CC-073`, `CC-080`, `CC-083`, `CC-106`, `CC-107`, `CC-207`, `CC-208`, `CC-224`, `CC-245` | Pylint plugin `clean-code-*` messages |

## Notes

Ruff does not currently support project-local custom rule plugins, so the config only uses built-in Ruff rule families. Pylint is included because its design checker still provides useful clean-code pressure that Ruff either does not cover or would duplicate less flexibly.

The thresholds are intentionally strict enough to act as early architecture-smell signals: modules warn above 300 lines, functions warn through statement count, and classes warn when public methods or attributes accumulate. Relax them for framework entrypoints, generated code, migrations, tests, and compatibility layers through project-local overrides.

## Remaining Custom Candidates

The remaining custom candidates are mostly domain-specific allowlists and
project-specific suppression policies around the `clean-code-*` messages.

See [python-pylint-custom-rules.md](./python-pylint-custom-rules.md) for the
custom rule details.
