#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

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
COLLECTION_NAME = "CleanCodeChunks"
VECTOR_NAME = "content"
CHUNKER_VERSION = "clean-code-semantic-v1"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_PROVIDER = "fastembed/cpu"
DEFAULT_WEAVIATE_URL = "http://127.0.0.1:8080"
DEFAULT_BATCH_SIZE = 64
MAX_SECTION_TOKENS = 1_200
TARGET_SECTION_TOKENS = 850
HTTP_NOT_FOUND = 404
PHRASE_BONUS_MIN_OVERLAP = 2
PLURAL_NORMALIZATION_MIN_LENGTH = 4
CONSERVATIVE_CONTEXT_THRESHOLD = 0.80
HIGH_CONFIDENCE_THRESHOLD = 0.72
EXACT_HIGH_CONFIDENCE_THRESHOLD = 0.40
MEDIUM_CONFIDENCE_THRESHOLD = 0.45
CHUNK_ID_NAMESPACE = uuid.UUID("fd1b279f-073e-5aa4-bf70-9f70446a3d8f")
EXACT_MATCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "be",
    "by",
    "code",
    "do",
    "for",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "thi",
    "this",
    "to",
    "when",
    "with",
}
NON_SPECIFIC_EXACT_ALIASES = {
    "clean code",
    "code smell",
    "comments",
    "error handling",
    "function smell",
    "functions",
    "function design",
    "planning guidance",
    "refactoring rule",
}
BROAD_CATEGORY_QUERY_TERMS = {
    "clean",
    "code",
    "comment",
    "comments",
    "error",
    "function",
    "handling",
    "guidance",
    "planning",
    "python",
    "refactoring",
    "rule",
    "smell",
    "typescript",
}
VAGUE_QUERY_TERMS = {"stuff", "thing", "things"}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CODE_FENCE_RE = re.compile(r"^\s*```")
CC_ID_RE = re.compile(r"\b(CC-\d{3})\b")
SLUG_RE = re.compile(r"[^a-z0-9]+")
WORD_RE = re.compile(r"[a-z0-9]+")
GRAPHQL_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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


def markdown_sections(path: Path, *, root: Path = ROOT) -> list[MarkdownSection]:
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


def create_schema_payload(*, collection_name: str = COLLECTION_NAME) -> JsonDict:
    return {
        "class": collection_name,
        "vectorConfig": {
            VECTOR_NAME: {
                "vectorIndexType": "hnsw",
                "vectorizer": {"none": {}},
            }
        },
        "properties": [
            {"name": "chunkId", "dataType": ["text"]},
            {"name": "sourceFile", "dataType": ["text"]},
            {"name": "sourceKind", "dataType": ["text"]},
            {"name": "recordId", "dataType": ["text"]},
            {"name": "title", "dataType": ["text"]},
            {"name": "topic", "dataType": ["text"]},
            {"name": "sectionPath", "dataType": ["text[]"]},
            {"name": "chunkKind", "dataType": ["text"]},
            {"name": "chunkIndex", "dataType": ["number"]},
            {"name": "ruleFamily", "dataType": ["text"]},
            {"name": "lintability", "dataType": ["text"]},
            {"name": "aliases", "dataType": ["text[]"]},
            {"name": "languages", "dataType": ["text[]"]},
            {"name": "lintCandidates", "dataType": ["text[]"]},
            {"name": "contentText", "dataType": ["text"]},
            {"name": "embeddingText", "dataType": ["text"]},
            {"name": "displayText", "dataType": ["text"]},
            {"name": "textHash", "dataType": ["text"]},
            {"name": "chunkerVersion", "dataType": ["text"]},
            {"name": "embeddingModel", "dataType": ["text"]},
            {"name": "embeddingProvider", "dataType": ["text"]},
            {"name": "createdAt", "dataType": ["date"]},
        ],
    }


def reset_collection(*, url: str, collection_name: str = COLLECTION_NAME) -> None:
    httpx = require_httpx()
    base_url = url.rstrip("/")
    with httpx.Client(timeout=120) as client:
        existing = client.get(f"{base_url}/v1/schema/{collection_name}")
        if existing.status_code != HTTP_NOT_FOUND:
            existing.raise_for_status()
            deleted = client.delete(f"{base_url}/v1/schema/{collection_name}")
            deleted.raise_for_status()
        created = client.post(
            f"{base_url}/v1/schema",
            json=create_schema_payload(collection_name=collection_name),
        )
        created.raise_for_status()


