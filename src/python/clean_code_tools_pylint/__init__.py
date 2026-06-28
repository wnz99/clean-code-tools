from __future__ import annotations

from pylint.lint import PyLinter

from .ast_checker import CleanCodeAstChecker
from .comments import CleanCodeCommentChecker


def register(linter: PyLinter) -> None:
    if getattr(linter, "_clean_code_tools_registered", False):  # pylint: disable=clean-code-boolean-flag-argument
        return
    linter._clean_code_tools_registered = True
    linter.register_checker(CleanCodeCommentChecker(linter))
    linter.register_checker(CleanCodeAstChecker(linter))
