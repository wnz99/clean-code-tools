#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    host = os.environ.get("CLEAN_CODE_MCP_HOST", "0.0.0.0")
    port = os.environ.get("CLEAN_CODE_MCP_PORT", "8765")
    subprocess.run(
        [
            sys.executable,
            "scripts/clean_code_mcp_server.py",
            "--transport",
            "http",
            "--host",
            host,
            "--port",
            port,
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
