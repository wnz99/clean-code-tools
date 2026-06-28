#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

CHUNKER_VERSION = "clean-code-semantic-v1"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_PROVIDER = "fastembed/cpu"

JsonDict = dict[str, Any]
Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True, slots=True)
class CleanCodeChunk:  # pylint: disable=too-many-instance-attributes
    chunk_id: str
    object_id: str
    source_file: str
    source_kind: str
    record_id: str
    title: str
    topic: str
    section_path: tuple[str, ...]
    chunk_kind: str
    chunk_index: int
    rule_family: str
    lintability: str
    aliases: tuple[str, ...]
    languages: tuple[str, ...]
    lint_candidates: tuple[str, ...]
    content_text: str
    embedding_text: str
    display_text: str
    text_hash: str

    @property
    def properties(self) -> JsonDict:
        return {
            "chunkId": self.chunk_id,
            "sourceFile": self.source_file,
            "sourceKind": self.source_kind,
            "recordId": self.record_id,
            "title": self.title,
            "topic": self.topic,
            "sectionPath": list(self.section_path),
            "chunkKind": self.chunk_kind,
            "chunkIndex": self.chunk_index,
            "ruleFamily": self.rule_family,
            "lintability": self.lintability,
            "aliases": list(self.aliases),
            "languages": list(self.languages),
            "lintCandidates": list(self.lint_candidates),
            "contentText": self.content_text,
            "embeddingText": self.embedding_text,
            "displayText": self.display_text,
            "textHash": self.text_hash,
            "chunkerVersion": CHUNKER_VERSION,
            "embeddingModel": DEFAULT_EMBEDDING_MODEL,
            "embeddingProvider": DEFAULT_EMBEDDING_PROVIDER,
            "createdAt": datetime.now(UTC).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class MarkdownSection:
    source_file: str
    section_path: tuple[str, ...]
    heading: str
    body: str
    start_line: int
    end_line: int
