from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
PYTHON_SRC = ROOT / "src" / "python"
if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from mcp_server import (
    corpus,
    custom_patterns,
    weaviate,
)
from mcp_server.models import MarkdownSection  # noqa: E402
from mcp_server.pattern_models import (  # noqa: E402
    CleanCodePattern,
    CustomCleanCodePattern,
    DeleteCustomPatternRequest,
    ListCustomPatternsRequest,
    UpsertCustomPatternRequest,
)


def sample_pattern(pattern_id: str = "CUSTOM-001") -> dict[str, object]:
    return {
        "id": pattern_id,
        "title": "Prefer Named Payment States",
        "topic": "Domain Rules",
        "rule_family": "naming",
        "aliases": ["payment state", "named status", "domain constant"],
        "problem": "Raw payment status strings make policy drift hard to see.",
        "use_when": "Use when status checks express business policy.",
        "avoid_when": "Avoid when parsing external payloads at the boundary.",
        "good_examples": {
            "typescript": ["if (payment.status === PaymentStatus.Captured) settle(payment);"],
            "python": ["if payment.status is PaymentStatus.CAPTURED:\n    settle(payment)"],
        },
        "bad_examples": {
            "typescript": ["if (payment.status === 'captured') settle(payment);"],
            "python": ["if payment.status == 'captured':\n    settle(payment)"],
        },
        "lint_candidates": ["Flag raw payment status strings outside adapters."],
        "lintability": "high",
        "source": {"kind": "custom", "version": 1},
    }


class TemporaryCustomPatternBase:
    def __init__(self, path: str) -> None:
        self.path = path
        self.original = os.environ.get("CLEAN_CODE_CUSTOM_PATTERNS_BASE")

    def __enter__(self) -> None:
        os.environ["CLEAN_CODE_CUSTOM_PATTERNS_BASE"] = self.path

    def __exit__(self, *_: object) -> None:
        if self.original is None:
            os.environ.pop("CLEAN_CODE_CUSTOM_PATTERNS_BASE", None)
            return
        os.environ["CLEAN_CODE_CUSTOM_PATTERNS_BASE"] = self.original


class CustomPatternModelTest(unittest.TestCase):
    def test_custom_pattern_rejects_builtin_namespace(self) -> None:
        with self.assertRaises(ValidationError):
            CustomCleanCodePattern.model_validate(sample_pattern("CC-999"))

    def test_write_requests_reject_extra_fields_before_writes(self) -> None:
        payload = {"pattern": sample_pattern(), "unexpected": True}
        with self.assertRaises(ValidationError):
            UpsertCustomPatternRequest.model_validate(payload)

    def test_write_requests_reject_unsafe_custom_paths(self) -> None:
        with self.assertRaises(ValidationError):
            UpsertCustomPatternRequest.model_validate(
                {"pattern": sample_pattern(), "custom_patterns_path": "custom.txt"}
            )
        with self.assertRaises(ValidationError):
            ListCustomPatternsRequest.model_validate(
                {"custom_patterns_path": str(ROOT / "data" / "clean-code-patterns.jsonl")}
            )
        with tempfile.TemporaryDirectory() as raw_tmp, self.assertRaises(ValidationError):
            DeleteCustomPatternRequest.model_validate(
                {
                    "pattern_id": "CUSTOM-001",
                    "custom_patterns_path": str(Path(raw_tmp) / "custom.jsonl"),
                }
            )

    def test_default_env_custom_path_is_validated_before_write(self) -> None:
        from mcp_server import server

        original_env_path = os.environ.get("CLEAN_CODE_CUSTOM_PATTERNS_PATH")
        try:
            with tempfile.TemporaryDirectory() as raw_tmp:
                unsafe_path = str(Path(raw_tmp) / "custom-patterns.jsonl")
                os.environ["CLEAN_CODE_CUSTOM_PATTERNS_PATH"] = unsafe_path
                with self.assertRaises(ValueError):
                    server.upsert_clean_code_pattern(sample_pattern(), sync_weaviate=False)
                self.assertFalse(Path(unsafe_path).exists())
        finally:
            if original_env_path is None:
                os.environ.pop("CLEAN_CODE_CUSTOM_PATTERNS_PATH", None)
                return
            os.environ["CLEAN_CODE_CUSTOM_PATTERNS_PATH"] = original_env_path

    def test_delete_request_rejects_builtin_namespace(self) -> None:
        with self.assertRaises(ValidationError):
            DeleteCustomPatternRequest.model_validate({"pattern_id": "CC-001"})

    def test_builtin_pattern_and_example_validators_reject_bad_shapes(self) -> None:
        valid = sample_pattern("CUSTOM-001") | {"id": "CC-999"}
        self.assertEqual(CleanCodePattern.model_validate(valid).id, "CC-999")

        with self.assertRaises(ValidationError):
            CustomCleanCodePattern.model_validate(sample_pattern() | {"aliases": ["one", "", "two"]})
        with self.assertRaises(ValidationError):
            CustomCleanCodePattern.model_validate(
                sample_pattern() | {"lint_candidates": ["duplicate", "duplicate"]}
            )
        with self.assertRaises(ValidationError):
            CustomCleanCodePattern.model_validate(
                sample_pattern() | {"good_examples": {"typescript": "const ok = true;"}}
            )
        with self.assertRaises(ValidationError):
            CustomCleanCodePattern.model_validate(
                sample_pattern()
                | {"bad_examples": {"typescript": "", "python": "bad = True"}}
            )
        with self.assertRaises(ValidationError):
            CustomCleanCodePattern.model_validate(
                sample_pattern()
                | {"bad_examples": {"typescript": [], "python": "bad = True"}}
            )
        with self.assertRaises(ValidationError):
            CustomCleanCodePattern.model_validate(
                sample_pattern()
                | {
                    "bad_examples": {
                        "typescript": ["const bad = true;", "const bad = true;"],
                        "python": "bad = True",
                    }
                }
            )


