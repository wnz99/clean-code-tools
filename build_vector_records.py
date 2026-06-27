#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "clean-code-examples.md"
OUTPUT = ROOT / "clean-code-patterns.jsonl"


FAMILY_RULES = [
    ("comment", "comments"),
    ("test", "tests"),
    ("name", "naming"),
    ("function", "functions"),
    ("argument", "function_arguments"),
    ("class", "classes"),
    ("error", "error_handling"),
    ("exception", "error_handling"),
    ("boundaries", "boundaries"),
    ("boundary", "boundaries"),
    ("concurr", "concurrency"),
    ("thread", "concurrency"),
    ("format", "formatting"),
    ("object", "objects_data"),
    ("data", "objects_data"),
    ("system", "systems"),
    ("design", "design"),
    ("refactor", "refactoring"),
    ("lint", "linting"),
]


ALIAS_BY_FAMILY = {
    "comments": ["comment smell", "stale comment", "documentation noise", "comment guidance"],
    "tests": ["unit test", "test smell", "test design", "test quality"],
    "naming": ["naming smell", "identifier name", "semantic naming", "readable name"],
    "functions": ["function smell", "single responsibility", "small function", "function design"],
    "function_arguments": ["argument smell", "parameter smell", "call site clarity", "function signature"],
    "classes": ["class smell", "cohesion", "single responsibility", "class design"],
    "error_handling": ["error handling", "exception design", "failure boundary", "error contract"],
    "boundaries": ["boundary design", "adapter", "third party code", "integration seam"],
    "concurrency": ["concurrency smell", "shared state", "threading", "async coordination"],
    "formatting": ["formatting", "layout", "readability", "code style"],
    "objects_data": ["data structure", "object design", "encapsulation", "data abstraction"],
    "systems": ["system design", "dependency injection", "composition root", "architecture"],
    "design": ["simple design", "emergent design", "expressive code", "minimal design"],
    "refactoring": ["refactoring", "successive refinement", "incremental change", "safe change"],
    "linting": ["lint rule", "static analysis", "code smell detection", "automated review"],
}


TITLE_ALIASES = {
    "flag": ["flag argument", "boolean parameter", "selector argument", "boolean mode"],
    "magic": ["magic number", "unnamed literal", "hard-coded value", "named constant"],
    "train wreck": ["train wreck", "message chain", "deep property chain", "transitive navigation"],
    "demeter": ["law of demeter", "least knowledge", "message chain", "object navigation"],
    "null": ["null handling", "none handling", "missing value", "absence contract"],
    "duplicate": ["duplication", "repeated knowledge", "DRY", "copy paste logic"],
    "one thing": ["do one thing", "single responsibility", "mixed responsibility", "function cohesion"],
    "side effect": ["hidden side effect", "mutation", "command query separation", "unexpected write"],
    "boundary": ["boundary condition", "edge case", "limit", "off by one"],
    "negative": ["negative conditional", "double negative", "positive predicate", "readable condition"],
    "static": ["static state", "global state", "hidden dependency", "test isolation"],
    "temporal": ["temporal coupling", "ordering dependency", "hidden sequence", "call order"],
    "import": ["import list", "dependency list", "module dependency", "wildcard import"],
    "enum": ["enum", "closed set", "constant group", "named variants"],
    "todo": ["todo comment", "tracked work", "issue marker", "technical debt marker"],
}


HIGH_LINT_TERMS = [
    "flag",
    "too many arguments",
    "output arguments",
    "dead code",
    "commented",
    "magic",
    "null",
    "todo",
    "long",
    "complex condition",
    "negative",
    "import",
    "coverage",
    "tests should be fast",
    "build requires",
    "tests require",
]


REVIEW_ONLY_TERMS = [
    "attitude",
    "schools",
    "art of",
    "how did",
    "rough draft",
    "city",
    "standards wisely",
]


