#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import time

import httpx

SERVER_ERROR_STATUS = 500


def wait_for_weaviate(url: str, *, timeout_seconds: int = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    ready_url = f"{url.rstrip('/')}/v1/.well-known/ready"
    while time.monotonic() < deadline:
        try:
            response = httpx.get(ready_url, timeout=5)
            if response.status_code < SERVER_ERROR_STATUS:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise SystemExit(f"Weaviate did not become ready at {ready_url}")


def main() -> None:
    weaviate_url = os.environ.get("WEAVIATE_URL", "http://weaviate:8080")
    reset = os.environ.get("CLEAN_CODE_MCP_RESET_WEAVIATE", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    wait_for_weaviate(weaviate_url)
    command = [
        sys.executable,
        "scripts/weaviate_ingest_clean_code.py",
        "--url",
        weaviate_url,
    ]
    if reset:
        command.append("--reset")
    print(f"running: {' '.join(command)}", flush=True)
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
