#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from src.mcp_server.models import MarkdownSection
from src.mcp_server.text import approximate_tokens, detected_record_id, slugless
from src.mcp_server.utils.unique_strings import unique_strings

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CODE_FENCE_RE = re.compile(r"^\s*```")
MAX_SECTION_TOKENS = 1_200
TARGET_SECTION_TOKENS = 850


def markdown_sections(path: Path, *, root: Path) -> list[MarkdownSection]:
    # pylint: disable=too-many-locals
    relative_path = path.relative_to(root).as_posix()
    lines = path.read_text().splitlines()
    sections: list[MarkdownSection] = []
    stack: list[str] = []
    current_heading = path.stem
    current_path = (path.stem,)
    current_start = 1
    current_body: list[str] = []
    in_code = False

    def flush(end_line: int) -> None:
        body = "\n".join(current_body).strip()
        if body:
            sections.append(
                MarkdownSection(
                    source_file=relative_path,
                    section_path=tuple(current_path),
                    heading=current_heading,
                    body=body,
                    start_line=current_start,
                    end_line=end_line,
                )
            )

    for line_number, line in enumerate(lines, start=1):
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            current_body.append(line)
            continue
        heading = HEADING_RE.match(line) if not in_code else None
        if heading:
            flush(line_number - 1)
            level = len(heading.group(1))
            text = heading.group(2).strip()
            stack = stack[: level - 1]
            stack.append(text)
            current_heading = text
            current_path = tuple(stack)
            current_start = line_number
            current_body = [line]
            continue
        current_body.append(line)

    flush(len(lines))
    return sections


def split_section_body(body: str) -> list[str]:
    if approximate_tokens(body) <= MAX_SECTION_TOKENS:
        return [body]
    blocks = semantic_blocks(body)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for block in blocks:
        block_tokens = approximate_tokens(block)
        if current and current_tokens + block_tokens > TARGET_SECTION_TOKENS:
            chunks.append("\n\n".join(current).strip())
            current = []
            current_tokens = 0
        current.append(block)
        current_tokens += block_tokens
    if current:
        chunks.append("\n\n".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def semantic_blocks(body: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    in_code = False
    for line in body.splitlines():
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            current.append(line)
            continue
        if not in_code and not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def infer_markdown_rule_family(section: MarkdownSection) -> str:
    text = " ".join(section.section_path).lower()
    if "eslint" in text or "ruff" in text or "lint" in text:
        return "linting"
    if "comment" in text:
        return "comments"
    if "test" in text:
        return "tests"
    if "function" in text or "argument" in text:
        return "functions"
    if "name" in text:
        return "naming"
    return "documentation"


def markdown_aliases(section: MarkdownSection) -> tuple[str, ...]:
    aliases = [section.heading, *section.section_path]
    record_id = detected_record_id(section.heading)
    if record_id:
        aliases.append(record_id)
    return tuple(unique_strings([slugless(alias) for alias in aliases if alias.strip()]))