class CustomPatternStorageTest(unittest.TestCase):
    def test_upsert_list_chunk_and_delete_custom_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp, TemporaryCustomPatternBase(raw_tmp):
            path = str(Path(raw_tmp) / "custom-patterns.jsonl")
            pattern = CustomCleanCodePattern.model_validate(sample_pattern())

            created, stored = custom_patterns.upsert_custom_pattern(pattern, path=path)
            self.assertTrue(created)
            self.assertEqual(stored["id"], "CUSTOM-001")
            self.assertEqual(len(custom_patterns.list_custom_pattern_records(path)), 1)

            updated_pattern = pattern.model_copy(update={"title": "Prefer Named Status Values"})
            created, stored = custom_patterns.upsert_custom_pattern(updated_pattern, path=path)
            self.assertFalse(created)
            self.assertEqual(stored["title"], "Prefer Named Status Values")

            chunk = custom_patterns.custom_pattern_chunk(updated_pattern, path=path)
            self.assertEqual(chunk.chunk_id, "custom-pattern:CUSTOM-001")
            self.assertEqual(chunk.source_kind, "custom_clean_code_pattern")
            self.assertIn("Raw payment status strings", chunk.embedding_text)

            source_rows = [
                json.loads(line)
                for line in Path(path).read_text().splitlines()
                if line.strip()
            ]
            self.assertEqual(source_rows[0]["id"], "CUSTOM-001")

            self.assertTrue(custom_patterns.delete_custom_pattern("CUSTOM-001", path=path))
            self.assertFalse(custom_patterns.delete_custom_pattern("CUSTOM-001", path=path))
            self.assertEqual(custom_patterns.list_custom_pattern_records(path), [])

    def test_corpus_pattern_file_edges(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            pattern_path = tmp / "patterns.jsonl"
            builtin_record = sample_pattern("CUSTOM-001") | {"id": "CC-999"}
            pattern_path.write_text(f"\n{json.dumps(builtin_record)}\n")

            chunks = corpus.pattern_record_chunks(pattern_path)
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].chunk_id, "pattern:CC-999")

            data_dir = tmp / "data"
            data_dir.mkdir()
            (data_dir / "clean-code-patterns.jsonl").write_text(
                f"{json.dumps(builtin_record)}\n"
            )
            self.assertIsNone(corpus.get_pattern_record("CC-000", root=tmp))
            self.assertEqual(
                corpus.markdown_topic(
                    MarkdownSection(
                        source_file="README.md",
                        section_path=(),
                        heading="Fallback Heading",
                        body="",
                        start_line=1,
                        end_line=1,
                    )
                ),
                "Fallback Heading",
            )


