# Publishing

This repo publishes two native package shapes from the same source tree.

## Registries

- npm registry: `clean-code-tools`
- PyPI: `clean-code-tools-python`

These are production registry names. If either name is already taken, rename the
package in `package.json` or `pyproject.toml` before the first publish.

## TypeScript / ESLint

The npm package exposes:

- `clean-code-tools`
- `clean-code-tools/eslint-plugin`
- `clean-code-tools/configs/eslint.clean-code.recommended.mjs`
- `clean-code-tools/configs/python.clean-code.pyproject.toml`

Before publishing:

```bash
bun run check:packages
npm publish --dry-run
```

The package must not set `private: true`; otherwise npm refuses publication. The
GitHub Actions workflows use npm trusted publishing with provenance, so configure
the npm package's trusted publisher to allow this repository and these workflow
files:

- `.github/workflows/publish-main.yml`

The workflows use Node 24 so the bundled npm supports trusted publishing.
npm provenance can be re-enabled with `--provenance` if this repository is
public; npm rejects provenance for private GitHub repositories.

## Python / Pylint

The PyPI package is `clean-code-tools-python`. It installs:

- the `clean_code_tools_pylint` plugin package
- Ruff and Pylint runtime dependencies
- the reusable config as package data at
  `clean_code_tools_pylint/configs/python.clean-code.pyproject.toml`

Before publishing:

```bash
bun run check:packages
uv build
uv publish --dry-run
```

Configure PyPI trusted publishers for this repository and these workflow files:

- `.github/workflows/publish-main.yml`

The workflows use `uv publish --trusted-publishing always`, so no PyPI token is
stored in GitHub secrets.

The package smoke check builds a wheel, installs it into an isolated virtualenv,
loads the packaged config through `importlib.resources`, then runs Ruff and
Pylint against a fixture that must trigger the custom `clean-code-*` messages.

## Versioning

The source manifests keep a stable release base:

- `package.json`
- `pyproject.toml`

Use `scripts/set_package_versions.py` to update them together:

```bash
uv run python scripts/set_package_versions.py --release 1.2.3
uv run python scripts/set_package_versions.py --bump patch --base 1.2.3
```

`bun run check:packages` requires exact version parity between npm and Python.
Packages are never given a development suffix.

Every push or merge to `develop` runs `.github/workflows/version-develop.yml`.
It reads the latest `vX.Y.Z` tag, bumps the patch version, writes that version to
`package.json` and `pyproject.toml`, runs the full check, then commits the
version update back to `develop` and creates a matching `vX.Y.Z` tag on that
develop commit.

Publishing happens only from `main`. Merge `develop` into `main` after the
versioning workflow has created the version commit and tag. A push to `main`
runs `.github/workflows/publish-main.yml`, verifies that the manifest version has
a matching `vX.Y.Z` tag reachable from `main`, runs the full check, then
publishes npm `latest` plus the PyPI final release.

If a change needs a minor or major bump, run the version script manually on
`develop` before merging, or adjust the workflow bump type for that release.

## SemVer Policy

Publish the Python package and npm package with matching versions when rule
semantics change. Patch-only documentation or packaging fixes can ship
independently if the lint behavior is unchanged.

The package check enforces version parity between `package.json` and
`pyproject.toml`, so bump both manifests in the same release change.

Use SemVer for both registries:

- patch: documentation, packaging, or false-positive tuning that reduces noise
- minor: new rules, new recommended warnings, or new MCP candidate mappings
- major: removed rules, renamed public exports, or stricter defaults that create
  a large new failure surface

## References

- npm publishing and trusted publishing:
  <https://docs.github.com/en/actions/tutorials/publish-packages/publish-nodejs-packages>
- npm package versions are immutable after publish:
  <https://docs.npmjs.com/cli/v11/commands/npm-publish/>
- PyPI trusted publishing:
  <https://docs.pypi.org/trusted-publishers/adding-a-publisher/>
- GitHub OIDC setup for PyPI:
  <https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-pypi>
- uv publishing with trusted publishers:
  <https://docs.astral.sh/uv/guides/package/>
