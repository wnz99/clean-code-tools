from __future__ import annotations

from clean_code_review_models import TriggerRule

PYLINT_TRIGGERS = {
    "cyclic-import": TriggerRule(
        questions=(
            "Is the cycle exposing a module boundary problem?",
            "Can dependencies be inverted or shared types/constants moved lower?",
        ),
        mcp_query="python cyclic import module boundary dependency inversion",
    ),
    "duplicate-code": TriggerRule(
        questions=(
            "Is this real domain duplication or a benign framework shape?",
            "Can a shared helper remove policy drift without obscuring the caller?",
        ),
        mcp_query="python duplicate code shared helper policy drift",
    ),
    "too-few-public-methods": TriggerRule(
        questions=(
            "Is this class just a passive data container or unnecessary wrapper?",
            "Would a dataclass, TypedDict, or plain function fit the local style better?",
        ),
        mcp_query="python too few public methods unnecessary class dataclass function",
    ),
    "too-many-ancestors": TriggerRule(
        questions=(
            "Is inheritance making behavior harder to trace?",
            "Would composition or a flatter design reduce coupling?",
        ),
        mcp_query="python too many ancestors inheritance composition coupling",
    ),
    "too-many-arguments": TriggerRule(
        questions=(
            "Do these arguments form a stable concept?",
            "Would a dataclass, TypedDict, or keyword-only boundary clarify the call site?",
        ),
        mcp_query="python too many arguments dataclass typed dict call site clarity",
    ),
    "too-many-boolean-expressions": TriggerRule(
        questions=(
            "Is this condition encoding several decisions at once?",
            "Would named predicates or explicit decision steps make the policy clearer?",
        ),
        mcp_query="python too many boolean expressions named predicates policy clarity",
    ),
    "too-many-branches": TriggerRule(
        questions=(
            "Is branching mixing policy decisions with execution?",
            "Can guard clauses, named predicates, or extracted decisions simplify the flow?",
        ),
        mcp_query="python too many branches guard clauses named predicates",
    ),
    "too-many-instance-attributes": TriggerRule(
        questions=(
            "Is this object accumulating multiple responsibilities or state groups?",
            "Can cohesive state move into smaller value objects or collaborators?",
        ),
        mcp_query="python too many instance attributes class responsibility state groups",
    ),
    "too-many-lines": TriggerRule(
        questions=(
            "Does this module have more than one reason to change?",
            "Are there cohesive extraction boundaries that preserve imports and public APIs?",
        ),
        mcp_query="python large module single responsibility extraction boundaries",
    ),
    "too-many-locals": TriggerRule(
        questions=(
            "Is the function carrying too much intermediate state?",
            "Can parsing, calculation, and side effects be separated?",
        ),
        mcp_query="python too many locals split parsing calculation side effects",
    ),
    "too-many-nested-blocks": TriggerRule(
        questions=(
            "Is nesting hiding the main path through the function?",
            "Can early returns or named predicates flatten the code?",
        ),
        mcp_query="python nested blocks guard clauses main path readability",
    ),
    "too-many-public-methods": TriggerRule(
        questions=(
            "Does this class represent more than one responsibility?",
            "Can cohesive behavior move into smaller collaborators or plain functions?",
        ),
        mcp_query="python class too many public methods single responsibility",
    ),
    "too-many-return-statements": TriggerRule(
        questions=(
            "Are return paths representing distinct outcomes that should be named?",
            "Can guard clauses or result objects make the contract clearer?",
        ),
        mcp_query="python too many return statements guard clauses result contract",
    ),
    "too-many-statements": TriggerRule(
        questions=(
            "Does this function combine validation, transformation, and side effects?",
            "Can smaller named steps preserve behavior while improving scanability?",
        ),
        mcp_query="python too many statements split validation transformation side effects",
    ),
}


