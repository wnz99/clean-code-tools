#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MCP_SRC = ROOT / "src" / "mcp_server"


def load_mcp_module(module_filename: str, module_name: str) -> ModuleType:
    module_path = MCP_SRC / module_filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_semantic_module() -> ModuleType:
    return load_mcp_module("semantic.py", "clean_code_mcp_semantic")


def load_server_module() -> ModuleType:
    return load_mcp_module("server.py", "clean_code_mcp_server")
