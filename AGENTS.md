# Repository Instructions

- Use Pydantic models for Python validation boundaries. Do not add new ad hoc
  dict-shape validation for JSON, API/tool payloads, config files, corpus
  records, or persisted records when a Pydantic model can express the contract.
- Every MCP tool that writes to the host filesystem, Weaviate, or another
  external state must validate its full input payload with a Pydantic request
  model before performing the write.
- New Python code must have tests with at least 90% coverage for the touched
  module or package. Keep coverage checks in CI-facing commands so the threshold
  is enforced, not just documented.