def parse_sections(text: str) -> list[dict[str, str]]:
    raw_sections = [section for section in text.split("\n## ") if section.startswith("CC-")]
    records = []
    for raw in raw_sections:
        lines = raw.splitlines()
        heading = lines[0].strip()
        match = re.match(r"^(CC-\d{3})\s+(.+)$", heading)
        if not match:
            raise ValueError(f"Bad heading: {heading}")

        section = "\n".join(lines[1:])
        topic = extract_field(section, "Topic")
        description = extract_field(section, "Description")
        lint = extract_field(section, "Lint candidates")
        ts = extract_code(section, "ts")
        py = extract_code(section, "python")
        records.append(
            {
                "id": match.group(1),
                "title": match.group(2),
                "topic": topic,
                "description": description,
                "lint": lint,
                "ts": ts,
                "py": py,
            }
        )
    return records


def extract_field(section: str, name: str) -> str:
    pattern = rf"^{re.escape(name)}:\s*(.+)$"
    match = re.search(pattern, section, re.MULTILINE)
    if not match:
        raise ValueError(f"Missing {name}")
    return match.group(1).strip()


def extract_code(section: str, language: str) -> str:
    match = re.search(rf"```{language}\n(.*?)\n```", section, re.DOTALL)
    if not match:
        raise ValueError(f"Missing {language} block")
    return match.group(1).strip()


def infer_family(title: str, topic: str) -> str:
    haystack = f"{title} {topic}".lower()
    for needle, family in FAMILY_RULES:
        if needle in haystack:
            return family
    return "clean_code"


def aliases_for(title: str, topic: str, family: str) -> list[str]:
    title_terms = normalize_terms(title)
    aliases = [title.lower(), *title_terms, *ALIAS_BY_FAMILY.get(family, [])]
    lower_title = title.lower()
    for needle, extra_aliases in TITLE_ALIASES.items():
        if needle in lower_title:
            aliases.extend(extra_aliases)
    aliases.append(topic.lower().replace("chapter 17: smells and heuristics - ", ""))
    aliases.extend(["clean code", "code smell", "planning guidance", "refactoring rule"])
    return unique_clean(aliases)[:12]


def normalize_terms(title: str) -> list[str]:
    title = re.sub(r"^[A-Z]\d+\s+", "", title)
    words = re.sub(r"[^A-Za-z0-9]+", " ", title).strip().lower()
    terms = [words]
    if len(words.split()) > 2:
        terms.append(" ".join(words.split()[:2]))
        terms.append(" ".join(words.split()[-2:]))
    return terms


def unique_clean(values: list[str]) -> list[str]:
    seen = set()
    cleaned = []
    for value in values:
        value = re.sub(r"\s+", " ", value.strip().lower())
        if len(value) < 2 or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def infer_lintability(title: str, lint: str) -> str:
    haystack = f"{title} {lint}".lower()
    if any(term in haystack for term in REVIEW_ONLY_TERMS):
        return "review_only"
    if any(term in haystack for term in HIGH_LINT_TERMS):
        return "high"
    if "no direct lint" in haystack or "review" in haystack:
        return "review_only"
    if "flag" in haystack or "detect" in haystack or "warn" in haystack:
        return "medium"
    return "low"


def build_problem(title: str, description: str, aliases: list[str]) -> str:
    return (
        f"Code has a clean-code risk related to {title.lower()}: {description} "
        f"Search terms that should match this issue include {', '.join(aliases[:5])}."
    )


def build_use_when(title: str, family: str, description: str) -> str:
    base = f"Use this pattern when planning or reviewing code where {description[0].lower() + description[1:]}"
    family_guidance = {
        "comments": " It is especially relevant when a comment is explaining confusing code, stale behavior, or nonlocal context.",
        "tests": " It is especially relevant when tests are hard to read, flaky, broad, slow, or missing boundary behavior.",
        "naming": " It is especially relevant when readers must translate vague identifiers into domain meaning.",
        "functions": " It is especially relevant when a function mixes abstraction levels, responsibilities, or side effects.",
        "function_arguments": " It is especially relevant when a call site is unclear or a parameter changes behavior by mode.",
        "concurrency": " It is especially relevant when async or threaded code shares mutable state or depends on ordering.",
        "error_handling": " It is especially relevant when callers need a clear failure contract.",
    }
    return base + family_guidance.get(family, " It is relevant when the pattern makes the code easier to change without hiding local conventions.")


