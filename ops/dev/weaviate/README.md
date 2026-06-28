# Local Weaviate

This stack runs a local Weaviate instance for clean-code semantic search.

It uses the same shape as the BusyBots local stack:

- no Weaviate vectorizer module
- anonymous local access
- self-provided vectors inserted by Python tooling
- HTTP on `http://127.0.0.1:8080`
- gRPC on `127.0.0.1:50051`
- persistent Docker volume `clean-code-tools-weaviate_weaviate_data`

## Commands

From the repo root:

```bash
uv sync
bun run weaviate:dev:start
bun run weaviate:dev:smoke
bun run weaviate:dev:status
bun run weaviate:dev:logs
bun run weaviate:dev:stop
```

If port `8080` is already taken:

```bash
WEAVIATE_HTTP_PORT=18080 WEAVIATE_GRPC_PORT=15051 bun run weaviate:dev:start
WEAVIATE_HTTP_PORT=18080 bun run weaviate:dev:smoke
```

The semantic ingestion scripts default to `WEAVIATE_URL=http://127.0.0.1:8080`.
