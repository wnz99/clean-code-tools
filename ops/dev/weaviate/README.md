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
npm run weaviate:dev:start
npm run weaviate:dev:smoke
npm run weaviate:dev:status
npm run weaviate:dev:logs
npm run weaviate:dev:stop
```

If port `8080` is already taken:

```bash
WEAVIATE_HTTP_PORT=18080 WEAVIATE_GRPC_PORT=15051 npm run weaviate:dev:start
WEAVIATE_HTTP_PORT=18080 npm run weaviate:dev:smoke
```

The semantic ingestion scripts default to `WEAVIATE_URL=http://127.0.0.1:8080`.
