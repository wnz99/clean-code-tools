#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

HTTPX_INSTALL_MESSAGE = "Install httpx to talk to Weaviate: python3 -m pip install httpx"


def require_httpx() -> Any:
    try:
        import httpx  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(HTTPX_INSTALL_MESSAGE) from exc
    return httpx
