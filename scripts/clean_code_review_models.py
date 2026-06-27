from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerRule:
    questions: tuple[str, ...]
    mcp_query: str


@dataclass(frozen=True)
class LintTrigger:
    tool: str
    rule: str
    message: str
    line: int | None
    column: int | None


@dataclass(frozen=True)
class TriggerInput:
    language: str
    file: str
    symbol: str | None
    anchor: str | None
    tool: str
    rule: str
    message: str
    line: int | None
    column: int | None


@dataclass(frozen=True)
class ReviewCandidate:
    language: str
    file: str
    symbol: str | None
    anchor: str | None
    skill: str
    triggers: tuple[LintTrigger, ...]
    semantic_questions: tuple[str, ...]
    mcp_queries: tuple[str, ...]
