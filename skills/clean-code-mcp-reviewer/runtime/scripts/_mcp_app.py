#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PYTHON_SRC = ROOT / "src" / "python"

if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))


def load_semantic_module() -> ModuleType:
    return importlib.import_module("mcp_server.semantic")


def load_server_module() -> ModuleType:
    return importlib.import_module("mcp_server.server")
