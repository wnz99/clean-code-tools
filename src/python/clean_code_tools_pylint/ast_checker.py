from __future__ import annotations

from typing import ClassVar

from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter

from .helpers import (
    MAX_ATTRIBUTE_CHAIN_DEPTH,
    MUTATOR_METHODS,
    annotation_is_bool,
    attribute_depth,
    is_allowed_literal_context,
    is_policy_literal_context,
    literal_looks_like_policy,
    name_looks_like_selector,
    root_name,
)


class CleanCodeAstChecker(BaseChecker):
    name = "clean-code-ast"
    msgs: ClassVar = {
        "C9003": (
            "Boolean selector argument changes behavior by mode; prefer named operations or an explicit options object.",
            "clean-code-boolean-flag-argument",
            "Discourage boolean selector arguments and boolean mode parameters.",
        ),
        "C9004": (
            "Avoid mutating parameter '%s' as an output argument; return a value or create a local copy instead.",
            "clean-code-output-argument-mutation",
            "Flag parameter mutation that treats arguments as output containers.",
        ),
        "C9007": (
            "Policy literal '%s' should usually be a named constant so the rule is searchable.",
            "clean-code-business-policy-literal",
            "Flag hard-coded policy literals in branch, return, and call expressions.",
        ),
        "C9008": (
            "Deep attribute chain exposes object internals; prefer a named query on the owning object.",
            "clean-code-train-wreck",
            "Flag deep attribute chains that expose transitive object structure.",
        ),
    }

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)
        self._function_params: list[set[str]] = []
        self._function_locals: list[set[str]] = []

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        params = {argument.name for argument in node.args.args + node.args.kwonlyargs}
        self._function_params.append(params)
        self._function_locals.append(set())
        self.check_boolean_params(node)

    visit_asyncfunctiondef = visit_functiondef

    def leave_functiondef(self, _node: nodes.FunctionDef) -> None:
        self._function_params.pop()
        self._function_locals.pop()

    leave_asyncfunctiondef = leave_functiondef

    def visit_assignname(self, node: nodes.AssignName) -> None:
        if isinstance(node.parent, nodes.Arguments):
            return
        if self._function_locals:
            self._function_locals[-1].add(node.name)

    def visit_call(self, node: nodes.Call) -> None:
        for argument in node.args:
            if isinstance(argument, nodes.Const) and isinstance(argument.value, bool):
                self.add_message("clean-code-boolean-flag-argument", node=argument)
        if isinstance(node.func, nodes.Attribute) and node.func.attrname in MUTATOR_METHODS:
            self.report_if_param_mutation(node.func.expr, node.func.expr)

    def visit_assignattr(self, node: nodes.AssignAttr) -> None:
        self.report_if_param_mutation(node, node)

    def visit_assign(self, node: nodes.Assign) -> None:
        for target in node.targets:
            self.report_if_param_mutation(target, target)

    def visit_augassign(self, node: nodes.AugAssign) -> None:
        self.report_if_param_mutation(node.target, node.target)

    def visit_const(self, node: nodes.Const) -> None:
        if (
            literal_looks_like_policy(node.value)
            and is_policy_literal_context(node)
            and not is_allowed_literal_context(node)
        ):
            self.add_message("clean-code-business-policy-literal", node=node, args=(str(node.value),))

    def visit_attribute(self, node: nodes.Attribute) -> None:
        if isinstance(node.parent, nodes.Attribute):
            return
        if attribute_depth(node) > MAX_ATTRIBUTE_CHAIN_DEPTH:
            self.add_message("clean-code-train-wreck", node=node)

    def check_boolean_params(self, node: nodes.FunctionDef) -> None:
        arguments = node.args.args + node.args.kwonlyargs
        annotations = node.args.annotations + node.args.kwonlyargs_annotations
        for argument, annotation in zip(arguments, annotations, strict=False):
            if argument.name in {"self", "cls"}:
                continue
            if annotation_is_bool(annotation) and name_looks_like_selector(argument.name):
                self.add_message("clean-code-boolean-flag-argument", node=argument)

    def report_if_param_mutation(self, node: nodes.NodeNG, expression: nodes.NodeNG) -> None:
        name = root_name(expression)
        if not name or name in {"self", "cls"}:
            return
        scopes = zip(reversed(self._function_params), reversed(self._function_locals), strict=False)
        for params, locals_ in scopes:
            if name in locals_:
                return
            if name in params:
                self.add_message("clean-code-output-argument-mutation", node=node, args=(name,))
                return
