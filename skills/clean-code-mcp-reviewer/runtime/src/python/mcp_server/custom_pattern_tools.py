#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from mcp_server import semantic


def validate_clean_code_pattern_payload(pattern: dict[str, Any]) -> dict[str, Any]:
    request = semantic.ValidateCustomPatternRequest.model_validate({"pattern": pattern})
    return {
        "valid": True,
        "pattern": request.pattern.model_dump(mode="json"),
        "custom_id_contract": "Use CUSTOM-001 or REPO-SLUG-001. Built-in CC-### records are read-only.",
    }


def list_custom_clean_code_pattern_payload(
    custom_patterns_path: str | None = None,
) -> dict[str, Any]:
    request = semantic.ListCustomPatternsRequest.model_validate(
        {"custom_patterns_path": custom_patterns_path}
    )
    patterns = semantic.list_custom_pattern_records(request.custom_patterns_path)
    return {
        "custom_patterns_path": str(semantic.custom_patterns_path(request.custom_patterns_path)),
        "count": len(patterns),
        "patterns": patterns,
    }


def upsert_clean_code_pattern_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    request = semantic.UpsertCustomPatternRequest.model_validate(payload)
    source = semantic.custom_patterns_path(request.custom_patterns_path)
    source_existed = source.exists()
    previous_patterns = semantic.load_custom_patterns(request.custom_patterns_path)
    created, stored = semantic.upsert_custom_pattern(
        request.pattern,
        path=request.custom_patterns_path,
    )
    if request.sync_weaviate:
        try:
            semantic.upsert_chunk(
                chunk=semantic.custom_pattern_chunk(
                    request.pattern,
                    path=request.custom_patterns_path,
                ),
                url=request.weaviate_url,
                collection_name=request.collection,
                model_name=request.model,
            )
        except Exception:
            restore_custom_patterns(
                previous_patterns,
                path=request.custom_patterns_path,
                source_existed=source_existed,
            )
            raise
    return {
        "pattern_id": request.pattern.id,
        "created": created,
        "updated": not created,
        "synced_weaviate": request.sync_weaviate,
        "custom_patterns_path": str(semantic.custom_patterns_path(request.custom_patterns_path)),
        "pattern": stored,
    }


def delete_custom_clean_code_pattern_payload(
    pattern_id: str,
    custom_patterns_path: str | None = None,
    *,
    sync_weaviate: bool = True,
    weaviate_url: str,
    collection: str,
) -> dict[str, Any]:
    request = semantic.DeleteCustomPatternRequest.model_validate(
        {
            "pattern_id": pattern_id,
            "custom_patterns_path": custom_patterns_path,
            "sync_weaviate": sync_weaviate,
            "weaviate_url": weaviate_url,
            "collection": collection,
        }
    )
    pattern = semantic.custom_pattern_by_id(
        request.pattern_id,
        path=request.custom_patterns_path,
    )
    source = semantic.custom_patterns_path(request.custom_patterns_path)
    source_existed = source.exists()
    previous_patterns = semantic.load_custom_patterns(request.custom_patterns_path)
    deleted = semantic.delete_custom_pattern(
        request.pattern_id,
        path=request.custom_patterns_path,
    )
    deleted_weaviate = False
    if request.sync_weaviate and pattern is not None:
        try:
            deleted_weaviate = semantic.delete_chunk(
                chunk=semantic.custom_pattern_chunk(
                    pattern,
                    path=request.custom_patterns_path,
                ),
                url=request.weaviate_url,
                collection_name=request.collection,
            )
        except Exception:
            restore_custom_patterns(
                previous_patterns,
                path=request.custom_patterns_path,
                source_existed=source_existed,
            )
            raise
    return {
        "pattern_id": request.pattern_id,
        "deleted": deleted,
        "deleted_weaviate": deleted_weaviate,
        "custom_patterns_path": str(semantic.custom_patterns_path(request.custom_patterns_path)),
    }


def restore_custom_patterns(
    patterns: list[semantic.CustomCleanCodePattern],
    *,
    path: str | None,
    source_existed: bool,
) -> None:
    source = semantic.custom_patterns_path(path)
    if source_existed:
        semantic.write_custom_patterns(patterns, path=path)
        return
    source.unlink(missing_ok=True)
