# Technical specification

Python owns data validation, calculations, governance, storage, and reporting. The live investigator
uses `codex exec` with saved ChatGPT authentication, a read-only sandbox, local MCP tools, JSONL
events, and a JSON output schema. Replay mode supplies frozen output through the same provider
interface.

Current evidence, historical knowledge, calculations, and policy are separate trust domains. The
agent receives an exception, one finance playbook, and scoped tools—not the whole repository.

See the root build plan for the complete architecture and phased delivery contract.