RUFF_TRIGGERS = {
    "ARG001": TriggerRule(
        questions=(
            "Is this unused argument required by a framework or callback contract?",
            "If not, can the function boundary be narrowed?",
        ),
        mcp_query="python unused function argument narrow function boundary",
    ),
    "ARG002": TriggerRule(
        questions=(
            "Is this unused method argument required by inheritance or framework convention?",
            "If not, can the method contract be simplified?",
        ),
        mcp_query="python unused method argument simplify contract",
    ),
    "ERA001": TriggerRule(
        questions=(
            "Is this commented code obsolete implementation detail?",
            "Can it be removed in favor of version control history or a tracked task?",
        ),
        mcp_query="python commented out code remove obsolete implementation",
    ),
    "F401": TriggerRule(
        questions=(
            "Is this unused import dead code or a leftover dependency?",
            "Can removing it clarify the module boundary?",
        ),
        mcp_query="python unused import dead code module boundary",
    ),
    "F841": TriggerRule(
        questions=(
            "Is this unused variable dead code or an incomplete refactor?",
            "Can the unused state or surrounding responsibility be removed?",
        ),
        mcp_query="python unused variable dead code incomplete refactor",
    ),
    "PLR0911": TriggerRule(
        questions=(
            "Are return paths representing distinct outcomes that should be named?",
            "Can guard clauses or result objects make the contract clearer?",
        ),
        mcp_query="python too many return statements guard clauses result contract",
    ),
    "PLR0912": TriggerRule(
        questions=(
            "Is branching mixing policy decisions with execution?",
            "Can guard clauses, named predicates, or extracted decisions simplify the flow?",
        ),
        mcp_query="python too many branches guard clauses named predicates",
    ),
    "PLR0913": TriggerRule(
        questions=(
            "Do these arguments form a stable concept?",
            "Would a dataclass, TypedDict, or keyword-only boundary clarify the call site?",
        ),
        mcp_query="python too many arguments dataclass typed dict call site clarity",
    ),
    "PLR0914": TriggerRule(
        questions=(
            "Is the function carrying too much intermediate state?",
            "Can parsing, calculation, and side effects be separated?",
        ),
        mcp_query="python too many locals split parsing calculation side effects",
    ),
    "PLR0915": TriggerRule(
        questions=(
            "Does this function combine validation, transformation, and side effects?",
            "Can smaller named steps preserve behavior while improving scanability?",
        ),
        mcp_query="python too many statements split validation transformation side effects",
    ),
    "PLR0916": TriggerRule(
        questions=(
            "Is this condition encoding several decisions at once?",
            "Would named predicates or explicit decision steps make the policy clearer?",
        ),
        mcp_query="python too many boolean expressions named predicates policy clarity",
    ),
    "PLR1702": TriggerRule(
        questions=(
            "Is nesting hiding the main path through the function?",
            "Can early returns or named predicates flatten the code?",
        ),
        mcp_query="python nested blocks guard clauses main path readability",
    ),
    "PLR2004": TriggerRule(
        questions=(
            "Does this value encode business policy or a domain threshold?",
            "Would a named constant make the rule searchable and easier to change?",
        ),
        mcp_query="python magic value comparison named constant business policy",
    ),
    "RET505": TriggerRule(
        questions=(
            "Is the else branch unnecessary after a return?",
            "Would flattening the control flow make the main path clearer?",
        ),
        mcp_query="python unnecessary else after return flatten control flow",
    ),
    "RET506": TriggerRule(
        questions=(
            "Is the else branch unnecessary after an exception?",
            "Would flattening the control flow make failure handling clearer?",
        ),
        mcp_query="python unnecessary else after raise flatten error handling",
    ),
    "RET507": TriggerRule(
        questions=(
            "Is the else branch unnecessary after continue?",
            "Would flattening the loop body improve scanability?",
        ),
        mcp_query="python unnecessary else after continue flatten loop",
    ),
    "RET508": TriggerRule(
        questions=(
            "Is the else branch unnecessary after break?",
            "Would flattening the loop body improve scanability?",
        ),
        mcp_query="python unnecessary else after break flatten loop",
    ),
    "SIM102": TriggerRule(
        questions=(
            "Is nested branching hiding a single combined condition?",
            "Would a named predicate or combined guard clarify the decision?",
        ),
        mcp_query="python nested if combined condition named predicate",
    ),
    "SIM103": TriggerRule(
        questions=(
            "Is a boolean branch returning literal booleans instead of the condition?",
            "Would returning a named predicate make intent clearer?",
        ),
        mcp_query="python needless boolean return named predicate",
    ),
    "SIM108": TriggerRule(
        questions=(
            "Is assignment spread across branches obscuring one decision?",
            "Would a named expression or helper make the choice clearer?",
        ),
        mcp_query="python if else assignment decision helper readability",
    ),
    "TD002": TriggerRule(
        questions=(
            "Is this TODO owned by a person or team?",
            "Should the debt be tracked or removed?",
        ),
        mcp_query="python todo owner tracked technical debt",
    ),
    "TD003": TriggerRule(
        questions=(
            "Is this TODO tied to a tracked issue?",
            "Should the comment become an actionable task or be removed?",
        ),
        mcp_query="python todo issue link actionable technical debt",
    ),
}
