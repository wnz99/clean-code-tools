#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ExampleSet = str | list[str]
Lintability = Literal["high", "medium", "low", "review_only"]
CUSTOM_PATTERN_ID_RE = r"^(?:CUSTOM|[A-Z][A-Z0-9-]{1,31})-\d{3}$"
EMPTY_ITEM_ERROR = "items must be non-empty strings"
DUPLICATE_ITEM_ERROR = "items must be unique"
LANGUAGE_EXAMPLES_ERROR = "examples must include exactly typescript and python"
EMPTY_EXAMPLE_ERROR = "example must be non-empty"
EMPTY_EXAMPLE_LIST_ERROR = "example list must not be empty"
DUPLICATE_EXAMPLE_ERROR = "examples must be unique"
CUSTOM_NAMESPACE_ERROR = "custom pattern IDs must not use the built-in CC namespace"
BUILTIN_READONLY_ERROR = "built-in CC patterns are read-only"
CUSTOM_PATTERN_PATH_EMPTY_ERROR = "custom_patterns_path must not be empty"
CUSTOM_PATTERN_PATH_SUFFIX_ERROR = "custom_patterns_path must point to a .jsonl file"
CUSTOM_PATTERN_PATH_BUILTIN_ERROR = "custom_patterns_path must not target built-in corpus files"
CUSTOM_PATTERN_PATH_SCOPE_ERROR = (
    "custom_patterns_path must be inside the current working directory "
    "or CLEAN_CODE_CUSTOM_PATTERNS_BASE"
)
CUSTOM_PATTERN_PATH_BASE_ENV = "CLEAN_CODE_CUSTOM_PATTERNS_BASE"
INDEX_PATH_BASE_ENV = "CLEAN_CODE_INDEX_BASE"
INDEX_PATH_SUFFIXES = frozenset({".sqlite", ".db"})
INDEX_PATH_EMPTY_ERROR = "index_path must not be empty"
INDEX_PATH_SUFFIX_ERROR = "index_path must point to a .sqlite or .db file"
INDEX_PATH_SCOPE_ERROR = (
    "index_path must be inside the current working directory or CLEAN_CODE_INDEX_BASE"
)
QUERY_EMPTY_ERROR = "query must not be empty"
BUILTIN_PATTERN_FILENAMES = frozenset(
    {
        "clean-code-patterns.jsonl",
        "vector-record.schema.json",
    }
)


class PatternSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1)
    version: int = Field(ge=1)


class BaseCleanCodePattern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(min_length=3)
    topic: str = Field(min_length=3)
    rule_family: str = Field(min_length=3)
    aliases: list[str] = Field(min_length=3)
    problem: str = Field(min_length=4)
    use_when: str = Field(min_length=10)
    avoid_when: str = Field(min_length=10)
    good_examples: dict[Literal["typescript", "python"], ExampleSet]
    bad_examples: dict[Literal["typescript", "python"], ExampleSet]
    lint_candidates: list[str] = Field(min_length=1)
    lintability: Lintability
    source: PatternSource

    @field_validator("aliases", "lint_candidates")
    @classmethod
    def require_non_empty_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(value):
            raise ValueError(EMPTY_ITEM_ERROR)
        if len(set(cleaned)) != len(cleaned):
            raise ValueError(DUPLICATE_ITEM_ERROR)
        return cleaned

    @field_validator("good_examples", "bad_examples")
    @classmethod
    def require_language_examples(
        cls,
        value: dict[Literal["typescript", "python"], ExampleSet],
    ) -> dict[Literal["typescript", "python"], ExampleSet]:
        if set(value) != {"typescript", "python"}:
            raise ValueError(LANGUAGE_EXAMPLES_ERROR)
        return {language: clean_examples(examples) for language, examples in value.items()}


def clean_examples(value: ExampleSet) -> ExampleSet:
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(EMPTY_EXAMPLE_ERROR)
        return cleaned
    cleaned_items = [item.strip() for item in value if item.strip()]
    if not cleaned_items:
        raise ValueError(EMPTY_EXAMPLE_LIST_ERROR)
    if len(set(cleaned_items)) != len(cleaned_items):
        raise ValueError(DUPLICATE_EXAMPLE_ERROR)
    return cleaned_items


class CleanCodePattern(BaseCleanCodePattern):
    id: str = Field(pattern=r"^CC-\d{3}$")


class CustomCleanCodePattern(BaseCleanCodePattern):
    id: str = Field(pattern=CUSTOM_PATTERN_ID_RE)

    @field_validator("id")
    @classmethod
    def reject_builtin_namespace(cls, value: str) -> str:
        if value.startswith("CC-"):
            raise ValueError(CUSTOM_NAMESPACE_ERROR)
        return value


class ValidateCustomPatternRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: CustomCleanCodePattern


class GetCustomPatternRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern_id: str = Field(pattern=CUSTOM_PATTERN_ID_RE)
    custom_patterns_path: str | None = None

    @field_validator("pattern_id")
    @classmethod
    def reject_builtin_namespace(cls, value: str) -> str:
        if value.startswith("CC-"):
            raise ValueError(BUILTIN_READONLY_ERROR)
        return value

    @field_validator("custom_patterns_path")
    @classmethod
    def validate_custom_patterns_path(cls, value: str | None) -> str | None:
        return clean_custom_patterns_path(value)


class UpsertCustomPatternRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: CustomCleanCodePattern
    custom_patterns_path: str | None = None
    sync_index: bool = True
    index_path: str | None = None
    model: str = Field(default="BAAI/bge-small-en-v1.5", min_length=1)

    @field_validator("custom_patterns_path")
    @classmethod
    def validate_custom_patterns_path(cls, value: str | None) -> str | None:
        return clean_custom_patterns_path(value)

    @field_validator("index_path")
    @classmethod
    def validate_index_path(cls, value: str | None) -> str | None:
        return clean_index_path(value)


class DeleteCustomPatternRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern_id: str = Field(pattern=CUSTOM_PATTERN_ID_RE)
    custom_patterns_path: str | None = None
    sync_index: bool = True
    index_path: str | None = None

    @field_validator("custom_patterns_path")
    @classmethod
    def validate_custom_patterns_path(cls, value: str | None) -> str | None:
        return clean_custom_patterns_path(value)

    @field_validator("index_path")
    @classmethod
    def validate_index_path(cls, value: str | None) -> str | None:
        return clean_index_path(value)

    @field_validator("pattern_id")
    @classmethod
    def reject_builtin_namespace(cls, value: str) -> str:
        if value.startswith("CC-"):
            raise ValueError(BUILTIN_READONLY_ERROR)
        return value


class ListCustomPatternsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    custom_patterns_path: str | None = None

    @field_validator("custom_patterns_path")
    @classmethod
    def validate_custom_patterns_path(cls, value: str | None) -> str | None:
        return clean_custom_patterns_path(value)


class SearchCleanCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=25)
    index_path: str | None = None
    model: str = Field(default="BAAI/bge-small-en-v1.5", min_length=1)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(QUERY_EMPTY_ERROR)
        return stripped

    @field_validator("index_path")
    @classmethod
    def validate_index_path(cls, value: str | None) -> str | None:
        return clean_index_path(value)


class SearchCleanCodePatternsRequest(SearchCleanCodeRequest):
    language: str = "any"
    rule_families: list[str] | None = None
    topics: list[str] | None = None
    lintability: list[str] | None = None
    source_kinds: list[str] | None = None


class RecommendCleanCodeLintRulesRequest(SearchCleanCodeRequest):
    language: str = "any"
    targets: list[str] | None = None


def clean_custom_patterns_path(value: str | None) -> str | None:
    if value is None:
        return None
    raw_value = value.strip()
    if not raw_value:
        raise ValueError(CUSTOM_PATTERN_PATH_EMPTY_ERROR)
    path = Path(raw_value).expanduser()
    if path.suffix != ".jsonl":
        raise ValueError(CUSTOM_PATTERN_PATH_SUFFIX_ERROR)
    if path.name in BUILTIN_PATTERN_FILENAMES:
        raise ValueError(CUSTOM_PATTERN_PATH_BUILTIN_ERROR)
    resolved_path = path.resolve(strict=False)
    if not is_allowed_custom_patterns_path(resolved_path):
        raise ValueError(CUSTOM_PATTERN_PATH_SCOPE_ERROR)
    return str(resolved_path)


def is_allowed_custom_patterns_path(path: Path) -> bool:
    allowed_roots = [Path.cwd().resolve()]
    configured_base = os.environ.get(CUSTOM_PATTERN_PATH_BASE_ENV)
    if configured_base:
        allowed_roots.append(Path(configured_base).expanduser().resolve(strict=False))
    return any(path == root or root in path.parents for root in allowed_roots)


def clean_index_path(value: str | None) -> str | None:
    if value is None:
        return None
    raw_value = value.strip()
    if not raw_value:
        raise ValueError(INDEX_PATH_EMPTY_ERROR)
    path = Path(raw_value).expanduser()
    if path.suffix not in INDEX_PATH_SUFFIXES:
        raise ValueError(INDEX_PATH_SUFFIX_ERROR)
    resolved_path = path.resolve(strict=False)
    if not is_allowed_index_path(resolved_path):
        raise ValueError(INDEX_PATH_SCOPE_ERROR)
    return str(resolved_path)


def is_allowed_index_path(path: Path) -> bool:
    allowed_roots = [Path.cwd().resolve()]
    configured_base = os.environ.get(INDEX_PATH_BASE_ENV)
    if configured_base:
        allowed_roots.append(Path(configured_base).expanduser().resolve(strict=False))
    return any(path == root or root in path.parents for root in allowed_roots)
