from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import runpy
import sys
import tempfile
import types
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from custom_patterns_test import sample_pattern
from mcp_server import (
    custom_pattern_tools,
    custom_patterns,
    semantic,
    server,
    shared_runtime,
    sqlite_vec_store,
)
from mcp_server.pattern_models import CustomCleanCodePattern
from pydantic import ValidationError
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse


class SharedRuntimeTest(unittest.TestCase):
    def test_real_shared_ingestion_preserves_unlisted_index_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            config = shared_runtime.SharedRuntimeConfig(home=home)
            index = str(home / "clean-code-index.sqlite")
            legacy = home / "runtime/data/custom-clean-code-patterns.jsonl"
            legacy.parent.mkdir(parents=True)
            legacy.write_text(json.dumps(sample_pattern("CUSTOM-101")) + "\n")
            shared = home / "data/custom-clean-code-patterns.jsonl"
            shared.parent.mkdir(parents=True)
            shared.write_text(json.dumps(sample_pattern("CUSTOM-102")) + "\n")
            orphan = custom_patterns.custom_pattern_chunk(
                CustomCleanCodePattern.model_validate(sample_pattern("CUSTOM-103"))
            )
            script = Path(__file__).resolve().parents[2] / "scripts/sqlite_vec_ingest_clean_code.py"
            with (
                patch.dict(os.environ, config.environment()),
                patch.object(sqlite_vec_store, "embed_texts", side_effect=lambda texts, **_: [[1.0, 0.0] for _ in texts]),
                patch.dict(sys.modules, {"_mcp_app": types.SimpleNamespace(load_semantic_module=lambda: semantic)}),
                patch.object(sys, "argv", [str(script), "--index-path", index, "--shared-home", str(home), "--no-reset"]),
            ):
                sqlite_vec_store.ingest_chunks(chunks=[orphan], index_path=index)
                runpy.run_path(str(script), run_name="__main__")
                with sqlite_vec_store.connect_index(index) as connection:
                    ids = {row[0] for row in connection.execute("select chunk_id from chunk_metadata")}
                edited = {**sample_pattern("CUSTOM-101"), "title": "Edited after migration"}
                custom_pattern_tools.upsert_clean_code_pattern_payload(
                    {"pattern": edited, "custom_patterns_path": str(shared), "index_path": index}
                )
                runpy.run_path(str(script), run_name="__main__")
                migrated = custom_patterns.custom_pattern_by_id("CUSTOM-101", path=str(shared))
                self.assertEqual(migrated.title, "Edited after migration")
                custom_pattern_tools.delete_custom_clean_code_pattern_payload(
                    "CUSTOM-101", str(shared), index_path=index
                )
                runpy.run_path(str(script), run_name="__main__")
                self.assertIsNone(custom_patterns.custom_pattern_by_id("CUSTOM-101", path=str(shared)))
                with sqlite_vec_store.connect_index(index) as connection:
                    deleted = connection.execute(
                        "select chunk_id from chunk_metadata where chunk_id = ?",
                        ("custom-pattern:CUSTOM-101",),
                    ).fetchone()
                    self.assertIsNone(deleted)
            for suffix in ("101", "102", "103"):
                self.assertIn(f"custom-pattern:CUSTOM-{suffix}", ids)
            self.assertFalse(legacy.exists())
            self.assertTrue(legacy.with_suffix(".jsonl.migrated").is_file())

    def test_migrate_both_defaults_and_reject_conflicting_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            config = shared_runtime.SharedRuntimeConfig(home=home)
            environment = patch.dict(os.environ, config.environment())
            environment.start()
            self.addCleanup(environment.stop)
            shared = home / "data/custom-clean-code-patterns.jsonl"
            legacy = home / "runtime/data/custom-clean-code-patterns.jsonl"
            shared_runtime.migrate_custom_store(config)
            first = sample_pattern()
            second = {**first, "id": "CUSTOM-002"}
            for path, record in [(shared, first), (legacy, second)]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(record) + "\n")
            before = shared.read_bytes()
            legacy.write_text(json.dumps({**first, "title": "Conflict"}) + "\n")
            with self.assertRaisesRegex(ValueError, "Conflicting custom pattern"):
                shared_runtime.migrate_custom_store(config)
            self.assertEqual(shared.read_bytes(), before)
            self.assertTrue(legacy.exists())
            legacy.write_text(json.dumps(second) + "\n")
            shared_runtime.migrate_custom_store(config)
            self.assertEqual(len(custom_patterns.load_custom_patterns(str(shared))), 2)
            shared_runtime.migrate_custom_store(config)
            before = shared.read_bytes()
            legacy.write_text(json.dumps({**first, "title": "Conflict"}) + "\n")
            with self.assertRaisesRegex(ValueError, "Legacy custom store reappeared"):
                shared_runtime.migrate_custom_store(config)
            self.assertEqual(shared.read_bytes(), before)

    def test_empty_legacy_store_is_archived_once(self):
        legacy = self.config.home / "runtime/data/custom-clean-code-patterns.jsonl"
        legacy.parent.mkdir(parents=True)
        legacy.touch()
        with patch.dict(os.environ, self.config.environment()):
            shared_runtime.migrate_custom_store(self.config)
            shared_runtime.migrate_custom_store(self.config)
        self.assertEqual(legacy.with_suffix(".jsonl.migrated").read_bytes(), b"")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = shared_runtime.SharedRuntimeConfig(home=Path(self.tmp.name))
        self.health = shared_runtime.RuntimeHealth(home=self.config.home, pid=123)

    def test_environment_uses_one_absolute_store_independent_of_client_cwd(self):
        with patch.dict(
            os.environ,
            {"CLEAN_CODE_TOOLS_HOME": str(self.config.home), "CLEAN_CODE_MCP_PORT": "19001"},
        ):
            config = shared_runtime.SharedRuntimeConfig.from_environment()
        self.assertEqual(config.url, "http://127.0.0.1:19001/mcp")
        env = config.environment()
        self.assertEqual(env["CLEAN_CODE_INDEX_BASE"], str(config.home))
        self.assertEqual(env["CLEAN_CODE_CUSTOM_PATTERNS_BASE"], str(config.home))
        self.assertEqual(
            env["CLEAN_CODE_VECTOR_INDEX_PATH"], str(config.home / "clean-code-index.sqlite")
        )
        for port in [0, 65536, "oops"]:
            with self.assertRaises(ValidationError):
                shared_runtime.SharedRuntimeConfig(home=config.home, port=port)

    def test_health_verifies_service_and_home_and_bypasses_proxies(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = (
            self.health.model_dump_json().encode()
        )
        with patch.object(shared_runtime.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(shared_runtime.runtime_health(self.config), self.health)
            opener.open.return_value.__enter__.return_value.read.return_value = (
                shared_runtime.RuntimeHealth(home=self.config.home / "other", pid=123)
                .model_dump_json()
                .encode()
            )
            with self.assertRaisesRegex(RuntimeError, "different"):
                shared_runtime.runtime_health(self.config)
            opener.open.return_value.__enter__.return_value.read.return_value = (
                b'{"service":"other"}'
            )
            with self.assertRaises(ValidationError):
                shared_runtime.runtime_health(self.config)
            opener.open.side_effect = urllib.error.URLError("offline")
            self.assertIsNone(shared_runtime.runtime_health(self.config))

    def test_existing_custom_records_are_reused_without_moving_or_overwriting(self):
        legacy = self.config.home / "data/custom-clean-code-patterns.jsonl"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("existing records\n")
        self.assertEqual(self.config.environment()[shared_runtime.CUSTOM_ENV], str(legacy))
        self.assertEqual(legacy.read_text(), "existing records\n")

    def test_start_reuses_healthy_server_without_spawning(self):
        with (
            patch.object(shared_runtime, "runtime_health", return_value=self.health),
            patch.object(shared_runtime.subprocess, "Popen") as spawn,
        ):
            shared_runtime.ensure_shared_runtime(self.config)
        spawn.assert_not_called()

    def test_start_waits_for_health_and_uses_installed_runtime(self):
        child = MagicMock()
        child.poll.return_value = None
        with (
            patch.object(shared_runtime, "runtime_health", side_effect=[None, None, self.health]),
            patch.object(shared_runtime.subprocess, "Popen", return_value=child) as spawn,
            patch.object(shared_runtime.time, "sleep"),
        ):
            shared_runtime.ensure_shared_runtime(self.config)
        self.assertEqual(spawn.call_args.args[0][-1], "--shared")
        self.assertEqual(spawn.call_args.kwargs["cwd"], self.config.home)
        self.assertEqual(
            spawn.call_args.kwargs["env"]["CLEAN_CODE_TOOLS_HOME"], str(self.config.home)
        )
        child.terminate.assert_not_called()

    def test_failed_start_is_an_error_without_private_fallback(self):
        child = MagicMock()
        child.poll.return_value = 1
        with (
            patch.object(shared_runtime, "runtime_health", return_value=None),
            patch.object(shared_runtime.subprocess, "Popen", return_value=child),
        ):
            with self.assertRaisesRegex(RuntimeError, "startup failed"):
                shared_runtime.ensure_shared_runtime(self.config)

    def test_timeout_reaps_only_the_spawned_child(self):
        for stubborn in [False, True]:
            with self.subTest(stubborn=stubborn):
                child = MagicMock()
                child.poll.return_value = None
                if stubborn:
                    child.wait.side_effect = [
                        shared_runtime.subprocess.TimeoutExpired("server", 5),
                        0,
                    ]
                with (
                    patch.object(shared_runtime, "runtime_health", return_value=None),
                    patch.object(shared_runtime.subprocess, "Popen", return_value=child),
                    patch.object(shared_runtime.time, "monotonic", side_effect=[0, 31]),
                ):
                    with self.assertRaises(TimeoutError):
                        shared_runtime.ensure_shared_runtime(self.config)
                child.terminate.assert_called_once()
                self.assertEqual(child.kill.called, stubborn)

    def test_concurrent_custom_mutations_do_not_lose_records(self):
        store = self.config.home / "custom.jsonl"
        with patch.dict(os.environ, {"CLEAN_CODE_CUSTOM_PATTERNS_BASE": str(self.config.home)}):

            def write(number):
                return custom_pattern_tools.upsert_clean_code_pattern_payload(
                    {
                        "pattern": sample_pattern(f"CUSTOM-{number:03d}"),
                        "custom_patterns_path": str(store),
                        "sync_index": False,
                    }
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(write, range(1, 25)))
            result = custom_pattern_tools.list_custom_clean_code_pattern_payload(str(store))
            self.assertEqual(result["count"], 24)

    def test_shared_server_uses_singleton_lock_and_stateless_transport(self):
        with (
            patch.dict(os.environ, {"CLEAN_CODE_TOOLS_HOME": str(self.config.home)}),
            patch("sys.argv", ["server", "--shared"]),
            patch.object(server.mcp, "run") as run,
        ):
            server.main()
        self.assertEqual(run.call_args.kwargs["host"], "127.0.0.1")
        self.assertTrue(run.call_args.kwargs["stateless_http"])


class LocalHttpTest(unittest.IsolatedAsyncioTestCase):
    async def test_host_origin_and_non_http_scope(self):
        app = shared_runtime.LocalOnlyMiddleware(PlainTextResponse("ok"), port=8765)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1:8765"
        ) as client:
            self.assertEqual((await client.get("/")).status_code, 200)
            self.assertEqual(
                (await client.get("/", headers={"Origin": "http://127.0.0.1:8765"})).status_code,
                200,
            )
            self.assertEqual(
                (await client.get("/", headers={"Origin": "https://evil.test"})).status_code, 403
            )
            self.assertEqual(
                (await client.get("/", headers={"Host": "evil.test:8765"})).status_code, 403
            )
        calls = []

        async def lifespan(scope, receive, send):
            calls.append(scope["type"])

        await shared_runtime.LocalOnlyMiddleware(lifespan, port=8765)(
            {"type": "lifespan"}, None, None
        )
        self.assertEqual(calls, ["lifespan"])

    async def test_two_http_clients_use_same_service_and_validate_tool_inputs(self):
        # Both clients address the same app, without starting per-client subprocesses.
        from starlette.testclient import TestClient

        app = server.mcp.http_app(
            path="/mcp",
            stateless_http=True,
            json_response=True,
            middleware=[Middleware(shared_runtime.LocalOnlyMiddleware, port=8765)],
        )

        def requests():
            with TestClient(app, base_url="http://127.0.0.1:8765") as client:
                health = client.get("/health").json()
                headers = {
                    "Accept": "application/json, text/event-stream",
                    "MCP-Protocol-Version": "2025-03-26",
                }
                for request_id in [1, 2]:
                    response = client.post(
                        "/mcp",
                        headers=headers,
                        json={
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "method": "tools/call",
                            "params": {
                                "name": "get_clean_code_pattern",
                                "arguments": {"pattern_id": "CC-043"},
                            },
                        },
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("CC-043", response.text)
                self.assertEqual(health["pid"], os.getpid())

        await asyncio.to_thread(requests)