def embed_texts(texts: list[str], *, model_name: str, batch_size: int) -> list[list[float]]:
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise SystemExit("Install fastembed to embed clean-code chunks: python3 -m pip install fastembed") from exc
    model = TextEmbedding(model_name=model_name)
    return [[float(value) for value in vector] for vector in model.embed(texts, batch_size=batch_size)]


def ingest_chunks(
    *,
    chunks: list[CleanCodeChunk],
    url: str,
    collection_name: str = COLLECTION_NAME,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    httpx = require_httpx()
    base_url = url.rstrip("/")
    inserted = 0
    with httpx.Client(timeout=120) as client:
        for offset in range(0, len(chunks), batch_size):
            batch = chunks[offset : offset + batch_size]
            vectors = embed_texts(
                [chunk.embedding_text for chunk in batch],
                model_name=model_name,
                batch_size=batch_size,
            )
            objects = [
                {
                    "class": collection_name,
                    "id": chunk.object_id,
                    "properties": chunk.properties,
                    "vectors": {VECTOR_NAME: vector},
                }
                for chunk, vector in zip(batch, vectors, strict=True)
            ]
            response = client.post(f"{base_url}/v1/batch/objects", json={"objects": objects})
            response.raise_for_status()
            failures = batch_failures(response.json())
            if failures:
                raise RuntimeError(f"Weaviate rejected {len(failures)} objects: {failures[:3]}")
            inserted += len(batch)
    return inserted


def search_chunks(
    *,
    query: str,
    url: str,
    collection_name: str = COLLECTION_NAME,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    limit: int = 8,
) -> list[JsonDict]:
    httpx = require_httpx()
    vector = embed_texts([query], model_name=model_name, batch_size=1)[0]
    graphql_query = build_search_graphql_query(
        collection_name=collection_name,
        vector=vector,
        limit=limit,
    )
    response = httpx.post(f"{url.rstrip('/')}/v1/graphql", json={"query": graphql_query}, timeout=120)
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload.get("data", {}).get("Get", {}).get(collection_name, [])


def search_pattern_records(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-locals
    *,
    query: str,
    url: str,
    collection_name: str = COLLECTION_NAME,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    limit: int = 8,
    language: str = "any",
    rule_families: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    lintability: tuple[str, ...] = (),
    source_kinds: tuple[str, ...] = ("clean_code_pattern",),
) -> JsonDict:
    vector_limit = max(limit * 4, 25)
    vector_rows = search_chunks(
        query=query,
        url=url,
        collection_name=collection_name,
        model_name=model_name,
        limit=vector_limit,
    )
    return rank_pattern_rows(
        query=query,
        vector_rows=vector_rows,
        limit=limit,
        language=language,
        rule_families=rule_families,
        topics=topics,
        lintability=lintability,
        source_kinds=source_kinds,
    )


def rank_pattern_rows(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-locals
    *,
    query: str,
    vector_rows: list[JsonDict],
    limit: int = 8,
    language: str = "any",
    rule_families: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    lintability: tuple[str, ...] = (),
    source_kinds: tuple[str, ...] = ("clean_code_pattern",),
) -> JsonDict:
    rows_by_chunk_id: dict[str, JsonDict] = {}
    for row in [*vector_rows, *local_keyword_rows(query)]:
        chunk_id = str(row.get("chunkId", ""))
        if chunk_id:
            rows_by_chunk_id[chunk_id] = merge_search_rows(rows_by_chunk_id.get(chunk_id), row)

    filters = {
        "language": language,
        "rule_families": rule_families,
        "topics": topics,
        "lintability": lintability,
        "source_kinds": source_kinds,
    }
    ranked: list[JsonDict] = []
    for row in rows_by_chunk_id.values():
        if not row_matches_filters(row, filters):
            continue
        ranked.append(score_pattern_row(row, query=query, filters=filters))

    ranked.sort(key=lambda item: float(item["score"]), reverse=True)
    deduped = dedupe_pattern_results(ranked)
    results = deduped[:limit]
    return {
        "query": query,
        "filters_applied": filters,
        "results": results,
        "no_strong_match": not results or results[0]["confidence"] != "high",
    }


def local_keyword_rows(query: str) -> list[JsonDict]:
    query_terms = set(query_tokens(query))
    if not query_terms:
        return []
    matches: list[JsonDict] = []
    for chunk in build_chunks():
        haystack = " ".join(
            (
                chunk.record_id,
                chunk.title,
                chunk.topic,
                chunk.rule_family,
                chunk.lintability,
                " ".join(chunk.aliases),
                " ".join(chunk.lint_candidates),
                chunk.content_text[:600],
            )
        )
        if lexical_score(query_terms, haystack) > 0:
            matches.append(chunk.properties | {"_additional": {"id": chunk.object_id}})
    return matches


def merge_search_rows(existing: JsonDict | None, row: JsonDict) -> JsonDict:
    if existing is None:
        return row
    existing_distance = distance_for(existing)
    row_distance = distance_for(row)
    if existing_distance is None:
        return row
    if row_distance is None:
        return existing
    return row if row_distance < existing_distance else existing


def row_matches_filters(row: JsonDict, filters: JsonDict) -> bool:
    source_kinds = tuple(str(value) for value in filters["source_kinds"])
    if source_kinds and str(row.get("sourceKind", "")) not in source_kinds:
        return False

    language = str(filters["language"])
    languages = tuple(str(value) for value in row.get("languages", []))
    if language not in {"", "any", "both"} and language not in languages:
        return False
    if language == "both" and not {"typescript", "python"} <= set(languages):
        return False

    rule_families = {str(value) for value in filters["rule_families"]}
    if rule_families and str(row.get("ruleFamily", "")) not in rule_families:
        return False

    topics = {str(value) for value in filters["topics"]}
    if topics and str(row.get("topic", "")) not in topics:
        return False

    lintability = {str(value) for value in filters["lintability"]}
    return not lintability or str(row.get("lintability", "")) in lintability


def score_pattern_row(row: JsonDict, *, query: str, filters: JsonDict) -> JsonDict:
    query_terms = set(query_tokens(query))
    distance = distance_for(row)
    semantic_score = semantic_similarity(distance)
    keyword_score = lexical_score(query_terms, searchable_row_text(row))
    metadata_boost, match_reasons = metadata_boost_and_reasons(row, filters, query_terms)
    context_penalty, context_reasons = context_penalty_and_reasons(query_terms)
    match_reasons.extend(context_reasons)
    score = max(0.0, min(1.0, semantic_score * 0.60 + keyword_score * 0.25 + metadata_boost - context_penalty))
    confidence = confidence_for(score, match_reasons, semantic_score=semantic_score)
    return {
        "pattern_id": row.get("recordId", ""),
        "chunk_id": row.get("chunkId", ""),
        "title": row.get("title", ""),
        "topic": row.get("topic", ""),
        "rule_family": row.get("ruleFamily", ""),
        "lintability": row.get("lintability", ""),
        "languages": row.get("languages", []),
        "aliases": row.get("aliases", []),
        "lint_candidates": row.get("lintCandidates", []),
        "source_kind": row.get("sourceKind", ""),
        "chunk_kind": row.get("chunkKind", ""),
        "section_path": row.get("sectionPath", []),
        "score": round(score, 4),
        "confidence": confidence,
        "distance": distance,
        "match_reasons": match_reasons,
        "snippet": " ".join(str(row.get("contentText", "")).split())[:500],
        "source": {
            "source_file": row.get("sourceFile", ""),
            "source_kind": row.get("sourceKind", ""),
            "text_hash": row.get("textHash", ""),
        },
        "score_breakdown": {
            "semantic_score": round(semantic_score, 4),
            "keyword_score": round(keyword_score, 4),
            "metadata_boost": round(metadata_boost, 4),
            "context_penalty": round(context_penalty, 4),
        },
    }


def dedupe_pattern_results(rows: list[JsonDict]) -> list[JsonDict]:
    by_record_id: dict[str, JsonDict] = {}
    for row in rows:
        record_id = str(row.get("pattern_id") or row.get("chunk_id"))
        if record_id not in by_record_id or float(row["score"]) > float(by_record_id[record_id]["score"]):
            by_record_id[record_id] = row
    return sorted(by_record_id.values(), key=lambda item: float(item["score"]), reverse=True)


def metadata_boost_and_reasons(
    row: JsonDict,
    filters: JsonDict,
    query_terms: set[str],
) -> tuple[float, list[str]]:
    boost = 0.0
    reasons: list[str] = []
    source_kind = str(row.get("sourceKind", ""))
    if source_kind == "clean_code_pattern":
        boost += 0.05
        reasons.append("canonical clean-code pattern")

    language = str(filters["language"])
    languages = {str(value) for value in row.get("languages", [])}
    if language not in {"", "any"} and (language == "both" or language in languages):
        boost += 0.05
        reasons.append(f"language matched: {language}")

    lintability = str(row.get("lintability", ""))
    if lintability and lintability in set(filters["lintability"]):
        boost += 0.05
        reasons.append(f"lintability matched: {lintability}")

    exact_terms = exact_match_terms(row, query_terms)
    if exact_terms:
        boost += 0.15
        reasons.append(f"matched exact terms: {', '.join(exact_terms[:4])}")

    if not reasons:
        reasons.append("semantic similarity")
    return min(boost, 0.30), reasons


def context_penalty_and_reasons(query_terms: set[str]) -> tuple[float, list[str]]:
    safe_context_terms = {"generated", "fixture", "fixtures", "test", "tests"}
    matched = sorted(query_terms & safe_context_terms)
    reasons: list[str] = []
    if matched:
        reasons.append(f"conservative context: {', '.join(matched)}")
    meaningful_terms = query_terms - EXACT_MATCH_STOPWORDS
    if meaningful_terms and meaningful_terms <= BROAD_CATEGORY_QUERY_TERMS:
        reasons.append("conservative context: broad category query")
    if meaningful_terms and meaningful_terms <= VAGUE_QUERY_TERMS:
        reasons.append("conservative context: vague query")
    if {"todo", "tracked", "issue"} <= query_terms:
        reasons.append("conservative context: compliant tracked TODO")
    if not reasons:
        return 0.0, []
    return 0.35, reasons


def exact_match_terms(row: JsonDict, query_terms: set[str]) -> list[str]:
    values = [
        str(row.get("recordId", "")),
        str(row.get("title", "")),
        *[str(value) for value in row.get("aliases", [])],
        *[str(value) for value in row.get("lintCandidates", [])],
    ]
    matched: list[str] = []
    for value in values:
        normalized_value = " ".join(query_tokens(value))
        if normalized_value in NON_SPECIFIC_EXACT_ALIASES:
            continue
        terms = set(query_tokens(value))
        meaningful_terms = terms - EXACT_MATCH_STOPWORDS
        if terms and meaningful_terms and terms <= query_terms:
            matched.append(value)
    return unique_strings(matched)


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


def searchable_row_text(row: JsonDict) -> str:
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


def distance_for(row: JsonDict) -> float | None:
    additional = row.get("_additional")
    if not isinstance(additional, dict):
        return None
    distance = additional.get("distance")
    return float(distance) if isinstance(distance, int | float) else None


def confidence_for(score: float, match_reasons: list[str], *, semantic_score: float) -> Confidence:
    if any(reason.startswith("conservative context") for reason in match_reasons):
        return "low" if score < CONSERVATIVE_CONTEXT_THRESHOLD else "medium"
    has_exact = any(reason.startswith("matched exact terms") for reason in match_reasons)
    if score >= HIGH_CONFIDENCE_THRESHOLD or (
        has_exact and semantic_score > 0 and score >= EXACT_HIGH_CONFIDENCE_THRESHOLD
    ):
        return "high"
    if score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def build_search_graphql_query(
    *,
    collection_name: str,
    vector: list[float],
    limit: int,
) -> str:
    if not GRAPHQL_NAME_RE.fullmatch(collection_name):
        raise ValueError("collection_name must be a valid GraphQL identifier")
    return (
        "{ Get { "
        f"{collection_name}("
        f"nearVector: {{vector: {json.dumps(vector)}, targetVectors: [{json.dumps(VECTOR_NAME)}]}}, "
        f"limit: {limit}"
        ") { "
        "chunkId recordId sourceFile sourceKind title topic sectionPath chunkKind "
        "ruleFamily lintability aliases languages lintCandidates contentText textHash "
        "_additional { id distance } "
        "} } }"
    )


def batch_failures(payload: JsonDict) -> list[JsonDict]:
    rows = payload if isinstance(payload, list) else payload.get("objects", [])
    return [row for row in rows if isinstance(row, dict) and not is_successful_batch_row(row)]


def is_successful_batch_row(row: JsonDict) -> bool:
    result = row.get("result")
    status = result.get("status") if isinstance(result, dict) else row.get("status")
    return isinstance(status, str) and status.upper() in {"SUCCESS", "OK"}


def detected_record_id(value: str) -> str:
    match = CC_ID_RE.search(value)
    return match.group(1) if match else ""


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


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = re.sub(r"\s+", " ", value.strip())
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def object_id_for(chunk_id: str) -> str:
    return str(uuid.uuid5(CHUNK_ID_NAMESPACE, chunk_id))


def approximate_tokens(value: str) -> int:
    return max(1, len(re.findall(r"\S+", value)))


def require_httpx() -> Any:
    try:
        import httpx
    except ImportError as exc:
        raise SystemExit("Install httpx to talk to Weaviate: python3 -m pip install httpx") from exc
    return httpx
