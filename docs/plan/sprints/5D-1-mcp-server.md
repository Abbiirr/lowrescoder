# Sprint 5D-1: MCP Server

> Status: **NOT STARTED**
> Sprint: 5D (External Integration)
> Est. Hours: ~8h (3h tests + 5h impl)
> Dependencies: MVP Gate (5C complete)
> Owner: Claude

---

## Goal

Read-only MCP server exposing 6 tools: search_code, find_definition, find_references, list_symbols, read_file, get_diagnostics.

---

## TDD Tests (Write First)

- [ ] `test_mcp_6_tools` - MCP server exposes exactly 6 tools
- [ ] `test_mcp_validation` - input validation enforces path allowlist
- [ ] `test_mcp_audit` - every tool call is logged
- [ ] `test_mcp_tool_poisoning_defense` - tool results sanitized against prompt injection

## Implementation

- [ ] Implement MCP server using mcp-sdk v1.x
- [ ] Transport: stdio-first for local (Section 15.18 R4)
- [ ] Expose 6 read-only tools
- [ ] Path allowlist: only project root (R4)
- [ ] Audit logging: every call logged (R4)
- [ ] Input sanitization: defense against tool poisoning (R4)
- [ ] Explicit remote opt-in for network transport (R4)

## Acceptance Criteria

- [ ] MCP server exposes 6 read-only tools
- [ ] stdio transport works for local integration
- [ ] Path allowlist enforced
- [ ] Audit logging active
- [ ] Tool poisoning defense active
- [ ] MCP SDK pinned to v1.x
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_mcp_server.py`
- Integration test: `tests/integration/test_mcp_claude_code.py`
- QA artifact: `docs/qa/test-results/sprint-5d-1-mcp-server.md`
