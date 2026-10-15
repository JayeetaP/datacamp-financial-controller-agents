# ADR 003: Use a local synthetic MCP server

Status: accepted.

The demo uses a project-scoped, read-only MCP server over stdio. It exposes synthetic knowledge,
current evidence, deterministic calculations, and process-owner lookup. This preserves visible tool
use without requiring a live enterprise connection.
