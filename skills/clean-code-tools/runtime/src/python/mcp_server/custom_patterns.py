#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from mcp_server.models import CleanCodeChunk, JsonDict
from mcp_server.pattern_chunks import PatternChunkSpec, pattern_chunk
from mcp_server.pattern_models import CustomCleanCodePattern, clean_custom_patterns_path

RUNTIME_HOME = Path(__file__).resolve().parents[4]
CUSTOM_PATTERNS_ENV_VAR = "CLEAN_CODE_CUSTOM_PATTERNS_PATH"
DEFAULT_CUSTOM_PATTERN_RECORDS = RUNTIME_HOME / "data" / "custom-clean-code-patterns.jsonl"
CUSTOM_PATTERN_RECORDS = DEFAULT_CUSTOM_PATTERN_RECORDS


def custom_patterns_path(path: str | None = None) -> Path:
    raw_path = path or os.environ.get(CUSTOM_PATTERNS_ENV_VAR)
    if raw_path:
        clean_path = clean_custom_patterns_path(raw_path)
        if clean_path is None:
            return DEFAULT_CUSTOM_PATTERN_RECORDS
        return Path(clean_path)
    return DEFAULT_CUSTOM_PATTERN_RECORDS


def load_custom_patterns(path: str | None = None) -> list[CustomCleanCodePattern]:
    source = custom_patterns_path(path)
    if not source.exists():
        return []
    patterns: list[CustomCleanCodePattern] = []
    with source.open() as handle:
        patterns.extend(
            CustomCleanCodePattern.model_validate_json(line)
            for line in handle
            if line.strip()
        )
    return patterns


def list_custom_pattern_records(path: str | None = None) -> list[JsonDict]:
    return [pattern.model_dump(mode="json") for pattern in load_custom_patterns(path)]


def custom_pattern_chunks(path: str | None = None) -> list[CleanCodeChunk]:
    return [
        pattern_chunk(
            pattern,
            spec=PatternChunkSpec(
                chunk_index=index,
                source_file=custom_patterns_path(path).name,
                source_kind="custom_clean_code_pattern",
                chunk_kind="custom_pattern_record",
                chunk_id_prefix="custom-pattern",
            ),
        )
        for index, pattern in enumerate(load_custom_patterns(path))
    ]


def upsert_custom_pattern(
    pattern: CustomCleanCodePattern,
    *,
    path: str | None = None,
) -> tuple[bool, JsonDict]:
    patterns = load_custom_patterns(path)
    created = True
    next_patterns: list[CustomCleanCodePattern] = []
    for existing in patterns:
        if existing.id == pattern.id:
            created = False
            next_patterns.append(pattern)
        else:
            next_patterns.append(existing)
    if created:
        next_patterns.append(pattern)
    write_custom_patterns(next_patterns, path=path)
    return created, pattern.model_dump(mode="json")


def delete_custom_pattern(pattern_id: str, *, path: str | None = None) -> bool:
    patterns = load_custom_patterns(path)
    next_patterns = [pattern for pattern in patterns if pattern.id != pattern_id]
    if len(next_patterns) == len(patterns):
        return False
    write_custom_patterns(next_patterns, path=path)
    return True


def custom_pattern_by_id(
    pattern_id: str,
    *,
    path: str | None = None,
) -> CustomCleanCodePattern | None:
    for pattern in load_custom_patterns(path):
        if pattern.id == pattern_id:
            return pattern
    return None


def custom_pattern_chunk(
    pattern: CustomCleanCodePattern,
    *,
    path: str | None = None,
) -> CleanCodeChunk:
    return pattern_chunk(
        pattern,
        spec=PatternChunkSpec(
            chunk_index=0,
            source_file=custom_patterns_path(path).name,
            source_kind="custom_clean_code_pattern",
            chunk_kind="custom_pattern_record",
            chunk_id_prefix="custom-pattern",
        ),
    )


def write_custom_patterns(
    patterns: list[CustomCleanCodePattern],
    *,
    path: str | None = None,
) -> None:
    source = custom_patterns_path(path)
    source.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(
        json.dumps(pattern.model_dump(mode="json"), sort_keys=True)
        for pattern in sorted(patterns, key=lambda item: item.id)
    )
    write_text_atomic(source, f"{payload}\n" if payload else "")


def write_text_atomic(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
    ) as handle:
        handle.write(content)
        tmp_path = Path(handle.name)
    tmp_path.replace(path)
