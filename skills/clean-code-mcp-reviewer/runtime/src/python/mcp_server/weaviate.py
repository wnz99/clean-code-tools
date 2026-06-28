#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re

from mcp_server.models import DEFAULT_EMBEDDING_MODEL, CleanCodeChunk, JsonDict
from mcp_server.utils.httpx_loader import require_httpx

COLLECTION_NAME = "CleanCodeChunks"
VECTOR_NAME = "content"
DEFAULT_WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://127.0.0.1:8080")  # pylint: disable=clean-code-business-policy-literal
DEFAULT_BATCH_SIZE = 64
HTTP_NOT_FOUND = 404
GRAPHQL_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FASTEMBED_INSTALL_MESSAGE = "Install fastembed to embed clean-code chunks: python3 -m pip install fastembed"


def create_schema_payload(*, collection_name: str = COLLECTION_NAME) -> JsonDict:
    return {
        "class": collection_name,
        "vectorConfig": {
            VECTOR_NAME: {
                "vectorIndexType": "hnsw",
                "vectorizer": {"none": {}},
            }
        },
        "properties": [
            {"name": "chunkId", "dataType": ["text"]},
            {"name": "sourceFile", "dataType": ["text"]},
            {"name": "sourceKind", "dataType": ["text"]},
            {"name": "recordId", "dataType": ["text"]},
            {"name": "title", "dataType": ["text"]},
            {"name": "topic", "dataType": ["text"]},
            {"name": "sectionPath", "dataType": ["text[]"]},
            {"name": "chunkKind", "dataType": ["text"]},
            {"name": "chunkIndex", "dataType": ["number"]},
            {"name": "ruleFamily", "dataType": ["text"]},
            {"name": "lintability", "dataType": ["text"]},
            {"name": "aliases", "dataType": ["text[]"]},
            {"name": "languages", "dataType": ["text[]"]},
            {"name": "lintCandidates", "dataType": ["text[]"]},
            {"name": "contentText", "dataType": ["text"]},
            {"name": "embeddingText", "dataType": ["text"]},
            {"name": "displayText", "dataType": ["text"]},
            {"name": "textHash", "dataType": ["text"]},
            {"name": "chunkerVersion", "dataType": ["text"]},
            {"name": "embeddingModel", "dataType": ["text"]},
            {"name": "embeddingProvider", "dataType": ["text"]},
            {"name": "createdAt", "dataType": ["date"]},
        ],
    }


def reset_collection(*, url: str, collection_name: str = COLLECTION_NAME) -> None:
    httpx = require_httpx()
    base_url = url.rstrip("/")
    with httpx.Client(timeout=120) as client:
        existing = client.get(f"{base_url}/v1/schema/{collection_name}")
        if existing.status_code != HTTP_NOT_FOUND:
            existing.raise_for_status()
            deleted = client.delete(f"{base_url}/v1/schema/{collection_name}")
            deleted.raise_for_status()
        created = client.post(
            f"{base_url}/v1/schema",
            json=create_schema_payload(collection_name=collection_name),
        )
        created.raise_for_status()


def embed_texts(texts: list[str], *, model_name: str, batch_size: int) -> list[list[float]]:
    try:
        from fastembed import TextEmbedding  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(FASTEMBED_INSTALL_MESSAGE) from exc
    model = TextEmbedding(model_name=model_name)
    return [[float(value) for value in vector] for vector in model.embed(texts, batch_size=batch_size)]


def ingest_chunks(
    *,
    chunks: list[CleanCodeChunk],
    url: str,
    collection_name: str = COLLECTION_NAME,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    httpx = require_httpx()
    base_url = url.rstrip("/")
    inserted = 0
    with httpx.Client(timeout=120) as client:
        for offset in range(0, len(chunks), batch_size):
            batch = chunks[offset : offset + batch_size]
            vectors = embed_texts(
                [chunk.embedding_text for chunk in batch],
                model_name=model_name,
                batch_size=batch_size,
            )
            objects = [
                {
                    "class": collection_name,
                    "id": chunk.object_id,
                    "properties": chunk.properties,
                    "vectors": {VECTOR_NAME: vector},
                }
                for chunk, vector in zip(batch, vectors, strict=True)
            ]
            response = client.post(f"{base_url}/v1/batch/objects", json={"objects": objects})
            response.raise_for_status()
            failures = batch_failures(response.json())
            if failures:
                raise RuntimeError(f"Weaviate rejected {len(failures)} objects: {failures[:3]}")  # noqa: TRY003  # pylint: disable=clean-code-business-policy-literal
            inserted += len(batch)
    return inserted


def search_chunks(
    *,
    query: str,
    url: str,
    collection_name: str = COLLECTION_NAME,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    limit: int = 8,
) -> list[JsonDict]:
    vector = embed_query(query, model_name=model_name)
    graphql_query = build_search_graphql_query(
        collection_name=collection_name,
        vector=vector,
        limit=limit,
    )
    payload = execute_graphql_search(url=url, graphql_query=graphql_query)
    return search_rows_from_payload(payload, collection_name=collection_name)


def embed_query(query: str, *, model_name: str) -> list[float]:
    return embed_texts([query], model_name=model_name, batch_size=1)[0]


def execute_graphql_search(*, url: str, graphql_query: str) -> JsonDict:
    httpx = require_httpx()
    response = httpx.post(f"{url.rstrip('/')}/v1/graphql", json={"query": graphql_query}, timeout=120)
    response.raise_for_status()
    return response.json()


def search_rows_from_payload(payload: JsonDict, *, collection_name: str) -> list[JsonDict]:
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload.get("data", {}).get("Get", {}).get(collection_name, [])


def build_search_graphql_query(
    *,
    collection_name: str,
    vector: list[float],
    limit: int,
) -> str:
    if not GRAPHQL_NAME_RE.fullmatch(collection_name):
        raise ValueError("collection_name must be a valid GraphQL identifier")  # noqa: TRY003
    return (
        "{ Get { "
        f"{collection_name}("
        f"nearVector: {{vector: {json.dumps(vector)}, targetVectors: [{json.dumps(VECTOR_NAME)}]}}, "
        f"limit: {limit}"
        ") { "
        "chunkId recordId sourceFile sourceKind title topic sectionPath chunkKind "
        "ruleFamily lintability aliases languages lintCandidates contentText textHash "
        "_additional { id distance } "
        "} } }"
    )


def batch_failures(payload: JsonDict) -> list[JsonDict]:
    rows = payload if isinstance(payload, list) else payload.get("objects", [])
    return [row for row in rows if isinstance(row, dict) and not is_successful_batch_row(row)]


def is_successful_batch_row(row: JsonDict) -> bool:
    result = row.get("result")
    status = result.get("status") if isinstance(result, dict) else row.get("status")
    return isinstance(status, str) and status.upper() in {"SUCCESS", "OK"}  # pylint: disable=clean-code-business-policy-literal
