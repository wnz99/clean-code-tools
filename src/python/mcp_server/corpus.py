#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from mcp_server.markdown import (
    infer_markdown_rule_family,
    markdown_aliases,
    markdown_sections,
    split_section_body,
)
from mcp_server.models import CleanCodeChunk, JsonDict, MarkdownSection
from mcp_server.pattern_chunks import PatternChunkSpec, object_id_for, pattern_chunk
from mcp_server.pattern_models import CleanCodePattern
from mcp_server.text import (
    clean_alias,
    clean_topic,
    clean_topic_text,
    detected_record_id,
    languages_in_text,
    lint_candidates_in_text,
    slug,
)
from mcp_server.utils.sha256_text import sha256_text

ROOT = Path(__file__).resolve().parents[3]
PATTERN_RECORDS = ROOT / "data" / "clean-code-patterns.jsonl"
MARKDOWN_SOURCES = (
    ROOT / "README.md",
    ROOT / "docs" / "eslint-custom-rules.md",
    ROOT / "docs" / "eslint-recommended-config.md",
    ROOT / "docs" / "python-lint-recommended-config.md",
    ROOT / "docs" / "python-pylint-custom-rules.md",
    ROOT / "docs" / "static-trigger-semantic-review.md",
)
def build_chunks(root: Path = ROOT) -> list[CleanCodeChunk]:
    chunks = [*pattern_record_chunks(root / PATTERN_RECORDS.relative_to(ROOT))]
    for source in MARKDOWN_SOURCES:
        path = root / source.relative_to(ROOT)
        if path.exists():
            chunks.extend(markdown_chunks(path, root=root))
    try:
        from mcp_server.custom_patterns import custom_pattern_chunks  # noqa: PLC0415
    except ImportError:
        return chunks
    custom_path = None
    if root != ROOT:
        custom_path = str(root / "data" / "custom-clean-code-patterns.jsonl")
    chunks.extend(custom_pattern_chunks(custom_path))
    return chunks


def pattern_record_chunks(path: Path) -> list[CleanCodeChunk]:
    chunks: list[CleanCodeChunk] = []
    with path.open() as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            record = CleanCodePattern.model_validate_json(line)
            chunks.append(
                pattern_chunk(
                    record,
                    spec=PatternChunkSpec(
                        chunk_index=index,
                        source_file=path.name,
                        source_kind="clean_code_pattern",
                        chunk_kind="pattern_record",
                        chunk_id_prefix="pattern",
                    ),
                )
            )
    return chunks


def load_pattern_records(path: Path = PATTERN_RECORDS) -> list[JsonDict]:
    records: list[JsonDict] = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                record = CleanCodePattern.model_validate_json(line)
                records.append(record.model_dump(mode="json"))
    return records


def get_pattern_record(pattern_id: str, *, root: Path = ROOT) -> JsonDict | None:
    normalized_id = pattern_id.strip().upper()
    for record in load_pattern_records(root / PATTERN_RECORDS.relative_to(ROOT)):
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
                    topic=markdown_topic(section),
                    section_path=tuple(clean_topic(item) for item in section.section_path),
                    chunk_kind="markdown_section" if split_index == 0 else "markdown_section_part",
                    chunk_index=section_index * 100 + split_index,
                    rule_family=infer_markdown_rule_family(section),
                    lintability="",
                    aliases=clean_markdown_aliases(section),
                    languages=languages_in_text(content_text),
                    lint_candidates=lint_candidates_in_text(content_text),
                    content_text=content_text,
                    embedding_text=embedding_text,
                    display_text=embedding_text,
                    text_hash=sha256_text(embedding_text),
                )
            )
    return chunks


def markdown_topic(section: MarkdownSection) -> str:
    if section.section_path:
        return clean_topic(section.section_path[0])
    return clean_topic(section.heading)


def clean_markdown_aliases(section: MarkdownSection) -> tuple[str, ...]:
    return tuple(
        alias
        for alias in (clean_alias(value) for value in markdown_aliases(section))
        if alias
    )
