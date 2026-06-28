#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "package.json"
PYPROJECT = ROOT / "pyproject.toml"
RELEASE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[a-zA-Z0-9.-]+)?$")
CORE_VERSION_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
PYPROJECT_VERSION_RE = re.compile(r'(?m)^version = "([^"]+)"$')


def package_version() -> str:
    return str(json.loads(PACKAGE_JSON.read_text())["version"])


def set_json_version(path: Path, version: str) -> None:
    payload = json.loads(path.read_text())
    payload["version"] = version
    path.write_text(json.dumps(payload, indent=2) + "\n")


def set_pyproject_version(version: str) -> None:
    text = PYPROJECT.read_text()
    updated, count = PYPROJECT_VERSION_RE.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        raise SystemExit("Expected exactly one [project] version in pyproject.toml")
    PYPROJECT.write_text(updated)


def set_versions(*, npm_version: str, python_version: str) -> None:
    set_json_version(PACKAGE_JSON, npm_version)
    set_pyproject_version(python_version)
    print(f"npm_version={npm_version}")
    print(f"python_version={python_version}")


def bumped_version(base: str, part: str) -> str:
    match = CORE_VERSION_RE.match(base)
    if match is None:
        raise SystemExit(f"Version bumps require a plain major.minor.patch base, got: {base}")
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Set coordinated npm and Python package versions.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--release", help="Release version to write to both manifests, for example 1.2.3.")
    group.add_argument("--bump", choices=("patch", "minor", "major"), help="Bump the base release version.")
    parser.add_argument(
        "--base",
        default=None,
        help="Base SemVer version for --bump. Defaults to package.json.",
    )
    args = parser.parse_args()

    if args.release:
        if not RELEASE_VERSION_RE.match(args.release):
            raise SystemExit(f"Invalid release version: {args.release}")
        set_versions(npm_version=args.release, python_version=args.release)
        return

    base = args.base or package_version()
    if not RELEASE_VERSION_RE.match(base):
        raise SystemExit(f"Invalid base version: {base}")
    version = bumped_version(base, args.bump)
    set_versions(npm_version=version, python_version=version)


if __name__ == "__main__":
    main()
