from __future__ import annotations

from clean_code_review_models import TriggerRule

ESLINT_TRIGGERS = {
    "@typescript-eslint/naming-convention": TriggerRule(
        questions=(
            "Is the name hiding domain meaning or using inconsistent terminology?",
            "Would renaming improve call-site readability without changing behavior?",
        ),
        mcp_query="typescript naming consistency intention revealing names",
    ),
    "@typescript-eslint/consistent-type-imports": TriggerRule(
        questions=(
            "Are runtime imports being used only for types?",
            "Would type-only imports clarify the module's runtime dependency boundary?",
        ),
        mcp_query="typescript type only imports runtime dependency boundary",
    ),
    "@typescript-eslint/no-confusing-void-expression": TriggerRule(
        questions=(
            "Is this expression mixing side effects with value flow?",
            "Would separating the side effect from the return value clarify intent?",
        ),
        mcp_query="typescript confusing void expression separate side effects values",
    ),
    "@typescript-eslint/no-magic-numbers": TriggerRule(
        questions=(
            "Does this number encode business policy or a domain threshold?",
            "Would a named constant make the rule searchable and easier to change?",
        ),
        mcp_query="typescript magic number named constant business policy",
    ),
    "@typescript-eslint/no-unnecessary-condition": TriggerRule(
        questions=(
            "Is this branch dead or protecting against an impossible state?",
            "Would removing it clarify the real contract?",
        ),
        mcp_query="typescript unnecessary condition dead branch explicit contract",
    ),
    "@typescript-eslint/no-unnecessary-type-assertion": TriggerRule(
        questions=(
            "Is the assertion hiding a type contract that is already known?",
            "Would removing it make the trusted shape clearer?",
        ),
        mcp_query="typescript unnecessary type assertion trusted shape contract",
    ),
    "@typescript-eslint/no-unused-vars": TriggerRule(
        questions=(
            "Is this dead code or a half-removed responsibility?",
            "Can it be deleted safely without changing behavior?",
        ),
        mcp_query="typescript unused variable dead code remove safely",
    ),
    "@typescript-eslint/prefer-nullish-coalescing": TriggerRule(
        questions=(
            "Is falsy handling being confused with absence handling?",
            "Would explicit nullish logic make the data contract clearer?",
        ),
        mcp_query="typescript nullish coalescing absence contract",
    ),
    "@typescript-eslint/strict-boolean-expressions": TriggerRule(
        questions=(
            "Is truthiness hiding the distinction between absence, empty values, and false?",
            "Would an explicit predicate or comparison make the condition safer to read?",
        ),
        mcp_query="typescript strict boolean expressions explicit predicate truthiness",
    ),
    "@typescript-eslint/switch-exhaustiveness-check": TriggerRule(
        questions=(
            "Is variant handling incomplete or scattered?",
            "Would an exhaustive branch make the domain states explicit?",
        ),
        mcp_query="typescript exhaustive switch discriminated union explicit states",
    ),
    "clean-code/no-boolean-flag-arguments": TriggerRule(
        questions=(
            "Does the boolean select behavior rather than represent plain data?",
            "Would intention-revealing functions make call sites clearer?",
        ),
        mcp_query="typescript boolean flag argument intention revealing functions",
    ),
    "clean-code/no-business-policy-literals": TriggerRule(
        questions=(
            "Does this literal encode business policy or domain state?",
            "Would a named constant or typed domain value make changes safer?",
        ),
        mcp_query="typescript business policy literal named constant domain state",
    ),
    "clean-code/no-commented-out-code": TriggerRule(
        questions=(
            "Is this commented code obsolete implementation detail?",
            "Can it be removed in favor of version control history or a tracked task?",
        ),
        mcp_query="typescript commented out code remove obsolete implementation",
    ),
    "clean-code/no-noisy-comments": TriggerRule(
        questions=(
            "Is the comment adding constraint/context or just visual noise?",
            "Would deleting or replacing it with a precise explanation improve scanability?",
        ),
        mcp_query="typescript noisy comments remove visual separators byline comments",
    ),
    "clean-code/no-output-argument-mutation": TriggerRule(
        questions=(
            "Is mutation hidden behind an output parameter?",
            "Would returning a value make the contract clearer?",
        ),
        mcp_query="typescript output argument mutation return value contract",
    ),
    "clean-code/no-redundant-comment": TriggerRule(
        questions=(
            "Does the comment repeat the next line instead of explaining why?",
            "Can clearer naming or deletion remove the need for the comment?",
        ),
        mcp_query="typescript redundant comment intention revealing code",
    ),
    "clean-code/no-train-wrecks": TriggerRule(
        questions=(
            "Is this chain exposing too much object structure to the caller?",
            "Would a named query/helper or domain method reduce coupling?",
        ),
        mcp_query="typescript train wreck law of demeter object navigation",
    ),
    "clean-code/todo-format": TriggerRule(
        questions=(
            "Is this TODO actionable and traceable?",
            "Should the comment include a tracked issue or be converted into code/tests?",
        ),
        mcp_query="typescript todo comment issue id actionable technical debt",
    ),
    "complexity": TriggerRule(
        questions=(
            "Is this function mixing validation, transformation, branching, and side effects?",
            "Can guard clauses or cohesive helper extraction reduce branching?",
        ),
        mcp_query="typescript high complexity function mixed responsibilities guard clauses",
    ),
    "max-depth": TriggerRule(
        questions=(
            "Is rightward drift hiding the normal path?",
            "Can early returns, named predicates, or smaller functions flatten the flow?",
        ),
        mcp_query="typescript deeply nested conditionals guard clauses readability",
    ),
    "max-lines": TriggerRule(
        questions=(
            "Does this file contain multiple reasons to change?",
            "Are there cohesive module boundaries that preserve the public API?",
        ),
        mcp_query="typescript large file single responsibility extraction boundaries",
    ),
    "max-lines-per-function": TriggerRule(
        questions=(
            "Does this function do more than one job?",
            "Can stable parsing, validation, transformation, or side-effect steps be separated?",
        ),
        mcp_query="typescript long function split validation transformation side effects",
    ),
    "max-params": TriggerRule(
        questions=(
            "Do these parameters travel together as a named concept?",
            "Would a typed object parameter improve call-site clarity?",
        ),
        mcp_query="typescript long parameter list object parameter call site clarity",
    ),
    "no-empty": TriggerRule(
        questions=(
            "Is this empty block hiding ignored behavior or an incomplete branch?",
            "Should the code handle, document, or remove the branch explicitly?",
        ),
        mcp_query="typescript empty block ignored behavior explicit handling",
    ),
    "no-negated-condition": TriggerRule(
        questions=(
            "Is the negative branch making the normal path harder to follow?",
            "Would a positive predicate or guard clause clarify the condition?",
        ),
        mcp_query="typescript negated condition positive predicate guard clause",
    ),
    "no-nested-ternary": TriggerRule(
        questions=(
            "Is dense expression logic hiding a decision table or branching policy?",
            "Would named intermediate values or ordinary branches improve readability?",
        ),
        mcp_query="typescript nested ternary decision logic readability",
    ),
    "no-restricted-syntax": TriggerRule(
        questions=(
            "Is this import list signaling an overly broad module boundary?",
            "Would a narrower module, namespace import, or split dependency improve scanability?",
        ),
        mcp_query="typescript long import list module boundary readability",
    ),
    "no-useless-return": TriggerRule(
        questions=(
            "Is redundant control flow adding noise to the function ending?",
            "Can the return path be simplified without changing behavior?",
        ),
        mcp_query="typescript useless return redundant control flow",
    ),
    "sonarjs/cognitive-complexity": TriggerRule(
        questions=(
            "Which branches force a reader to retain too much context?",
            "Can conditions be named or decision logic isolated?",
        ),
        mcp_query="typescript cognitive complexity named predicates decision logic",
    ),
    "sonarjs/no-dead-store": TriggerRule(
        questions=(
            "Is this assignment dead code or evidence of an incomplete refactor?",
            "Can the unused state or surrounding responsibility be removed?",
        ),
        mcp_query="typescript dead store incomplete refactor unused state",
    ),
    "sonarjs/no-duplicate-string": TriggerRule(
        questions=(
            "Is this repeated string a domain value, message, or policy token?",
            "Would naming it avoid drift between copies?",
        ),
        mcp_query="typescript duplicate string named constant policy drift",
    ),
    "sonarjs/no-duplicated-branches": TriggerRule(
        questions=(
            "Is duplicated branching hiding a missing abstraction or a bug?",
            "Can the condition or branch body be simplified safely?",
        ),
        mcp_query="typescript duplicated branches conditional simplification",
    ),
    "sonarjs/no-identical-conditions": TriggerRule(
        questions=(
            "Is repeated conditional logic hiding a copy/paste mistake or missing predicate?",
            "Can the branching model be simplified safely?",
        ),
        mcp_query="typescript identical conditions duplicated predicate branch bug",
    ),
    "sonarjs/no-identical-functions": TriggerRule(
        questions=(
            "Is this real duplication or a coincidental framework shape?",
            "Can a shared helper remove policy drift without hiding intent?",
        ),
        mcp_query="typescript duplicated functions shared helper policy drift",
    ),
    "sonarjs/no-inverted-boolean-check": TriggerRule(
        questions=(
            "Is inverted boolean logic making the condition harder to read?",
            "Would a positive predicate or renamed boolean clarify intent?",
        ),
        mcp_query="typescript inverted boolean check positive predicate naming",
    ),
    "unicorn/explicit-length-check": TriggerRule(
        questions=(
            "Is collection emptiness being expressed indirectly?",
            "Would an explicit length comparison clarify the condition?",
        ),
        mcp_query="typescript explicit length check collection emptiness",
    ),
    "unicorn/no-negated-condition": TriggerRule(
        questions=(
            "Is the negative branch making the normal path harder to follow?",
            "Would a positive predicate or guard clause clarify the condition?",
        ),
        mcp_query="typescript negated condition positive predicate guard clause",
    ),
    "unicorn/no-null": TriggerRule(
        questions=(
            "Is null being used as an ambiguous absence value?",
            "Does the surrounding code prefer undefined, option-like objects, or explicit states?",
        ),
        mcp_query="typescript null absence value explicit state contract",
    ),
}
