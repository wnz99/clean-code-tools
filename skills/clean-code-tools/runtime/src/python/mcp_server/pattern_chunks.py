#!/usr/bin/env python3
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from mcp_server.models import CleanCodeChunk
from mcp_server.pattern_models import BaseCleanCodePattern
from mcp_server.text import clean_alias, clean_topic, clean_topic_text
from mcp_server.utils.sha256_text import sha256_text

CHUNK_ID_NAMESPACE = uuid.UUID("fd1b279f-073e-5aa4-bf70-9f70446a3d8f")
GENERIC_ALIASES = {
    "clean code",
    "code smell",
    "planning guidance",
    "refactoring rule",
}
PATTERN_EXAMPLE_LIMIT = 2
ExampleGroup = Literal["good_examples", "bad_examples"]
ExampleLanguage = Literal["typescript", "python"]


@dataclass(frozen=True)
class PatternChunkSpec:
    chunk_index: int
    source_file: str
    source_kind: str
    chunk_kind: str
    chunk_id_prefix: str


def pattern_chunk(
    record: BaseCleanCodePattern,
    *,
    spec: PatternChunkSpec,
) -> CleanCodeChunk:
    chunk_id = f"{spec.chunk_id_prefix}:{record.id}"
    topic = clean_topic(record.topic)
    embedding_text = pattern_embedding_text(record)
    display_text = pattern_display_text(record)
    return CleanCodeChunk(
        chunk_id=chunk_id,
        object_id=object_id_for(chunk_id),
        source_file=spec.source_file,
        source_kind=spec.source_kind,
        record_id=record.id,
        title=record.title,
        topic=topic,
        section_path=(topic, record.title),
        chunk_kind=spec.chunk_kind,
        chunk_index=spec.chunk_index,
        rule_family=record.rule_family,
        lintability=record.lintability,
        aliases=record_aliases(record),
        languages=record_languages(record),
        lint_candidates=tuple(record.lint_candidates),
        content_text=display_text,
        embedding_text=embedding_text,
        display_text=display_text,
        text_hash=sha256_text(embedding_text),
    )


def object_id_for(chunk_id: str) -> str:
    return str(uuid.uuid5(CHUNK_ID_NAMESPACE, chunk_id))


def record_aliases(record: BaseCleanCodePattern) -> tuple[str, ...]:
    return tuple(
        alias
        for alias in (clean_alias(item) for item in record.aliases)
        if alias
    )


def specific_record_aliases(record: BaseCleanCodePattern) -> tuple[str, ...]:
    return tuple(
        alias
        for alias in record_aliases(record)
        if alias.lower() not in GENERIC_ALIASES
    )


def record_languages(record: BaseCleanCodePattern) -> tuple[str, ...]:
    return tuple(
        language
        for language in ("typescript", "python")
        if record_examples(record, "good_examples", language)
        or record_examples(record, "bad_examples", language)
    )


def record_examples(
    record: BaseCleanCodePattern,
    group: ExampleGroup,
    language: ExampleLanguage,
) -> tuple[str, ...]:
    raw_examples = record.good_examples if group == "good_examples" else record.bad_examples
    value = raw_examples.get(language)
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def pattern_embedding_text(record: BaseCleanCodePattern) -> str:
    aliases = specific_record_aliases(record)
    lines = [
        f"Pattern {record.id}: {record.title}",
        (
            f"Topic: {record.topic}. "
            f"Rule family: {record.rule_family}. "
            f"Lintability: {record.lintability}."
        ),
    ]
    if aliases:
        lines.append(f"Aliases: {', '.join(aliases[:10])}.")
    lines.extend(
        [
            f"Problem: {record.problem}",
            f"Use when: {record.use_when}",
            f"Avoid when: {record.avoid_when}",
            f"Static signals: {'; '.join(record.lint_candidates)}",
        ]
    )
    lines.extend(pattern_example_lines(record, limit=PATTERN_EXAMPLE_LIMIT))
    return clean_topic_text("\n".join(lines))


def pattern_display_text(record: BaseCleanCodePattern) -> str:
    aliases = specific_record_aliases(record)
    lines = [
        f"{record.id} {record.title}",
        f"Topic: {record.topic}",
        f"Rule family: {record.rule_family}",
        f"Lintability: {record.lintability}",
    ]
    if aliases:
        lines.append(f"Aliases: {', '.join(aliases)}")
    lines.extend(
        [
            f"Problem: {record.problem}",
            f"Use when: {record.use_when}",
            f"Avoid when: {record.avoid_when}",
            f"Lint candidates: {'; '.join(record.lint_candidates)}",
        ]
    )
    lines.extend(pattern_example_lines(record, limit=None))
    return clean_topic_text("\n".join(lines))


def pattern_example_lines(record: BaseCleanCodePattern, *, limit: int | None) -> list[str]:
    lines: list[str] = []
    labels = (("typescript", "TypeScript"), ("python", "Python"))
    for group, adjective in (("good_examples", "Good"), ("bad_examples", "Bad")):
        for language, label in labels:
            examples = record_examples(record, group, language)
            selected = examples if limit is None else examples[:limit]
            for index, example in enumerate(selected, start=1):
                suffix = f" {index}" if len(examples) > 1 else ""
                lines.append(f"{adjective} {label} example{suffix}:\n{example}")
    return lines
