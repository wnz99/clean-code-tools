#!/usr/bin/env python3
"""Start the installed shared HTTP runtime, reusing an already healthy server."""

import argparse
import sys

from _mcp_app import load_shared_runtime_module

if __name__ == "__main__":
    shared = load_shared_runtime_module()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home")
    parser.add_argument(
        "--check", action="store_true", help="Check readiness without starting a server"
    )
    args = parser.parse_args()
    config = shared.SharedRuntimeConfig.from_environment()
    if args.home:
        config = shared.SharedRuntimeConfig(home=args.home, port=config.port)
    if args.check:
        sys.exit(0 if shared.runtime_health(config) else 1)
    shared.ensure_shared_runtime(config)
