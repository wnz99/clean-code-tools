from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PYTHON_SRC = ROOT / "src" / "python"
if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from mcp_server import ranking  # noqa: E402


def vector_row(
    chunk_id: str,
    *,
    record_id: str,
    title: str,
    distance: float | None = 0.1,
    language: str = "typescript",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "chunkId": chunk_id,
        "recordId": record_id,
        "title": title,
        "topic": "Function Design",
        "ruleFamily": "naming" if language == "typescript" else "validation",
        "lintability": "high",
        "languages": [language],
        "aliases": [title],
        "lintCandidates": [f"Flag {title}"],
        "sourceKind": "clean_code_pattern",
        "chunkKind": "pattern_record",
        "sectionPath": [],
        "contentText": f"{title} keeps rules explicit.",
        "sourceFile": "clean-code-patterns.jsonl",
        "textHash": f"hash-{chunk_id}",
    }
    if distance is not None:
        row["_additional"] = {"distance": distance}
    return row


class RankingTest(unittest.TestCase):
    def test_rank_pattern_rows_merges_duplicate_chunks_and_filters(self) -> None:
        lower_distance = vector_row(
            "pattern:CC-001",
            record_id="CC-001",
            title="Named Payment State",
            distance=0.08,
        )
        higher_distance = vector_row(
            "pattern:CC-001",
            record_id="CC-001",
            title="Named Payment State",
            distance=0.5,
        )
        filtered_out = vector_row(
            "pattern:CC-002",
            record_id="CC-002",
            title="Python Boundary Model",
            distance=0.01,
            language="python",
        )

        original_keyword_rows = ranking.local_keyword_rows
        try:
            ranking.local_keyword_rows = lambda _query: []
            result = ranking.rank_pattern_rows(
                query="named payment state",
                vector_rows=[higher_distance, filtered_out, lower_distance],
                language="typescript",
                rule_families=("naming",),
                limit=5,
            )
        finally:
            ranking.local_keyword_rows = original_keyword_rows

        self.assertFalse(result["no_strong_match"])
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["chunk_id"], "pattern:CC-001")
        self.assertEqual(result["results"][0]["distance"], 0.08)

    def test_search_pattern_records_uses_vector_limit_and_index_path(self) -> None:
        calls: list[dict[str, Any]] = []

        def fake_search_chunks(**kwargs: Any) -> list[dict[str, Any]]:
            calls.append(kwargs)
            return [
                vector_row(
                    "pattern:CC-010",
                    record_id="CC-010",
                    title="Boundary Validation",
                    distance=0.05,
                )
            ]

        original_search_chunks = ranking.search_chunks
        original_keyword_rows = ranking.local_keyword_rows
        try:
            with tempfile.TemporaryDirectory() as raw_tmp:
                index_path = str(Path(raw_tmp) / "custom-index.sqlite")
                ranking.search_chunks = fake_search_chunks
                ranking.local_keyword_rows = lambda _query: []
                result = ranking.search_pattern_records(
                    query="boundary validation",
                    index_path=index_path,
                    model_name="test-model",
                    limit=3,
                )
        finally:
            ranking.search_chunks = original_search_chunks
            ranking.local_keyword_rows = original_keyword_rows

        self.assertEqual(calls[0]["index_path"], index_path)
        self.assertEqual(calls[0]["model_name"], "test-model")
        self.assertEqual(calls[0]["limit"], 25)
        self.assertEqual(result["results"][0]["pattern_id"], "CC-010")

    def test_local_keyword_rows_returns_matching_corpus_chunks(self) -> None:
        rows = ranking.local_keyword_rows("boolean flag argument")

        self.assertGreater(len(rows), 0)
        self.assertTrue(all("chunkId" in row for row in rows))

    def test_merge_search_rows_prefers_available_and_nearest_distance(self) -> None:
        existing = vector_row("pattern:CC-001", record_id="CC-001", title="A", distance=None)
        row = vector_row("pattern:CC-001", record_id="CC-001", title="A", distance=0.3)
        self.assertIs(ranking.merge_search_rows(existing, row), row)

        existing = vector_row("pattern:CC-001", record_id="CC-001", title="A", distance=0.2)
        row = vector_row("pattern:CC-001", record_id="CC-001", title="A", distance=None)
        self.assertIs(ranking.merge_search_rows(existing, row), existing)

        farther = vector_row("pattern:CC-001", record_id="CC-001", title="A", distance=0.4)
        nearer = vector_row("pattern:CC-001", record_id="CC-001", title="A", distance=0.1)
        self.assertIs(ranking.merge_search_rows(farther, nearer), nearer)


if __name__ == "__main__":
    unittest.main()
