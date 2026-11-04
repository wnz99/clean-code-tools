#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

from _mcp_app import load_server_module, load_shared_runtime_module

if __name__ == "__main__":
    if "--shared" in sys.argv:
        shared = load_shared_runtime_module()
        os.environ.update(shared.SharedRuntimeConfig.from_environment().environment())
    load_server_module().main()
