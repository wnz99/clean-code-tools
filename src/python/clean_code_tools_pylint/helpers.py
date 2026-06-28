from __future__ import annotations

import re
from typing import Any

from astroid import nodes

TODO_PATTERN = re.compile(r"^(TODO|FIXME|XXX)\([A-Z][A-Z0-9]+-\d+\):\s+\S", re.IGNORECASE)
TODO_SEGMENT = re.compile(r"\b(?:TODO|FIXME|XXX)\b[^\n;]*", re.IGNORECASE)
SELECTOR_PARAM_NAMES = (
    "flag",
    "mode",
    "option",
    "type",
    "kind",
    "variant",
    "selector",
    "enabled",
    "disabled",
    "dry_run",
    "verbose",
    "silent",
    "force",
    "skip",
    "include",
    "exclude",
)
MUTATOR_METHODS = {
    "add",
    "append",
    "clear",
    "discard",
    "extend",
    "insert",
    "pop",
    "popitem",
    "remove",
    "reverse",
    "setdefault",
    "sort",
    "update",
}
ALLOWED_LITERAL_CALLS = {
    "bool",
    "bytes",
    "dict",
    "float",
    "int",
    "len",
    "list",
    "print",
    "range",
    "repr",
    "set",
    "str",
    "tuple",
}
STATUS_WORD = re.compile(
    r"(?:^|[_\s-])(active|approved|cancelled|canceled|draft|failed|paid|pending|rejected|retry|suspended)(?:$|[_\s-])",
    re.IGNORECASE,
)
MIN_CODE_COMMENT_LENGTH = 4
MIN_SEPARATOR_LENGTH = 8
MIN_POLICY_STRING_LENGTH = 2
MIN_SHARED_COMMENT_WORDS = 2
REDUNDANT_COMMENT_OVERLAP_RATIO = 0.65
MAX_ATTRIBUTE_CHAIN_DEPTH = 3


def clean_comment(comment: str) -> str:
    return comment.lstrip("#").strip()


def normalized_words(value: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9]+", re.sub(r"[_$]+", " ", value).lower())


def is_likely_code_comment(text: str) -> bool:
    if len(text.strip()) < MIN_CODE_COMMENT_LENGTH:
        return False
    code_patterns = (
        r"\b(await|def|class|return|raise|if|for|while|match|import|from|with|try|except)\b",
        r"(?:^|\s)[\w.]+\([^)]*\)\s*$",
        r"^\s*[\w.]+\s*=\s*.+$",
        r"[{}\[\]]",
        r"->",
    )
    return any(re.search(pattern, text) for pattern in code_patterns)


def is_separator_comment(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    return len(compact) >= MIN_SEPARATOR_LENGTH and bool(re.fullmatch(r"[-=*_/#]+", compact))


def is_byline_or_date(text: str) -> bool:
    byline = r"\b(author|created by|written by|modified by|last modified|since)\b"
    date = r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b"
    return bool(re.search(byline, text, re.IGNORECASE) or re.search(date, text))


def annotation_is_bool(annotation: nodes.NodeNG | None) -> bool:
    return isinstance(annotation, nodes.Name) and annotation.name == "bool"


def name_looks_like_selector(name: str) -> bool:
    lower_name = name.lower()
    return any(selector in lower_name for selector in SELECTOR_PARAM_NAMES)


def call_name(node: nodes.Call) -> str | None:
    func = node.func
    if isinstance(func, nodes.Name):
        return func.name
    if isinstance(func, nodes.Attribute):
        return func.attrname
    return None


def root_name(node: nodes.NodeNG) -> str | None:
    current = node
    while isinstance(current, (nodes.Attribute, nodes.Subscript)):
        current = current.expr if isinstance(current, nodes.Attribute) else current.value
    if isinstance(current, nodes.Name):
        return current.name
    return None


def is_uppercase_assignment(node: nodes.Const) -> bool:
    parent = node.parent
    if not isinstance(parent, (nodes.Assign, nodes.AnnAssign)):
        return False
    targets = parent.targets if isinstance(parent, nodes.Assign) else [parent.target]
    return any(isinstance(target, nodes.AssignName) and target.name.isupper() for target in targets)


def literal_looks_like_policy(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return value not in {-1, 0, 1}
    if not isinstance(value, str) or len(value) < MIN_POLICY_STRING_LENGTH:
        return False
    return bool(
        re.fullmatch(r"[A-Z][A-Z0-9_]+", value)
        or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
        or STATUS_WORD.search(value)
    )


def is_allowed_literal_context(node: nodes.Const) -> bool:
    if is_uppercase_assignment(node):
        return True
    current = node.parent
    while current is not None:
        if isinstance(current, nodes.Call) and call_name(current) in ALLOWED_LITERAL_CALLS:
            return True
        current = current.parent
    return False


def is_policy_literal_context(node: nodes.Const) -> bool:
    if isinstance(node.value, int | float) and not literal_looks_like_named_threshold(node):
        return False
    current = node.parent
    while current is not None and not isinstance(
        current,
        (nodes.ClassDef, nodes.FunctionDef, nodes.AsyncFunctionDef, nodes.Module),
    ):
        if isinstance(current, (nodes.Compare, nodes.If, nodes.Return, nodes.Call)):
            return True
        if isinstance(current, nodes.Assign):
            return any(isinstance(target, (nodes.AssignAttr, nodes.Subscript)) for target in current.targets)
        current = current.parent
    return False


def literal_looks_like_named_threshold(node: nodes.Const) -> bool:
    current = node.parent
    while current is not None and not isinstance(
        current,
        (nodes.ClassDef, nodes.FunctionDef, nodes.AsyncFunctionDef, nodes.Module),
    ):
        if isinstance(current, nodes.Compare):
            return True
        current = current.parent
    return False


def attribute_depth(node: nodes.Attribute) -> int:
    depth = 0
    current: nodes.NodeNG = node
    while isinstance(current, nodes.Attribute):
        depth += 1
        current = current.expr
    return depth
