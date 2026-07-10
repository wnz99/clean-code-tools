#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from mcp_server.corpus import build_chunks
from mcp_server.models import DEFAULT_EMBEDDING_MODEL, CleanCodeChunk, JsonDict

INDEX_SCHEMA_VERSION = "clean-code-sqlite-vec-v1"
DEFAULT_BATCH_SIZE = 64
VECTOR_INDEX_PATH_ENV_VAR = "CLEAN_CODE_VECTOR_INDEX_PATH"
RUNTIME_HOME = Path(__file__).resolve().parents[4]
DEFAULT_INDEX_PATH = os.environ.get(VECTOR_INDEX_PATH_ENV_VAR, str(RUNTIME_HOME / "clean-code-index.sqlite"))
FASTEMBED_CACHE_PATH = RUNTIME_HOME / "cache" / "fastembed"
SQLITE_VEC_INSTALL_MESSAGE = (
    "Install sqlite-vec to use local clean-code vector search: python3 -m pip install sqlite-vec"
)
FASTEMBED_INSTALL_MESSAGE = "Install fastembed to embed clean-code chunks: python3 -m pip install fastembed"
INDEX_NOT_READY_MESSAGE = "Clean-code sqlite-vec index is not ready. Build it first with scripts/sqlite_vec_ingest_clean_code.py."
QUERY_DIMENSION_MISMATCH_TEMPLATE = (
    "query embedding has {dimensions} dimensions, but index uses {stored_dimensions}; "
    "rebuild the index with the same model used for search"
)
CHUNK_DIMENSION_MISMATCH_TEMPLATE = (
    "chunk embedding has {dimensions} dimensions, but index uses {stored_dimensions}; "
    "rebuild the index with the same model before syncing custom patterns"
)


