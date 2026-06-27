# Clean-Code MCP Agent Plan

## Goal

Make this repository useful to coding agents that want interactive clean-code
guidance without turning the MCP into a noisy style oracle.

## Execution Steps

1. Create an agent skill for using the clean-code MCP correctly.
   - Add and review a `clean-code-mcp-reviewer` skill.
   - Teach agents to read code first, form concrete smell hypotheses, query
     narrowly, and only use high-fit matches anchored to local code evidence.
   - Include cases where the skill should not trigger or should not apply MCP
     guidance.

2. Add skill eval scaffolding.
   - Add realistic eval prompts for code review, refactoring, lint-rule design,
     and near-miss cases.
   - Include small code snippets or local context in the eval prompts so the
     skill can be evaluated against its central "read code first" behavior.
   - Define expected behavior around narrow queries, weak-match suppression, and
     lintable versus review-only guidance.

3. Add retrieval evals and baseline cases.
   - Add positive and near-miss cases for expected pattern IDs.
   - Track top-1 accuracy, top-5 recall, duplicate rate, markdown pollution, and
     `no_strong_match` calibration.
   - Use the baseline results to tune weak-match thresholds rather than relying
     on arbitrary distance values.

4. Implement pattern-first MCP search.
   - Add `search_clean_code_patterns`.
   - Prefer canonical `clean_code_pattern` records by default.
   - Support filters for language, rule family, topic, lintability, source kind,
     and result limit.
   - Return structured metadata, normalized confidence, match reasons, and
     deduplicated pattern records.
   - Use two-pass retrieval: overfetch semantic matches from Weaviate, add local
     exact metadata/alias candidates, filter by source kind and metadata, rerank,
     and group by `record_id`.
   - Keep the existing `search_clean_code` tool as the low-level compatibility
     search surface until callers and docs explicitly migrate.

5. Add full pattern lookup.
   - Add `get_clean_code_pattern`.
   - Keep search responses compact and fetch full pattern detail only after a
     relevant pattern is selected.
   - Use `clean-code-patterns.jsonl` as the source of truth.
   - Validate `CC-###` IDs and return a clear not-found error.
   - Expose this as both a tool and a resource once the tool is stable.

6. Improve retrieval.
   - Combine semantic search, exact keyword/alias matching, metadata filters,
     transparent reranking boosts, and `record_id` deduplication.
   - Return `no_strong_match` when the top results are weak.
   - Calibrate `no_strong_match` with the retrieval evals from step 3.

7. Add lint-rule recommendation support.
   - Add `recommend_clean_code_lint_rules`.
   - Filter toward high- and medium-lintability patterns.
   - Return likely static signals, false-positive risks, suppressions, and
     target tool guidance.

8. Add facet discovery.
   - Add `list_clean_code_facets`.
   - Expose topics, rule families, lintability values, source kinds, languages,
     and counts.

9. Update docs.
   - Document agent workflows, tool contracts, query examples, confidence
     policy, lint-rule promotion, and local verification commands.

10. Verify and review.
    - After every implementation step, run a subagent review loop for the work
      completed in that step and fix substantiated blocking issues.
    - At the end, reread this plan, verify all steps, and run a final subagent
      review loop over the whole implementation.
