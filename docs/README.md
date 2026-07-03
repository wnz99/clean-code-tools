# Documentation Index

Production-facing docs for clean-code lint packages, MCP pattern lookup, and
release operations.

## Package Usage

- [ESLint recommended config](./eslint-recommended-config.md): install and use
  the TypeScript ESLint preset from the npm package.
- [ESLint custom rules](./eslint-custom-rules.md): project-owned TypeScript
  clean-code rules included in the ESLint plugin.
- [Python recommended config](./python-lint-recommended-config.md): install and
  use the Ruff, Pylint, and Deptry config from the Python package.
- [Python custom Pylint rules](./python-pylint-custom-rules.md): project-owned
  Python clean-code rules exposed by the Pylint plugin.

## Agent And MCP Workflows

- [FastMCP local server](./fastmcp-local-server.md): run the local MCP server,
  inspect exposed tools, and query clean-code patterns from an agent.
- [Semantic Weaviate search](./semantic-weaviate.md): run local Weaviate,
  ingest the pattern corpus, and test semantic retrieval.
- [Static trigger to semantic review](./static-trigger-semantic-review.md):
  convert deterministic lint output into clean-code MCP review candidates.

## Operations

- [Publishing](./publishing.md): package registry setup, branch flow, automated
  versioning on `develop`, and publishing on `main`.
