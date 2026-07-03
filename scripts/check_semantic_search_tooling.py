#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

from _mcp_app import load_semantic_module

ROOT = Path(__file__).resolve().parents[1]


def load_source_records() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (ROOT / "data" / "clean-code-patterns.jsonl").read_text().splitlines()
        if line.strip()
    ]


def assert_source_record_contract(records: list[dict[str, object]]) -> None:
    assert len(records) == 264
    for record in records:
        assert "embedding_text" not in record
        assert "display_text" not in record
        for group in ("good_examples", "bad_examples"):
            group_examples = record[group]
            assert isinstance(group_examples, dict)
            for language in ("typescript", "python"):
                examples = group_examples[language]
                assert isinstance(examples, str | list)
                if isinstance(examples, list):
                    assert examples
                    assert all(
                        isinstance(example, str) and example.strip()
                        for example in examples
                    )


def assert_chunk_contract(semantic: object, chunks: list[object]) -> None:
    by_kind = {}
    for chunk in chunks:
        by_kind[chunk.chunk_kind] = by_kind.get(chunk.chunk_kind, 0) + 1
    assert by_kind["pattern_record"] == 264
    assert by_kind["markdown_section"] >= 40
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert len({chunk.object_id for chunk in chunks}) == len(chunks)
    for chunk in chunks:
        uuid.UUID(chunk.object_id)
        assert chunk.embedding_text
        assert chunk.text_hash == semantic.sha256_text(chunk.embedding_text)

    by_chunk_id = {chunk.chunk_id: chunk for chunk in chunks}
    assert "pattern:CC-043" in by_chunk_id
    assert "pattern:CC-068" in by_chunk_id
    assert "pattern:CC-107" in by_chunk_id
    assert by_chunk_id["pattern:CC-043"].languages == ("typescript", "python")
    assert "flag argument" in " ".join(by_chunk_id["pattern:CC-043"].aliases)


def assert_schema_and_search_contract(semantic: object) -> None:
    schema = semantic.create_schema_payload()
    assert schema["class"] == semantic.COLLECTION_NAME
    assert schema["vectorConfig"][semantic.VECTOR_NAME]["vectorizer"] == {"none": {}}
    property_names = {property_config["name"] for property_config in schema["properties"]}
    for required in (
        "chunkId",
        "recordId",
        "sourceFile",
        "sourceKind",
        "sectionPath",
        "ruleFamily",
        "lintability",
        "embeddingText",
        "textHash",
        "embeddingModel",
    ):
        assert required in property_names

    query = semantic.build_search_graphql_query(
        collection_name=semantic.COLLECTION_NAME,
        vector=[0.1, 0.2, 0.3],
        limit=5,
    )
    assert "nearVector" in query
    assert 'targetVectors: ["content"]' in query
    assert "chunkId recordId sourceFile" in query

    payload = {"data": {"Get": {semantic.COLLECTION_NAME: [{"chunkId": "pattern:CC-043"}]}}}
    assert semantic.search_rows_from_payload(
        payload,
        collection_name=semantic.COLLECTION_NAME,
    ) == [{"chunkId": "pattern:CC-043"}]
    assert semantic.search_rows_from_payload({}, collection_name=semantic.COLLECTION_NAME) == []
    try:
        semantic.search_rows_from_payload(
            {"errors": [{"message": "bad query"}]},
            collection_name=semantic.COLLECTION_NAME,
        )
    except RuntimeError as exc:
        assert "bad query" in str(exc)
    else:
        raise AssertionError("expected Weaviate GraphQL errors to raise")


def assert_markdown_contract(semantic: object) -> None:
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        doc = tmp / "sample.md"
        doc.write_text(
            "# Root\n\n"
            "Intro.\n\n"
            "## Section\n\n"
            "Before.\n\n"
            "```ts\n"
            "const heading = '## not a heading';\n"
            "```\n\n"
            "After.\n"
        )
        sections = semantic.markdown_sections(doc, root=tmp)
        assert len(sections) == 2
        assert sections[1].heading == "Section"
        assert "## not a heading" in sections[1].body


def main() -> None:
    semantic = load_semantic_module()

    chunks = semantic.build_chunks()
    assert_source_record_contract(load_source_records())
    assert_chunk_contract(semantic, chunks)
    assert_schema_and_search_contract(semantic)
    assert_markdown_contract(semantic)

    print("semantic_search_tooling_check=ok")


if __name__ == "__main__":
    main()
