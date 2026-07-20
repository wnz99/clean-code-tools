#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from mcp_server import semantic

PATTERN_NOT_FOUND_ERROR = "pattern not found"
CUSTOM_PATTERN_NOT_FOUND_ERROR = "custom pattern not found"


def pattern_by_id(
    pattern_id: str,
    *,
    custom_patterns_path: str | None = None,
) -> dict[str, Any]:
    normalized = pattern_id.strip().upper()
    if semantic.CC_ID_RE.fullmatch(normalized):
        record = semantic.get_pattern_record(normalized)
        if record is None:
            raise ValueError(f"{PATTERN_NOT_FOUND_ERROR}: {normalized}")  # noqa: TRY003
        return record
    request = semantic.GetCustomPatternRequest.model_validate(
        {
            "pattern_id": normalized,
            "custom_patterns_path": custom_patterns_path,
        }
    )
    custom_pattern = semantic.custom_pattern_by_id(
        request.pattern_id,
        path=request.custom_patterns_path,
    )
    if custom_pattern is None:
        raise ValueError(f"{CUSTOM_PATTERN_NOT_FOUND_ERROR}: {request.pattern_id}")  # noqa: TRY003
    return custom_pattern.model_dump(mode="json")