def build_avoid_when(family: str) -> str:
    guidance = {
        "comments": "Avoid applying this mechanically when a short comment records an external constraint, legal requirement, or non-obvious tradeoff that code cannot express.",
        "tests": "Avoid applying this mechanically when an integration or characterization test intentionally covers a wider workflow.",
        "naming": "Avoid renaming when the current term is a stable domain word, public API name, or project convention.",
        "functions": "Avoid extracting helpers that only hide simple logic or make the call path harder to follow.",
        "function_arguments": "Avoid wrapping parameters when the existing call is already clear and the values do not form a stable concept.",
        "concurrency": "Avoid adding concurrency abstractions unless shared state, ordering, or throughput needs justify the extra complexity.",
        "error_handling": "Avoid changing error style when the surrounding API has a deliberate return-value or result-object contract.",
    }
    return guidance.get(
        family,
        "Avoid applying this mechanically when local project conventions or a simpler direct implementation communicate the intent better.",
    )


def bad_examples_for(title: str, family: str, good_ts: str, good_py: str) -> dict[str, str]:
    lower = title.lower()
    if "flag" in lower or "selector" in lower:
        return {
            "typescript": "sendInvoice(invoice, true);",
            "python": "send_invoice(invoice, reminder=True)",
        }
    if "magic" in lower or "searchable" in lower or "named constant" in lower:
        return {
            "typescript": "if (failedAttempts >= 5) lockAccount(userId);",
            "python": "if failed_attempts >= 5:\n    lock_account(user_id)",
        }
    if "commented" in lower:
        return {
            "typescript": "// await publishReceipt(receipt);\nawait saveReceipt(receipt);",
            "python": "# publish_receipt(receipt)\nsave_receipt(receipt)",
        }
    if "null" in lower:
        return {
            "typescript": "return invoice ?? null;",
            "python": "return invoice or None",
        }
    if "train wreck" in lower or "demeter" in lower or "transitive" in lower:
        return {
            "typescript": "const city = order.customer.address.city;",
            "python": "city = order.customer.address.city",
        }
    if "negative" in lower:
        return {
            "typescript": "if (!isNotDisabled(account)) allowTransfer(account);",
            "python": "if not is_not_disabled(account):\n    allow_transfer(account)",
        }
    if "too many arguments" in lower:
        return {
            "typescript": "createDelivery(orderId, startsAt, endsAt, timezone, carrier);",
            "python": "create_delivery(order_id, starts_at, ends_at, timezone, carrier)",
        }
    if "one thing" in lower or "single responsibility" in lower:
        return {
            "typescript": "async function submitOrder(input) { validate(input); await db.save(input); await email(input); }",
            "python": "def submit_order(payload):\n    validate(payload)\n    db.save(payload)\n    email(payload)",
        }
    if family == "comments":
        return {
            "typescript": "// increments retry count\nretryCount += 1;",
            "python": "# increments retry count\nretry_count += 1",
        }
    if family == "tests":
        return {
            "typescript": "it('works', () => { expect(a()).toBe(1); expect(b()).toBe(2); });",
            "python": "def test_works():\n    assert a() == 1\n    assert b() == 2",
        }
    if family == "naming":
        return {
            "typescript": "const data = getData(x);",
            "python": "data = get_data(x)",
        }
    if family == "concurrency":
        return {
            "typescript": "sharedCache[key] = await loadValue(key);",
            "python": "shared_cache[key] = await load_value(key)",
        }
    if family == "error_handling":
        return {
            "typescript": "return { ok: false, errorCode: 'FAILED' };",
            "python": "return {'ok': False, 'error_code': 'FAILED'}",
        }
    return {
        "typescript": summarize_as_anti_example(good_ts, "typescript"),
        "python": summarize_as_anti_example(good_py, "python"),
    }