class CustomPatternToolTest(unittest.TestCase):
    def test_server_tools_validate_write_and_delete_without_weaviate(self) -> None:
        from mcp_server import server

        with tempfile.TemporaryDirectory() as raw_tmp, TemporaryCustomPatternBase(raw_tmp):
            path = str(Path(raw_tmp) / "custom-patterns.jsonl")
            validation = server.validate_clean_code_pattern(sample_pattern())
            self.assertTrue(validation["valid"])

            upserted = server.upsert_clean_code_pattern(
                sample_pattern(),
                custom_patterns_path=path,
                sync_weaviate=False,
            )
            self.assertTrue(upserted["created"])
            self.assertFalse(upserted["synced_weaviate"])

            listed = server.list_custom_clean_code_patterns(custom_patterns_path=path)
            self.assertEqual(listed["count"], 1)

            deleted = server.delete_custom_clean_code_pattern(
                "CUSTOM-001",
                custom_patterns_path=path,
                sync_weaviate=False,
            )
            self.assertTrue(deleted["deleted"])

    def test_server_write_tools_sync_weaviate_after_validation(self) -> None:
        from mcp_server import server

        calls: list[tuple[str, str]] = []
        original_upsert = server.semantic.upsert_chunk
        original_delete = server.semantic.delete_chunk

        def fake_upsert_chunk(**kwargs: Any) -> None:
            calls.append(("upsert", kwargs["chunk"].chunk_id))

        def fake_delete_chunk(**kwargs: Any) -> bool:
            calls.append(("delete", kwargs["chunk"].chunk_id))
            return True

        server.semantic.upsert_chunk = fake_upsert_chunk
        server.semantic.delete_chunk = fake_delete_chunk
        try:
            with tempfile.TemporaryDirectory() as raw_tmp:
                with TemporaryCustomPatternBase(raw_tmp):
                    path = str(Path(raw_tmp) / "custom-patterns.jsonl")
                    server.upsert_clean_code_pattern(
                        sample_pattern(),
                        custom_patterns_path=path,
                        sync_weaviate=True,
                    )
                    server.delete_custom_clean_code_pattern(
                        "CUSTOM-001",
                        custom_patterns_path=path,
                        sync_weaviate=True,
                    )
        finally:
            server.semantic.upsert_chunk = original_upsert
            server.semantic.delete_chunk = original_delete

        self.assertEqual(
            calls,
            [
                ("upsert", "custom-pattern:CUSTOM-001"),
                ("delete", "custom-pattern:CUSTOM-001"),
            ],
        )

    def test_server_read_tools_and_validation_errors(self) -> None:
        from mcp_server import server

        original_search_chunks = server.search_chunks
        original_search_patterns = server.search_pattern_records
        original_get_pattern = server.get_pattern_record

        def fake_search_chunks(**_: Any) -> list[dict[str, Any]]:
            return [{"chunkId": "x", "contentText": "A useful snippet", "_additional": {}}]

        def fake_search_patterns(**_: Any) -> dict[str, Any]:
            return {
                "no_strong_match": False,
                "results": [
                    {
                        "pattern_id": "CUSTOM-001",
                        "title": "Custom",
                        "rule_family": "naming",
                        "lintability": "high",
                        "confidence": "high",
                        "score": 0.9,
                        "lint_candidates": ["Flag raw statuses."],
                    }
                ],
            }

        def fake_get_pattern(pattern_id: str) -> dict[str, Any] | None:
            if pattern_id == "CC-043":
                return sample_pattern("CUSTOM-001") | {"id": "CC-043"}
            return None

        server.search_chunks = fake_search_chunks
        server.search_pattern_records = fake_search_patterns
        server.get_pattern_record = fake_get_pattern
        try:
            self.assertEqual(server.clean_code_weaviate_schema()["class"], "CleanCodeChunks")
            self.assertEqual(json.loads(server.weaviate_schema())["class"], "CleanCodeChunks")
            pattern_resource = json.loads(server.clean_code_pattern_resource("CC-043"))
            self.assertEqual(pattern_resource["id"], "CC-043")
            self.assertEqual(server.search_clean_code("flag")[0]["chunk_id"], "x")
            self.assertFalse(server.search_clean_code_patterns("flag")["no_strong_match"])
            recommendation = server.recommend_clean_code_lint_rules("flag", language="python")
            self.assertEqual(recommendation["results"][0]["targets"], ["ruff", "pylint", "semgrep"])
            self.assertEqual(server.get_clean_code_pattern("CC-043")["id"], "CC-043")
            with self.assertRaises(ValueError):
                server.search_clean_code(" ")
            with self.assertRaises(ValueError):
                server.search_clean_code("flag", limit=0)
            with self.assertRaises(ValueError):
                server.search_clean_code_patterns(" ")
            with self.assertRaises(ValueError):
                server.search_clean_code_patterns("flag", limit=0)
            with self.assertRaises(ValueError):
                server.get_clean_code_pattern("CUSTOM-001")
            with self.assertRaises(ValueError):
                server.pattern_by_id("CC-999")
            server.search_clean_code_patterns = lambda *_args, **_kwargs: {
                "no_strong_match": True,
                "results": [],
            }
            no_match = server.recommend_clean_code_lint_rules("flag", language="typescript")
            self.assertTrue(no_match["no_strong_match"])
            with self.assertRaises(ValidationError):
                server.upsert_clean_code_pattern(sample_pattern("CC-999"), sync_weaviate=False)
        finally:
            server.search_chunks = original_search_chunks
            server.search_pattern_records = original_search_patterns
            server.get_pattern_record = original_get_pattern

    def test_server_write_tools_do_not_mutate_storage_when_sync_fails(self) -> None:
        from mcp_server import server

        original_upsert = server.semantic.upsert_chunk
        original_delete = server.semantic.delete_chunk

        def failing_upsert_chunk(**_: Any) -> None:
            raise RuntimeError("weaviate unavailable")

        def failing_delete_chunk(**_: Any) -> bool:
            raise RuntimeError("weaviate unavailable")

        try:
            with tempfile.TemporaryDirectory() as raw_tmp:
                with TemporaryCustomPatternBase(raw_tmp):
                    path = str(Path(raw_tmp) / "custom-patterns.jsonl")
                    server.semantic.upsert_chunk = failing_upsert_chunk
                    with self.assertRaises(RuntimeError):
                        server.upsert_clean_code_pattern(
                            sample_pattern(),
                            custom_patterns_path=path,
                            sync_weaviate=True,
                        )
                    self.assertFalse(Path(path).exists())

                    server.semantic.upsert_chunk = original_upsert
                    server.upsert_clean_code_pattern(
                        sample_pattern(),
                        custom_patterns_path=path,
                        sync_weaviate=False,
                    )
                    server.semantic.delete_chunk = failing_delete_chunk
                    with self.assertRaises(RuntimeError):
                        server.delete_custom_clean_code_pattern(
                            "CUSTOM-001",
                            custom_patterns_path=path,
                            sync_weaviate=True,
                        )
                    self.assertEqual(
                        custom_patterns.list_custom_pattern_records(path)[0]["id"],
                        "CUSTOM-001",
                    )
        finally:
            server.semantic.upsert_chunk = original_upsert
            server.semantic.delete_chunk = original_delete

    def test_server_write_tool_does_not_sync_when_local_write_fails(self) -> None:
        from mcp_server import server

        calls: list[str] = []
        original_write = custom_patterns.write_text_atomic
        original_upsert = server.semantic.upsert_chunk

        def failing_write_text_atomic(*_: Any, **__: Any) -> None:
            raise OSError("disk full")

        def fake_upsert_chunk(**_: Any) -> None:
            calls.append("upsert")

        custom_patterns.write_text_atomic = failing_write_text_atomic
        server.semantic.upsert_chunk = fake_upsert_chunk
        try:
            with tempfile.TemporaryDirectory() as raw_tmp:
                with TemporaryCustomPatternBase(raw_tmp):
                    with self.assertRaises(OSError):
                        server.upsert_clean_code_pattern(
                            sample_pattern(),
                            custom_patterns_path=str(Path(raw_tmp) / "custom-patterns.jsonl"),
                            sync_weaviate=True,
                        )
        finally:
            custom_patterns.write_text_atomic = original_write
            server.semantic.upsert_chunk = original_upsert
        self.assertEqual(calls, [])

    def test_default_pattern_search_can_include_custom_patterns(self) -> None:
        from mcp_server import server

        captured: dict[str, Any] = {}
        original_search_patterns = server.search_pattern_records

        def fake_search_patterns(**kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {"no_strong_match": True, "results": []}

        server.search_pattern_records = fake_search_patterns
        try:
            server.search_clean_code_patterns("payment state", language="typescript")
        finally:
            server.search_pattern_records = original_search_patterns
        self.assertEqual(
            captured["source_kinds"],
            ("clean_code_pattern", "custom_clean_code_pattern"),
        )

    def test_get_clean_code_pattern_can_return_custom_pattern(self) -> None:
        from mcp_server import server

        with tempfile.TemporaryDirectory() as raw_tmp, TemporaryCustomPatternBase(raw_tmp):
            path = str(Path(raw_tmp) / "custom-patterns.jsonl")
            server.upsert_clean_code_pattern(
                sample_pattern(),
                custom_patterns_path=path,
                sync_weaviate=False,
            )
            pattern = server.get_clean_code_pattern(
                "CUSTOM-001",
                custom_patterns_path=path,
            )
        self.assertEqual(pattern["id"], "CUSTOM-001")

    def test_server_main_routes_stdio_and_http(self) -> None:
        from mcp_server import server

        original_argv = sys.argv
        original_run = server.mcp.run
        calls: list[dict[str, Any]] = []

        def fake_run(**kwargs: Any) -> None:
            calls.append(kwargs)

        server.mcp.run = fake_run
        try:
            sys.argv = ["server", "--transport", "stdio"]
            server.main()
            sys.argv = [
                "server",
                "--transport",
                "http",
                "--host",
                "0.0.0.0",
                "--port",
                "9999",
            ]
            server.main()
        finally:
            sys.argv = original_argv
            server.mcp.run = original_run
        self.assertEqual(
            calls,
            [{}, {"transport": "http", "host": "0.0.0.0", "port": 9999}],
        )


class WeaviateWriteTest(unittest.TestCase):
    def test_upsert_delete_ingest_reset_and_search_use_http_contracts(self) -> None:
        chunk = custom_patterns.custom_pattern_chunk(
            CustomCleanCodePattern.model_validate(sample_pattern())
        )
        fake_httpx = FakeHttpx()
        original_require_httpx = weaviate.require_httpx
        original_embed_texts = weaviate.embed_texts
        weaviate.require_httpx = lambda: fake_httpx
        weaviate.embed_texts = lambda texts, **_: [[0.1, 0.2] for _text in texts]
        try:
            weaviate.reset_collection(url="http://weaviate", collection_name="CleanCodeChunks")
            self.assertIn(("get", "http://weaviate/v1/schema/CleanCodeChunks"), fake_httpx.calls)
            self.assertIn(("post", "http://weaviate/v1/schema"), fake_httpx.calls)

            fake_httpx.get_status = 200
            weaviate.reset_collection(url="http://weaviate", collection_name="CleanCodeChunks")
            self.assertIn(
                ("delete", "http://weaviate/v1/schema/CleanCodeChunks"),
                fake_httpx.calls,
            )

            inserted = weaviate.ingest_chunks(chunks=[chunk], url="http://weaviate")
            self.assertEqual(inserted, 1)
            self.assertIn(("post", "http://weaviate/v1/batch/objects"), fake_httpx.calls)

            weaviate.upsert_chunk(chunk=chunk, url="http://weaviate")
            self.assertIn(
                ("put", f"http://weaviate/v1/objects/CleanCodeChunks/{chunk.object_id}"),
                fake_httpx.calls,
            )

            self.assertTrue(weaviate.delete_chunk(chunk=chunk, url="http://weaviate"))
            fake_httpx.delete_status = weaviate.HTTP_NOT_FOUND
            self.assertFalse(weaviate.delete_chunk(chunk=chunk, url="http://weaviate"))

            rows = weaviate.search_chunks(query="flag", url="http://weaviate", limit=1)
            self.assertEqual(rows, [{"chunkId": "custom-pattern:CUSTOM-001"}])
            fake_httpx.batch_payload = [{"result": {"status": "FAILED"}}]
            with self.assertRaises(RuntimeError):
                weaviate.ingest_chunks(chunks=[chunk], url="http://weaviate")
            with self.assertRaises(ValueError):
                weaviate.build_search_graphql_query(
                    collection_name="bad-name",
                    vector=[0.1],
                    limit=1,
                )
            with self.assertRaises(RuntimeError):
                weaviate.search_rows_from_payload(
                    {"errors": [{"message": "bad"}]},
                    collection_name="X",
                )
        finally:
            weaviate.require_httpx = original_require_httpx
            weaviate.embed_texts = original_embed_texts

    def test_embed_texts_uses_fastembed_adapter(self) -> None:
        original_fastembed = sys.modules.get("fastembed")

        class FakeEmbedding:
            def __init__(self, model_name: str) -> None:
                self.model_name = model_name

            def embed(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
                return [[float(len(text)), float(batch_size)] for text in texts]

        sys.modules["fastembed"] = types.SimpleNamespace(TextEmbedding=FakeEmbedding)
        try:
            self.assertEqual(
                weaviate.embed_texts(["abc"], model_name="fake", batch_size=7),
                [[3.0, 7.0]],
            )
        finally:
            if original_fastembed is None:
                sys.modules.pop("fastembed", None)
            else:
                sys.modules["fastembed"] = original_fastembed


class FakeResponse:
    def __init__(self, payload: Any | None = None, status_code: int = 200) -> None:
        self._payload = payload if payload is not None else {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return self._payload


class FakeClient:
    def __init__(self, owner: FakeHttpx, timeout: int) -> None:
        self.owner = owner
        self.timeout = timeout

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get(self, url: str) -> FakeResponse:
        self.owner.calls.append(("get", url))
        return FakeResponse(status_code=self.owner.get_status)

    def delete(self, url: str) -> FakeResponse:
        self.owner.calls.append(("delete", url))
        return FakeResponse(status_code=self.owner.delete_status)

    def post(self, url: str, *, json: Any) -> FakeResponse:
        self.owner.calls.append(("post", url))
        if url.endswith("/v1/batch/objects"):
            return FakeResponse(self.owner.batch_payload)
        return FakeResponse({"ok": True})


class FakeHttpx:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.batch_payload: list[dict[str, object]] = [{"result": {"status": "SUCCESS"}}]
        self.delete_status = 200
        self.get_status = weaviate.HTTP_NOT_FOUND

    def Client(self, *, timeout: int) -> FakeClient:
        return FakeClient(self, timeout)

    def put(self, url: str, *, json: Any, timeout: int) -> FakeResponse:
        self.calls.append(("put", url))
        return FakeResponse({"ok": True})

    def delete(self, url: str, *, timeout: int) -> FakeResponse:
        self.calls.append(("delete", url))
        return FakeResponse(status_code=self.delete_status)

    def post(self, url: str, *, json: Any, timeout: int) -> FakeResponse:
        self.calls.append(("post", url))
        if url.endswith("/v1/graphql"):
            return FakeResponse(
                {
                    "data": {
                        "Get": {
                            "CleanCodeChunks": [
                                {"chunkId": "custom-pattern:CUSTOM-001"},
                            ]
                        }
                    }
                }
            )
        return FakeResponse({"ok": True})


if __name__ == "__main__":
    unittest.main()
