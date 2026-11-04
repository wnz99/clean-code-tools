from __future__ import annotations

import asyncio
import concurrent.futures
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from pydantic import ValidationError
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse

from mcp_server import custom_pattern_tools, server, shared_runtime
from custom_patterns_test import sample_pattern


class SharedRuntimeTest(unittest.TestCase):
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