def summarize_as_anti_example(code: str, language: str) -> str:
    if language == "typescript":
        return "const result = process(data);"
    return "result = process(data)"


def lint_candidates_for(lint: str) -> list[str]:
    lint = lint.strip()
    if lint.lower().startswith("candidate lint/search rule:"):
        lint = lint.split(":", 1)[1].strip()
    return [lint[:1].upper() + lint[1:]]


def display_text(record: dict) -> str:
    return (
        f"{record['id']} {record['title']}\n"
        f"Topic: {record['topic']}\n"
        f"Aliases: {', '.join(record['aliases'])}\n"
        f"Problem: {record['problem']}\n"
        f"Use when: {record['use_when']}\n"
        f"Avoid when: {record['avoid_when']}\n"
        f"Good TypeScript:\n{record['good_examples']['typescript']}\n"
        f"Good Python:\n{record['good_examples']['python']}\n"
        f"Bad TypeScript:\n{record['bad_examples']['typescript']}\n"
        f"Bad Python:\n{record['bad_examples']['python']}\n"
        f"Lint candidates: {'; '.join(record['lint_candidates'])}\n"
        f"Lintability: {record['lintability']}"
    )


def embedding_text(record: dict) -> str:
    return (
        f"Clean code pattern {record['id']}: {record['title']}. "
        f"Topic: {record['topic']}. Rule family: {record['rule_family']}. "
        f"Aliases and smell terms: {', '.join(record['aliases'])}. "
        f"Problem: {record['problem']} "
        f"Use when: {record['use_when']} "
        f"Avoid when: {record['avoid_when']} "
        f"Lint candidates: {'; '.join(record['lint_candidates'])}. "
        f"Good TypeScript example: {record['good_examples']['typescript']} "
        f"Good Python example: {record['good_examples']['python']} "
        f"Bad TypeScript example: {record['bad_examples']['typescript']} "
        f"Bad Python example: {record['bad_examples']['python']}"
    )


def enrich(parsed: dict[str, str]) -> dict:
    family = infer_family(parsed["title"], parsed["topic"])
    aliases = aliases_for(parsed["title"], parsed["topic"], family)
    record = {
        "id": parsed["id"],
        "title": parsed["title"],
        "topic": parsed["topic"],
        "rule_family": family,
        "aliases": aliases,
        "problem": build_problem(parsed["title"], parsed["description"], aliases),
        "use_when": build_use_when(parsed["title"], family, parsed["description"]),
        "avoid_when": build_avoid_when(family),
        "good_examples": {
            "typescript": parsed["ts"],
            "python": parsed["py"],
        },
        "bad_examples": bad_examples_for(parsed["title"], family, parsed["ts"], parsed["py"]),
        "lint_candidates": lint_candidates_for(parsed["lint"]),
        "lintability": infer_lintability(parsed["title"], parsed["lint"]),
        "source": {
            "kind": "clean_code_original_example_enriched_from_markdown",
            "version": 1,
        },
    }
    record["embedding_text"] = embedding_text(record)
    record["display_text"] = display_text(record)
    return record


def validate(records: list[dict]) -> None:
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate IDs found")
    for record in records:
        for key in [
            "id",
            "title",
            "topic",
            "rule_family",
            "aliases",
            "problem",
            "use_when",
            "avoid_when",
            "good_examples",
            "bad_examples",
            "lint_candidates",
            "lintability",
            "embedding_text",
            "display_text",
            "source",
        ]:
            if key not in record:
                raise ValueError(f"{record.get('id', '<unknown>')} missing {key}")
        if len(record["aliases"]) < 3:
            raise ValueError(f"{record['id']} has too few aliases")
        if len(record["embedding_text"].split()) < 120:
            raise ValueError(f"{record['id']} embedding_text too short")


def main() -> None:
    parsed = parse_sections(SOURCE.read_text())
    records = [enrich(section) for section in parsed]
    validate(records)
    with OUTPUT.open("w") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(records)} records to {OUTPUT}")


if __name__ == "__main__":
    main()