def connect_index(index_path: str = DEFAULT_INDEX_PATH) -> sqlite3.Connection:
    try:
        import sqlite_vec  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(SQLITE_VEC_INSTALL_MESSAGE) from exc
    path = Path(index_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    allow_sqlite_extensions(connection)
    sqlite_vec.load(connection)
    return connection


def allow_sqlite_extensions(connection: sqlite3.Connection) -> None:
    # SQLite exposes extension loading as an unavoidable boolean-toggle API.
    # pylint: disable-next=clean-code-boolean-flag-argument
    connection.enable_load_extension(True)  # noqa: FBT003


def create_index_info(*, index_path: str = DEFAULT_INDEX_PATH) -> JsonDict:
    return {
        "backend": "sqlite-vec",
        "schema_version": INDEX_SCHEMA_VERSION,
        "index_path": str(Path(index_path).expanduser()),
        "tables": {
            "vec_chunks": {"kind": "sqlite-vec virtual table", "columns": ["chunk_id", "embedding"]},
            "chunk_metadata": {"kind": "sqlite table", "columns": ["chunk_id", "object_id", "payload"]},
        },
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
    }


def reset_index(*, index_path: str = DEFAULT_INDEX_PATH, vector_dimensions: int = 384) -> None:
    path = Path(index_path).expanduser()
    path.unlink(missing_ok=True)
    path.with_suffix(path.suffix + "-wal").unlink(missing_ok=True)
    path.with_suffix(path.suffix + "-shm").unlink(missing_ok=True)
    with connect_index(str(path)) as connection:
        create_tables(connection, vector_dimensions=vector_dimensions)


def create_tables(connection: sqlite3.Connection, *, vector_dimensions: int) -> None:
    connection.execute(
        f"create virtual table if not exists vec_chunks using vec0("
        f"chunk_id text primary key, embedding float[{vector_dimensions}])"
    )
    connection.execute(
        "create table if not exists chunk_metadata("
        "chunk_id text primary key, object_id text not null, payload text not null)"
    )
    connection.execute("create table if not exists index_metadata(key text primary key, value text not null)")
    connection.execute(
        "insert or replace into index_metadata(key, value) values (?, ?)",
        ("schema_version", INDEX_SCHEMA_VERSION),
    )
    connection.execute(
        "insert or replace into index_metadata(key, value) values (?, ?)",
        ("vector_dimensions", str(vector_dimensions)),
    )
    connection.commit()


def embed_texts(texts: list[str], *, model_name: str, batch_size: int) -> list[list[float]]:
    try:
        from fastembed import TextEmbedding  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(FASTEMBED_INSTALL_MESSAGE) from exc
    model = TextEmbedding(model_name=model_name, cache_dir=str(FASTEMBED_CACHE_PATH))
    return [[float(value) for value in vector] for vector in model.embed(texts, batch_size=batch_size)]


def ingest_chunks(
    *,
    chunks: list[CleanCodeChunk],
    index_path: str = DEFAULT_INDEX_PATH,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    reset: bool = True,
) -> int:
    if not chunks:
        if reset:
            reset_index(index_path=index_path)
        return 0
    vectors = embed_texts(
        [chunk.embedding_text for chunk in chunks],
        model_name=model_name,
        batch_size=batch_size,
    )
    if reset:
        reset_index(index_path=index_path, vector_dimensions=len(vectors[0]))
    with connect_index(index_path) as connection:
        create_tables(connection, vector_dimensions=len(vectors[0]))
        write_chunks(connection, chunks=chunks, vectors=vectors)
    return len(chunks)


def write_chunks(
    connection: sqlite3.Connection,
    *,
    chunks: list[CleanCodeChunk],
    vectors: list[list[float]],
) -> None:
    chunk_ids = [(chunk.chunk_id,) for chunk in chunks]
    connection.executemany("delete from vec_chunks where chunk_id = ?", chunk_ids)
    connection.executemany("delete from chunk_metadata where chunk_id = ?", chunk_ids)
    connection.executemany(
        "insert into vec_chunks(chunk_id, embedding) values (?, ?)",
        [
            (chunk.chunk_id, vector_json(vector)) for chunk, vector in zip(chunks, vectors, strict=True)
        ],
    )
    connection.executemany(
        "insert or replace into chunk_metadata(chunk_id, object_id, payload) values (?, ?, ?)",
        [
            (
                chunk.chunk_id,
                chunk.object_id,
                json.dumps(chunk.properties, separators=(",", ":")),
            )
            for chunk in chunks
        ],
    )
    connection.commit()


def ensure_index(
    *,
    index_path: str = DEFAULT_INDEX_PATH,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> None:
    path = Path(index_path).expanduser()
    if index_has_chunks(path):
        return
    ingest_chunks(
        chunks=build_chunks(),
        index_path=str(path),
        model_name=model_name,
        batch_size=batch_size,
        reset=True,
    )


def index_has_chunks(index_path: Path) -> bool:
    if not index_path.exists():
        return False
    try:
        with sqlite3.connect(index_path) as connection:
            row = connection.execute("select count(*) from chunk_metadata").fetchone()
    except sqlite3.Error:
        return False
    return bool(row and row[0])


def upsert_chunk(
    *,
    chunk: CleanCodeChunk,
    index_path: str = DEFAULT_INDEX_PATH,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> None:
    vector = embed_texts([chunk.embedding_text], model_name=model_name, batch_size=1)[0]
    validate_write_dimensions(index_path=index_path, dimensions=len(vector))
    with connect_index(index_path) as connection:
        create_tables(connection, vector_dimensions=len(vector))
        write_chunks(connection, chunks=[chunk], vectors=[vector])


def delete_chunk(
    *,
    chunk: CleanCodeChunk,
    index_path: str = DEFAULT_INDEX_PATH,
) -> bool:
    with connect_index(index_path) as connection:
        before = connection.total_changes
        connection.execute("delete from vec_chunks where chunk_id = ?", (chunk.chunk_id,))
        connection.execute("delete from chunk_metadata where chunk_id = ?", (chunk.chunk_id,))
        connection.commit()
        return connection.total_changes > before


def search_chunks(
    *,
    query: str,
    index_path: str = DEFAULT_INDEX_PATH,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    limit: int = 8,
) -> list[JsonDict]:
    require_ready_index(index_path)
    vector = embed_query(query, model_name=model_name)
    validate_query_dimensions(index_path=index_path, dimensions=len(vector))
    with connect_index(index_path) as connection:
        rows = connection.execute(
            """
            select m.object_id, m.payload, v.distance
            from vec_chunks v
            join chunk_metadata m on m.chunk_id = v.chunk_id
            where v.embedding match ? and k = ?
            order by v.distance
            """,
            (vector_json(vector), limit),
        ).fetchall()
    return search_rows_from_sqlite(rows)


def require_ready_index(index_path: str) -> None:
    path = Path(index_path).expanduser()
    if not index_has_chunks(path):
        raise ValueError(INDEX_NOT_READY_MESSAGE)


def validate_query_dimensions(*, index_path: str, dimensions: int) -> None:
    stored_dimensions = stored_vector_dimensions(index_path)
    if stored_dimensions is None:
        return
    if stored_dimensions != dimensions:
        raise ValueError(
            QUERY_DIMENSION_MISMATCH_TEMPLATE.format(dimensions=dimensions, stored_dimensions=stored_dimensions)
        )


def validate_write_dimensions(*, index_path: str, dimensions: int) -> None:
    stored_dimensions = stored_vector_dimensions(index_path)
    if stored_dimensions is None:
        return
    if stored_dimensions != dimensions:
        raise ValueError(
            CHUNK_DIMENSION_MISMATCH_TEMPLATE.format(dimensions=dimensions, stored_dimensions=stored_dimensions)
        )


def stored_vector_dimensions(index_path: str) -> int | None:
    path = Path(index_path).expanduser()
    if not path.exists():
        return None
    with sqlite3.connect(Path(index_path).expanduser()) as connection:
        try:
            row = connection.execute(
                "select value from index_metadata where key = ?",
                ("vector_dimensions",),
            ).fetchone()
        except sqlite3.Error:
            return None
    return int(row[0]) if row else None


def embed_query(query: str, *, model_name: str) -> list[float]:
    return embed_texts([query], model_name=model_name, batch_size=1)[0]


def search_rows_from_sqlite(rows: list[tuple[str, str, float]]) -> list[JsonDict]:
    results: list[JsonDict] = []
    for object_id, payload, distance in rows:
        row = json.loads(payload)
        row["_additional"] = {"id": object_id, "distance": float(distance)}
        results.append(row)
    return results


def vector_json(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.9g}" for value in vector) + "]"
