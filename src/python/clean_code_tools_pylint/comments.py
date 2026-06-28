from __future__ import annotations

import tokenize
from io import BytesIO
from typing import ClassVar

from astroid import nodes
from pylint.checkers import BaseRawFileChecker

from .helpers import (
    MIN_SHARED_COMMENT_WORDS,
    REDUNDANT_COMMENT_OVERLAP_RATIO,
    TODO_PATTERN,
    TODO_SEGMENT,
    clean_comment,
    is_byline_or_date,
    is_likely_code_comment,
    is_separator_comment,
    normalized_words,
)


class CleanCodeCommentChecker(BaseRawFileChecker):
    name = "clean-code-comments"
    msgs: ClassVar = {
        "C9001": (
            "TODO/FIXME comments should include an owner or issue ID, for example TODO(PROJ-123): remove fallback.",
            "clean-code-todo-format",
            "Require TODO, FIXME, and XXX comments to include an owner or issue identifier.",
        ),
        "C9002": (
            "Remove commented-out code; version history should preserve old implementations.",
            "clean-code-commented-out-code",
            "Flag comments that look like disabled Python code.",
        ),
        "C9005": (
            "Comment mostly repeats the next line; prefer making the code name carry the intent.",
            "clean-code-redundant-comment",
            "Flag comments that mostly repeat the following line of code.",
        ),
        "C9006": (
            "Avoid noisy separator, byline, or date comments; use structure and version control instead.",
            "clean-code-noisy-comment",
            "Flag separator, byline, and date comments.",
        ),
    }

    def process_module(self, node: nodes.Module) -> None:
        raw_bytes = node.stream().read()
        lines = raw_bytes.decode("utf-8", errors="replace").splitlines()
        for token in tokenize.tokenize(BytesIO(raw_bytes).readline):
            if token.type != tokenize.COMMENT:
                continue
            text = clean_comment(token.string)
            line_number = token.start[0]
            self.check_todo(text, line_number)
            self.check_comment_shape(text, line_number)
            self.check_redundant_comment(text, line_number, lines)

    def check_todo(self, text: str, line_number: int) -> None:
        todo_segments = TODO_SEGMENT.findall(text)
        if any(not TODO_PATTERN.match(segment.strip()) for segment in todo_segments):
            self.add_message("clean-code-todo-format", line=line_number)

    def check_comment_shape(self, text: str, line_number: int) -> None:
        if TODO_SEGMENT.search(text):
            return
        if is_likely_code_comment(text):
            self.add_message("clean-code-commented-out-code", line=line_number)
        if is_separator_comment(text) or is_byline_or_date(text):
            self.add_message("clean-code-noisy-comment", line=line_number)

    def check_redundant_comment(self, text: str, line_number: int, lines: list[str]) -> None:
        comment_words = normalized_words(text)
        if len(comment_words) < MIN_SHARED_COMMENT_WORDS or line_number >= len(lines):
            return
        next_line_words = set(normalized_words(lines[line_number]))
        shared_words = [word for word in comment_words if word in next_line_words]
        if (
            len(shared_words) >= MIN_SHARED_COMMENT_WORDS
            and len(shared_words) / len(comment_words) >= REDUNDANT_COMMENT_OVERLAP_RATIO
        ):
            self.add_message("clean-code-redundant-comment", line=line_number)
