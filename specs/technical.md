# Technical specification

Python owns data validation, calculations, governance, storage, and reporting. The live investigator
uses `codex exec` with saved ChatGPT authentication, a read-only sandbox, local MCP tools, JSONL
events, and a JSON output schema. Replay mode supplies frozen output through the same provider
interface.

Current evidence, historical knowledge, calculations, and policy are separate trust domains. The
agent receives an exception, a bounded investigation procedure, and scoped tools—not the whole
repository. The procedure currently lives in `CodexProvider._prompt`; directly loading a versioned
finance playbook from `domain_skills/` is planned, not implemented.

See the [build plan](../docs/ai-dlc/build-plan.md) for the current implementation and next work,
and the [process design](../docs/process-design.md) for the stage-by-stage flow.
