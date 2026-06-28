#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

PHRASE_BONUS_MIN_OVERLAP = 2
PLURAL_NORMALIZATION_MIN_LENGTH = 4
SLUG_RE = re.compile(r"[^a-z0-9]+")
WORD_RE = re.compile(r"[a-z0-9]+")
CC_ID_RE = re.compile(r"\b(CC-\d{3})\b")


def semantic_similarity(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - distance))


def lexical_score(query_terms: set[str], haystack: str) -> float:
    if not query_terms:
        return 0.0
    haystack_terms = set(query_tokens(haystack))
    if not haystack_terms:
        return 0.0
    overlap = query_terms & haystack_terms
    phrase_bonus = 0.2 if overlap and len(overlap) >= PHRASE_BONUS_MIN_OVERLAP else 0.0
    return min(1.0, len(overlap) / len(query_terms) + phrase_bonus)


def searchable_row_text(row: dict[str, Any]) -> str:
    return " ".join(
        [
            str(row.get("recordId", "")),
            str(row.get("title", "")),
            str(row.get("topic", "")),
            str(row.get("ruleFamily", "")),
            str(row.get("lintability", "")),
            " ".join(str(value) for value in row.get("aliases", [])),
            " ".join(str(value) for value in row.get("lintCandidates", [])),
            str(row.get("contentText", "")),
        ]
    )


def query_tokens(value: str) -> list[str]:
    return [normalize_token(token) for token in WORD_RE.findall(value.lower())]


def normalize_token(value: str) -> str:
    if len(value) > PLURAL_NORMALIZATION_MIN_LENGTH and value.endswith("s"):
        return value[:-1]
    return value


def detected_record_id(value: str) -> str:
    match = CC_ID_RE.search(value)
    return match.group(1) if match else ""


def languages_in_text(text: str) -> tuple[str, ...]:
    languages: list[str] = []
    if "```ts" in text or "TypeScript" in text:
        languages.append("typescript")
    if "```python" in text or "Python" in text:
        languages.append("python")
    return tuple(languages)


def lint_candidates_in_text(text: str) -> tuple[str, ...]:
    return tuple(
        line.split(":", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith("Lint candidates:")
    )


def slug(value: str) -> str:
    normalized = SLUG_RE.sub("-", value.lower()).strip("-")
    return normalized[:96] or "section"


def slugless(value: str) -> str:
    return re.sub(r"^[#`\s]+|[#`\s]+$", "", value)


def clean_topic(value: str) -> str:
    topic = re.sub(r"^chapter\s+\d+:\s*", "", value, flags=re.IGNORECASE).strip()
    return re.sub(r"^smells and heuristics\s*-\s*", "", topic, flags=re.IGNORECASE).strip()


def clean_alias(value: str) -> str:
    alias = clean_topic(value)
    return "" if re.fullmatch(r"chapter\s+\d+", alias, flags=re.IGNORECASE) else alias


def clean_topic_text(value: str) -> str:
    value = re.sub(r"Chapter\s+\d+:\s*", "", value)
    value = re.sub(r"\bChapter\s+\d+\s+", "", value)
    return re.sub(r"Smells and Heuristics\s*-\s*", "", value)


def approximate_tokens(value: str) -> int:
    return max(1, len(re.findall(r"\S+", value)))
