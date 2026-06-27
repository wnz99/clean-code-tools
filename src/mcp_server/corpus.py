#!/usr/bin/env python3
from __future__ import annotations

import json
import uuid
from pathlib import Path

from src.mcp_server.markdown import (
    infer_markdown_rule_family,
    markdown_aliases,
    markdown_sections,
    split_section_body,
)
from src.mcp_server.models import CleanCodeChunk, JsonDict
from src.mcp_server.text import (
    clean_alias,
    clean_topic,
    clean_topic_text,
    detected_record_id,
    languages_in_text,
    lint_candidates_in_text,
    slug,
)
from src.mcp_server.utils.sha256_text import sha256_text

ROOT = Path(__file__).resolve().parents[2]
PATTERN_RECORDS = ROOT / "clean-code-patterns.jsonl"
MARKDOWN_SOURCES = (
    ROOT / "clean-code-examples.md",
    ROOT / "README.md",
    ROOT / "rag-mcp-design.md",
    ROOT / "docs" / "eslint-custom-rules.md",
    ROOT / "docs" / "eslint-recommended-config.md",
    ROOT / "docs" / "python-lint-recommended-config.md",
    ROOT / "docs" / "python-ruff-custom-rules-research.md",
)
CHUNK_ID_NAMESPACE = uuid.UUID("fd1b279f-073e-5aa4-bf70-9f70446a3d8f")


def build_chunks(root: Path = ROOT) -> list[CleanCodeChunk]:
    chunks = [*pattern_record_chunks(root / PATTERN_RECORDS.name)]
    for source in MARKDOWN_SOURCES:
        path = root / source.relative_to(ROOT)
        if path.exists():
            chunks.extend(markdown_chunks(path, root=root))
    return chunks


def pattern_record_chunks(path: Path) -> list[CleanCodeChunk]:
    chunks: list[CleanCodeChunk] = []
    with path.open() as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            record = json.loads(line)
            chunk_id = f"pattern:{record['id']}"
            topic = clean_topic(str(record["topic"]))
            aliases = tuple(
                alias
                for alias in (clean_alias(str(item)) for item in record["aliases"])
                if alias
            )
            embedding_text = clean_topic_text(str(record["embedding_text"]).strip())
            display_text = clean_topic_text(str(record["display_text"]).strip())
            languages = tuple(
                language
                for language in ("typescript", "python")
                if record.get("good_examples", {}).get(language)
                or record.get("bad_examples", {}).get(language)
            )
            chunks.append(
                CleanCodeChunk(
                    chunk_id=chunk_id,
                    object_id=object_id_for(chunk_id),
                    source_file=path.name,
                    source_kind="clean_code_pattern",
                    record_id=str(record["id"]),
                    title=str(record["title"]),
                    topic=topic,
                    section_path=(topic, str(record["title"])),
                    chunk_kind="pattern_record",
                    chunk_index=index,
                    rule_family=str(record["rule_family"]),
                    lintability=str(record["lintability"]),
                    aliases=aliases,
                    languages=languages,
                    lint_candidates=tuple(str(item) for item in record["lint_candidates"]),
                    content_text=display_text,
                    embedding_text=embedding_text,
                    display_text=display_text,
                    text_hash=sha256_text(embedding_text),
                )
            )
    return chunks


def load_pattern_records(path: Path = PATTERN_RECORDS) -> list[JsonDict]:
    records: list[JsonDict] = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                if isinstance(record, dict):
                    records.append(record)
    return records


def get_pattern_record(pattern_id: str, *, root: Path = ROOT) -> JsonDict | None:
    normalized_id = pattern_id.strip().upper()
    for record in load_pattern_records(root / PATTERN_RECORDS.name):
        if str(record.get("id", "")).upper() == normalized_id:
            return record
    return None


def markdown_chunks(path: Path, *, root: Path = ROOT) -> list[CleanCodeChunk]:
    chunks: list[CleanCodeChunk] = []
    relative_path = path.relative_to(root).as_posix()
    for section_index, section in enumerate(markdown_sections(path, root=root)):
        for split_index, body in enumerate(split_section_body(section.body)):
            heading_text = " > ".join(section.section_path)
            record_id = detected_record_id(section.heading)
            chunk_id = (
                f"md:{relative_path}:{slug(heading_text)}"
                if split_index == 0
                else f"md:{relative_path}:{slug(heading_text)}:{split_index + 1}"
            )
            content_text = clean_topic_text(body.strip())
            embedding_text = (
                f"Markdown section: {heading_text}\n"
                f"Source: {relative_path}:{section.start_line}-{section.end_line}\n\n"
                f"{content_text}"
            )
            chunks.append(
                CleanCodeChunk(
                    chunk_id=chunk_id,
                    object_id=object_id_for(chunk_id),
                    source_file=relative_path,
                    source_kind="markdown_doc",
                    record_id=record_id,
                    title=section.heading,
                    topic=clean_topic(section.section_path[0]) if section.section_path else clean_topic(section.heading),
                    section_path=tuple(clean_topic(item) for item in section.section_path),
                    chunk_kind="markdown_section" if split_index == 0 else "markdown_section_part",
                    chunk_index=section_index * 100 + split_index,
                    rule_family=infer_markdown_rule_family(section),
                    lintability="",
                    aliases=tuple(clean_alias(alias) for alias in markdown_aliases(section) if clean_alias(alias)),
                    languages=languages_in_text(content_text),
                    lint_candidates=lint_candidates_in_text(content_text),
                    content_text=content_text,
                    embedding_text=embedding_text,
                    display_text=embedding_text,
                    text_hash=sha256_text(embedding_text),
                )
            )
    return chunks


def object_id_for(chunk_id: str) -> str:
    return str(uuid.uuid5(CHUNK_ID_NAMESPACE, chunk_id))
