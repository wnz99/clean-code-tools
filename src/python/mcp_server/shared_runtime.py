"""One local HTTP runtime, with bounded startup and no per-agent proxy process."""

from __future__ import annotations

import argparse
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from filelock import FileLock
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from fastmcp import FastMCP

PORT_OWNER_ERROR = "The MCP port belongs to a different clean-code runtime"
START_ERROR = "Shared MCP startup failed; inspect shared-server.log"
TIMEOUT_ERROR = "Shared MCP startup timed out; inspect shared-server.log"
HOME_ENV = "CLEAN_CODE_TOOLS_HOME"
PORT_ENV = "CLEAN_CODE_MCP_PORT"
INDEX_BASE_ENV = "CLEAN_CODE_INDEX_BASE"
INDEX_ENV = "CLEAN_CODE_VECTOR_INDEX_PATH"
CUSTOM_BASE_ENV = "CLEAN_CODE_CUSTOM_PATTERNS_BASE"
CUSTOM_ENV = "CLEAN_CODE_CUSTOM_PATTERNS_PATH"
HTTP_GET = "GET"


class SharedRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    home: Path
    port: int = Field(default=8765, ge=1, le=65535)

    @field_validator("home")
    @classmethod
    def absolute_home(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @classmethod
    def from_environment(cls) -> SharedRuntimeConfig:
        return cls.model_validate(
            {
                "home": Path(os.environ.get(HOME_ENV, "~/.clean-code-tools"))
                .expanduser()
                .resolve(),
                "port": os.environ.get(PORT_ENV, "8765"),
            }
        )

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"

    def environment(self) -> dict[str, str]:
        return {
            **os.environ,
            HOME_ENV: str(self.home),
            PORT_ENV: str(self.port),
            INDEX_BASE_ENV: str(self.home),
            INDEX_ENV: str(self.home / "clean-code-index.sqlite"),
            CUSTOM_BASE_ENV: str(self.home),
            CUSTOM_ENV: str(self.home / "data/custom-clean-code-patterns.jsonl"),
        }


class RuntimeHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: Literal["clean-code-tools"] = "clean-code-tools"
    home: Path
    pid: int = Field(gt=0)


def migrate_custom_store(config: SharedRuntimeConfig) -> None:
    """Merge the historical default once, retaining its consumed input as a backup."""
    from mcp_server.custom_patterns import (  # noqa: PLC0415
        load_custom_patterns,
        write_custom_patterns,
    )

    destination = config.home / "data/custom-clean-code-patterns.jsonl"
    legacy = config.home / "runtime/data/custom-clean-code-patterns.jsonl"
    archive = legacy.with_suffix(".jsonl.migrated")
    if not legacy.exists():
        return
    if archive.exists():
        message = f"Legacy custom store reappeared after migration: {legacy}; reconcile it with {destination} and {archive}"
        raise ValueError(message)
    records = {}
    for record in [*load_custom_patterns(str(destination)), *load_custom_patterns(str(legacy))]:
        existing = records.get(record.id)
        if existing is not None and existing != record:
            message = f"Conflicting custom pattern {record.id}: {legacy} and {destination}"
            raise ValueError(message)
        records[record.id] = record
    if records:
        write_custom_patterns(list(records.values()), path=str(destination))
    # Preserve the source until the destination write succeeds.
    legacy.rename(archive)


def register_shared_health(server: FastMCP) -> None:
    @server.custom_route("/health", methods=[HTTP_GET])
    async def health(_request: Request) -> JSONResponse:
        config = SharedRuntimeConfig.from_environment()
        return JSONResponse(
            RuntimeHealth(home=config.home, pid=os.getpid()).model_dump(mode="json")
        )


def serve_shared(server: FastMCP) -> None:
    config = SharedRuntimeConfig.from_environment()
    config.home.mkdir(parents=True, exist_ok=True)
    with FileLock(str(config.home / "shared-server.lock"), timeout=0):
        server.run(
            transport="http",
            host="127.0.0.1",
            port=config.port,
            path="/mcp",
            stateless_http=True,
            json_response=True,
            middleware=[Middleware(LocalOnlyMiddleware, port=config.port)],
        )


def parse_server_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the clean-code FastMCP server.")
    parser.add_argument(
        "--shared", action="store_true", help="Run the singleton local HTTP runtime"
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse"),
        default="stdio",
        help="FastMCP transport to run.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args()


class LocalOnlyMiddleware:
    """Reject DNS rebinding and browser requests from unrelated origins."""

    def __init__(self, app: ASGIApp, port: int) -> None:
        self.app = app
        self.hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.origins = {f"http://{host}" for host in self.hosts}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = [(key.lower(), value.decode("latin-1")) for key, value in scope["headers"]]
            hosts = [value for key, value in headers if key == b"host"]
            origins = [value for key, value in headers if key == b"origin"]
            if (
                len(hosts) != 1
                or hosts[0] not in self.hosts
                or any(origin not in self.origins for origin in origins)
            ):
                await PlainTextResponse("Local MCP requests only", status_code=403)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)


def runtime_health(config: SharedRuntimeConfig) -> RuntimeHealth | None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(config.url.removesuffix("/mcp") + "/health", timeout=1) as response:
            health = RuntimeHealth.model_validate_json(response.read(4096))
    except (urllib.error.URLError, TimeoutError):
        return None
    if health.home.resolve() != config.home.resolve():
        raise RuntimeError(PORT_OWNER_ERROR)
    return health


def wait_for_runtime(config: SharedRuntimeConfig, child: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if runtime_health(config):
            return
        if child.poll() is not None:
            raise RuntimeError(START_ERROR)
        time.sleep(0.1)
    raise TimeoutError(TIMEOUT_ERROR)


def ensure_shared_runtime(config: SharedRuntimeConfig) -> None:
    """Start once, wait for readiness, or fail without creating a private server."""
    config.home.mkdir(parents=True, exist_ok=True)
    with FileLock(str(config.home / "shared-start.lock"), timeout=35):
        if runtime_health(config):
            return
        script = config.home / "runtime/scripts/clean_code_mcp_server.py"
        python = config.home / (
            ".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"
        )
        with (config.home / "shared-server.log").open("ab") as log:
            child = subprocess.Popen(  # noqa: S603
                [str(python), str(script), "--shared"],
                cwd=config.home,
                env=config.environment(),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        try:
            wait_for_runtime(config, child)
        except BaseException:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            raise
