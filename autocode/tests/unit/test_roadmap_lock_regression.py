"""Regression guards for Phase 5 roadmap lock artifacts.

Ensures key documentation and configuration remain consistent.
These tests prevent accidental drift in locked roadmap artifacts.
"""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Find the repo root (contains CLAUDE.md) or fall back to parents[2]."""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "CLAUDE.md").exists():
            return parent
    return p.parents[2]


# --- Phase 5 Plan ---


def test_phase5_plan_exists() -> None:
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    assert path.exists(), "Phase 5 plan must exist."


def test_phase5_plan_is_locked() -> None:
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "LOCKED" in content, "Phase 5 plan must contain LOCKED status."


def test_phase5_plan_has_standalone_first_strategy() -> None:
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Standalone first" in content, "Phase 5 must have standalone-first strategy."


def test_phase5_plan_has_sprints() -> None:
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Sprint 5A" in content, "Phase 5 plan must include Sprint 5A."
    assert "Sprint 5B" in content or "5B" in content, "Phase 5 plan must include Sprint 5B."


def test_phase5_plan_has_milestone_gates() -> None:
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert ">= 75%" in content or "75%" in content, "Phase 5 must have M1 pass rate gate."
    assert "p95" in content, "Phase 5 must have latency gate."


# --- CLAUDE.md ---


def test_claude_md_exists() -> None:
    path = _repo_root() / "CLAUDE.md"
    assert path.exists(), "CLAUDE.md must exist."


# CLAUDE.md was restructured on 2026-04-18 to be very lean and near-identical
# to AGENTS.md; detailed tech-stack / phase / Jedi locks moved to their
# canonical homes below. These tests follow that move so they stay
# meaningful as roadmap locks.


def test_phase5_plan_authoritative() -> None:
    """Phase 5 status and scope must live in its authoritative plan file."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    assert path.exists(), "Phase 5 plan must exist."
    content = path.read_text(encoding="utf-8")
    assert "Phase 5" in content, "Phase 5 plan must reference Phase 5."


def test_jedi_locked_in_phase5_plan() -> None:
    """Jedi as Python semantics choice is a locked tech decision."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Jedi" in content, (
        "Phase 5 plan must keep Jedi as Python semantics choice."
    )


def test_claude_md_no_outlines_as_active() -> None:
    path = _repo_root() / "CLAUDE.md"
    content = path.read_text(encoding="utf-8")
    # Outlines should not appear as the current L3 runtime choice
    assert "llama-cpp-python + Outlines" not in content, (
        "CLAUDE.md should not list Outlines as active L3 runtime (replaced by native grammar)."
    )


# --- docs/requirements_and_features.md ---


def test_requirements_exists() -> None:
    path = _repo_root() / "docs/requirements_and_features.md"
    assert path.exists(), "Requirements doc must exist."


def test_requirements_has_sprint_5a0() -> None:
    path = _repo_root() / "docs/requirements_and_features.md"
    content = path.read_text(encoding="utf-8")
    assert "5A0" in content, "Requirements must include Sprint 5A0."


def test_requirements_no_a2a_sprint() -> None:
    path = _repo_root() / "docs/requirements_and_features.md"
    content = path.read_text(encoding="utf-8")
    # A2A should be noted as dropped, not listed as active sprint
    assert "dropped" in content.lower() or "Sprint 5E" not in content.split("PLANNED")[0], (
        "Requirements should reflect A2A (5E) being dropped."
    )


def test_requirements_references_phase5_plan() -> None:
    path = _repo_root() / "docs/requirements_and_features.md"
    content = path.read_text(encoding="utf-8")
    assert "phase5-agent-teams.md" in content, (
        "Requirements must reference the authoritative Phase 5 plan."
    )


# --- PLAN.md (absorbed docs/plan.md content 2026-04-18) ---
#
# ``docs/plan.md`` was absorbed into ``PLAN.md`` §6 "MVP Acceptance &
# Targets" and removed. The MVP acceptance checklist moved to
# ``PLAN.md §6.2``; the sandbox / observability / success-metrics
# subsections moved to ``PLAN.md §6.1 / §6.3 / §6.4``. The legacy
# per-phase "Phase 4 COMPLETE" style assertions no longer apply —
# phase history now lives in ``current_directives.md`` and
# ``EXECUTION_CHECKLIST.md``.


def test_plan_md_absorbed_into_root_plan() -> None:
    """The absorbed content must now live in PLAN.md §6."""
    path = _repo_root() / "PLAN.md"
    content = path.read_text(encoding="utf-8")
    assert "MVP Acceptance" in content, (
        "PLAN.md must carry the MVP Acceptance section absorbed from docs/plan.md."
    )
    assert "§6.2" in content or "MVP Acceptance Checklist" in content, (
        "PLAN.md must expose an MVP Acceptance Checklist subsection."
    )


# --- Lock checklist ---


def test_lock_checklist_references_qa_pack() -> None:
    path = _repo_root() / "docs/plan/phase5-roadmap-lock-checklist.md"
    content = path.read_text(encoding="utf-8")
    assert "QA" in content, "Lock checklist must reference QA lock pack."
    assert "pytest" in content, "Lock checklist must mention pytest."


def test_lock_checklist_references_doc_pack() -> None:
    path = _repo_root() / "docs/plan/phase5-roadmap-lock-checklist.md"
    content = path.read_text(encoding="utf-8")
    assert "Documentation Lock Pack" in content, (
        "Lock checklist must reference documentation lock pack."
    )


# --- Cross-doc consistency ---


def test_phase5_sprint_order_consistent() -> None:
    """Verify sprint order is consistent across docs."""
    req_path = _repo_root() / "docs/requirements_and_features.md"
    req_content = req_path.read_text(encoding="utf-8")

    # Both docs should mention the same sprint order
    for sprint in ["5A0", "5A", "5B", "5C", "5D"]:
        assert sprint in req_content, (
            f"requirements_and_features.md missing sprint {sprint}"
        )


def test_benchmark_hardening_docs_marked_historical() -> None:
    """Verify benchmark hardening docs are marked as historical."""
    for phase_num in [1, 2, 3]:
        path = _repo_root() / f"docs/plan/benchmark-hardening-phase{phase_num}.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            assert "HISTORICAL" in content.upper(), (
                f"benchmark-hardening-phase{phase_num}.md must be marked as historical."
            )


# --- Rev 3 additions: B4/B5/Phase 6/Waiver/Precedence ---


def test_phase5_plan_has_doc_precedence_contract() -> None:
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Document Precedence Contract" in content, (
        "Phase 5 plan must have document precedence contract (Rev 3)."
    )
    assert "authority order" in content.lower() or "Priority" in content, (
        "Precedence contract must define authority order."
    )


def test_phase5_plan_has_phase6_entry_criteria() -> None:
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Phase 6 Entry Criteria" in content, (
        "Phase 5 plan must include Phase 6 entry criteria (Rev 3, D1)."
    )
    assert "single-installable" in content.lower() or "Single-installable" in content, (
        "Phase 6 entry criteria must reference single-installable packaging."
    )


def test_phase5_plan_has_waiver_policy() -> None:
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Waiver Policy" in content, (
        "Phase 5 plan must include waiver policy (Rev 3, W1-W3)."
    )
    assert "W1" in content and "W2" in content and "W3" in content, (
        "Waiver policy must define W1, W2, and W3."
    )


def test_phase5_plan_b4_reliability_gate_strengthened() -> None:
    """Rev 3: B4 amendments — 3 consecutive smoke passes, stored soak, fixed workload."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "3 consecutive smoke passes" in content, (
        "B4 reliability gate must require 3 consecutive smoke passes (Rev 3)."
    )
    assert "stored soak artifact" in content.lower() or "1 stored soak artifact" in content, (
        "B4 must require stored soak artifact per milestone (Rev 3)."
    )
    assert "Fixed workload fixture" in content or "fixed workload" in content.lower(), (
        "B4 must require fixed workload fixture (Rev 3)."
    )


def test_phase5_plan_b5_adapter_hardening() -> None:
    """Rev 3: B5 amendments — golden transcripts, version probe, JSON-only."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Golden transcript tests" in content or "golden transcript" in content.lower(), (
        "B5 adapter hardening must include golden transcript tests (Rev 3)."
    )
    assert "fail-closed" in content, (
        "B5 must require fail-closed behavior for unsupported versions (Rev 3)."
    )
    assert "JSON/schema parsing ONLY" in content or "JSON-only" in content.lower(), (
        "B5 must enforce JSON-only parsing, no regex (Rev 3)."
    )


def test_phase5_plan_edit_command_non_deferrable() -> None:
    """Rev 3: Full edit command pinned as P0 non-deferrable in Sprint 5B."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "NON-DEFERRABLE P0" in content, (
        "Full edit command must be marked NON-DEFERRABLE P0 (Rev 3)."
    )


def test_phase5_plan_a2a_watchlist() -> None:
    """Rev 3: A2A reclassified as WATCHLIST, not 'dead'."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "WATCHLIST" in content, (
        "A2A must be classified as WATCHLIST (Rev 3)."
    )


def test_phase5_plan_rev3_marker() -> None:
    """Verify plan is at Rev 3."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Rev 3" in content, "Phase 5 plan must be at Rev 3."


# --- Rev 3 C1: A2A terminology consistency ---


def test_a2a_terminology_consistent_no_dead() -> None:
    """A2A should be WATCHLIST, not 'dead' in any active doc."""
    for doc in [
        "CLAUDE.md",
        "PLAN.md",
        "docs/requirements_and_features.md",
    ]:
        path = _repo_root() / doc
        content = path.read_text(encoding="utf-8")
        assert "effectively dead" not in content.lower(), (
            f"{doc} should not say A2A is 'effectively dead' (use WATCHLIST)."
        )


# --- Rev 4: P1-P8 Execution Policies ---


def test_phase5_plan_rev4_marker() -> None:
    """Verify plan is at Rev 4."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Rev 4" in content, "Phase 5 plan must be at Rev 4."


def test_phase5_plan_has_execution_policies() -> None:
    """Rev 4: Plan must have Execution Policies section with P1-P8."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Execution Policies" in content, (
        "Phase 5 plan must have Execution Policies section (Rev 4, P1-P8)."
    )
    for p in ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]:
        assert p in content, f"Execution Policies must include {p} (Rev 4)."


def test_phase5_plan_p1_waiver_governance() -> None:
    """P1: Waiver governance must be enforceable with cap and auto-reopen."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "52" in content, "P1 must reference mypy baseline cap of 52."
    assert "auto-reopen" in content.lower(), "P1 must have auto-reopen rule."


def test_phase5_plan_p4_deterministic_acceptance() -> None:
    """P4: Each micro-sprint must have deterministic acceptance criteria."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "deterministic" in content.lower() and "acceptance" in content.lower(), (
        "P4 must require deterministic acceptance per micro-sprint."
    )


def test_phase5_plan_p5_risk_controls() -> None:
    """P5: 5B.5 must have fail-fast criteria and user escalation."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "fail-fast" in content.lower(), "P5 must have fail-fast criteria for 5B.5."
    assert "escalation" in content.lower() or "user override" in content.lower(), (
        "P5 must have user escalation trigger."
    )


def test_phase5_plan_p7_slice_independence() -> None:
    """P7: Slice-level independence contract must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "slice" in content.lower() and "independence" in content.lower(), (
        "P7 must define slice-level independence contract."
    )


def test_phase5_plan_p8_reproducible_benchmarks() -> None:
    """P8: Reproducible benchmark/eval policy must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "reproducible" in content.lower(), (
        "P8 must define reproducible benchmark/eval policy."
    )


def test_phase5_plan_claude_archival_file_exists() -> None:
    """Claude archival file must exist."""
    path = (
        _repo_root()
        / "docs/communication/old/2026-02-17-claude-phase5-planning-superseded.md"
    )
    assert path.exists(), "Claude phase5 planning archival file must exist."


def test_phase5_plan_m9_lock_state_schema() -> None:
    """M9: Lock-state table schema must define OPEN/CONDITIONAL_CLOSED/CLOSED."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "CONDITIONAL_CLOSED" in content, (
        "Plan must define CONDITIONAL_CLOSED status in lock-state schema (M9)."
    )
    assert "CHECKLIST_READY" in content, (
        "Plan must define CHECKLIST_READY status in lock-state schema (M9)."
    )


def test_phase5_plan_m10_duplicate_entry_id_rule() -> None:
    """M10: Duplicate entry-ID handling rule must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Duplicate Entry-ID" in content or "duplicate entry" in content.lower(), (
        "Plan must define duplicate entry-ID handling rule (M10)."
    )


# --- D1-D4 from Codex Entry 482 ---


def test_phase5_plan_d1_transition_conditions() -> None:
    """D1: B1/B2 transition conditions must be explicit and testable."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Transition Trigger" in content or "transition" in content.lower(), (
        "Plan must have explicit B1/B2 transition conditions (D1)."
    )


def test_phase5_plan_d3_failfast_hard_gate() -> None:
    """D3: 5B.5 fail-fast must be a hard gate, not advisory."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "hard gate" in content.lower(), (
        "5B.5 fail-fast must be marked as hard gate (D3)."
    )


def test_phase5_plan_d4_g5_evidence_bundle() -> None:
    """D4: G5 must specify exact first evidence bundle."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "G5" in content and "OPEN" in content, (
        "G5 must remain OPEN in plan (D4)."
    )
    assert "task bank" in content.lower() or "task-bank" in content.lower(), (
        "G5 evidence bundle must reference task bank (D4)."
    )


# --- Rev 5: R1-R6 from Codex Entry 484 ---


def test_phase5_plan_rev5_marker() -> None:
    """Verify plan is at Rev 5."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Rev 5" in content, "Phase 5 plan must be at Rev 5."


def test_phase5_plan_r1_integration_contract() -> None:
    """R1: Config/MCP-first integration contract must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Integration Contract" in content, (
        "Plan must have R1 integration contract section."
    )
    assert "no regex" in content.lower() or "json/schema only" in content.lower(), (
        "R1 must prohibit regex/free-text CLI parsing."
    )


def test_phase5_plan_r3_capability_probes() -> None:
    """R3: Adapter capability probes with fail-closed behavior."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "supports_mcp_server" in content, (
        "R3 must define supports_mcp_server probe."
    )
    assert "fail-closed" in content.lower(), (
        "R3 must require fail-closed behavior."
    )


def test_phase5_plan_r4_mcp_security() -> None:
    """R4: MCP security gate — local-only + path allowlist + audit."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "local-only" in content.lower(), "R4 must default to local-only transport."
    assert "path allowlist" in content.lower() or "project-root" in content.lower(), (
        "R4 must require path allowlist."
    )
    assert "audit log" in content.lower(), "R4 must require audit logging."
    assert "tool poisoning" in content.lower() or "prompt injection" in content.lower(), (
        "R4 must address tool poisoning / prompt injection defense."
    )


def test_phase5_plan_r5_eval_additions() -> None:
    """R5: Eval additions — context-budget sweep + negative control + routing-regret."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "context-budget" in content.lower() or "budget sweep" in content.lower(), (
        "R5 must include context-budget sweep."
    )
    assert "negative control" in content.lower() or "wrong-context" in content.lower(), (
        "R5 must include wrong-context negative control."
    )
    assert "routing-regret" in content.lower() or "routing regret" in content.lower(), (
        "R5 must include routing-regret metric."
    )


def test_phase5_plan_r6_d2_archival_correction() -> None:
    """R6: Comms regression guard — D2 archival correction text must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "Archival Count Audit" in content or "archival count" in content.lower(), (
        "D2 archival-correction text must exist in plan (R6 guard)."
    )


def test_phase5_plan_r6_d5_comms_archival_ops() -> None:
    """R6: Comms regression guard — D5 'applies to all comms archival operations' must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "applies to all comms archival operations" in content, (
        "D5 text must exist in plan (R6 guard)."
    )


def test_phase5_plan_b2_no_near_zero_adoption() -> None:
    """B2 fix: Plan must not contain 'near-zero adoption' (P2 violation)."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "near-zero adoption" not in content, (
        "Plan must not use 'near-zero adoption' — violates P2 terminology policy."
    )
    assert "faded from prominence" not in content, (
        "Plan must not use 'faded from prominence' — violates P2 terminology policy."
    )


# --- Q1-Q5 from Codex Entry 487 ---


def test_phase5_plan_q1_editor_bakeoff() -> None:
    """Q1: Editor model bakeoff gate must exist pre-5B."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "bakeoff" in content.lower() or "Bakeoff" in content, (
        "Plan must have editor model bakeoff gate (Q1)."
    )
    assert "promotion rule" in content.lower(), (
        "Q1 must have auto-promotion rule for editor tier."
    )


def test_phase5_plan_q2_latency_split_gates() -> None:
    """Q2: Latency budget must have split gates by task class."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "single-file fast path" in content.lower(), (
        "Q2 must define single-file fast path latency class."
    )
    assert "multi-file iterative" in content.lower(), (
        "Q2 must define multi-file iterative latency class."
    )
    assert "first_token_latency" in content or "end_to_end_latency" in content, (
        "Q2 must record first_token_latency and end_to_end_latency."
    )


def test_phase5_plan_q3_task_bank_prerequisite() -> None:
    """Q3: Task bank must be upfront lock prerequisite, not Sprint 5B deliverable."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "lock prerequisite" in content.lower(), (
        "Q3 must mark task bank as lock prerequisite."
    )
    assert ">= 30" in content or "30 concrete" in content.lower(), (
        "Q3 must require >= 30 task scenarios."
    )


def test_phase5_plan_q4_adaptive_context() -> None:
    """Q4: Adaptive context policy with 4096 min / 8192 target."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "minimum_supported_ctx" in content or "4096" in content, (
        "Q4 must define minimum context floor."
    )
    assert "target_ctx" in content or "8192" in content, (
        "Q4 must define target context window."
    )


def test_phase5_plan_q5_simulation_harness() -> None:
    """Q5: AgentBus 5C simulation harness must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "simulation harness" in content.lower(), (
        "Q5 must specify AgentBus simulation harness for 5C."
    )
    assert "contract tests" in content.lower() and "5d" in content.lower(), (
        "Q5 must reserve external-bridge contract tests for 5D."
    )


# --- R7-R9 from Codex Entry 492 ---


def test_phase5_plan_r7_codex_jsonl_contract() -> None:
    """R7: Codex JSONL event-stream contract tests must be specified."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "event-stream" in content.lower() or "jsonl" in content.lower(), (
        "R7 must specify Codex JSONL event-stream contract."
    )
    assert "unknown-event tolerance" in content.lower() or "unknown event" in content.lower(), (
        "R7 must require unknown-event tolerance."
    )


def test_phase5_plan_r8_output_schema_guard() -> None:
    """R8: --output-schema semantics guard must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "output-schema" in content.lower() or "output_schema" in content.lower(), (
        "R8 must define --output-schema semantics guard."
    )
    assert "final response shape" in content.lower() or "final payload" in content.lower(), (
        "R8 must clarify --output-schema constrains final response only."
    )


def test_phase5_plan_r9_mcp_transport_details() -> None:
    """R9: MCP transport/security compatibility details must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "streamable http" in content.lower(), (
        "R9 must specify Streamable HTTP transport."
    )
    assert "mcp-session-id" in content.lower(), (
        "R9 must document Mcp-Session-Id lifecycle handling."
    )
    assert "localhost" in content.lower() or "127.0.0.1" in content.lower(), (
        "R9 must default to localhost bind."
    )


# --- R10-R12 from Codex Entry 498 ---


def test_phase5_plan_r10_delegation_budget() -> None:
    """R10: Delegation budget controls must be a hard gate."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "delegation budget" in content.lower() or "delegation cap" in content.lower(), (
        "R10 must define delegation budget controls."
    )
    assert "hard gate" in content.lower(), (
        "R10 delegation controls must be hard gates, not advisory."
    )


def test_phase5_plan_r11_capability_matrix() -> None:
    """R11: External capability matrix must be an executable contract."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "capability" in content.lower() and "matrix" in content.lower(), (
        "R11 must define external capability matrix."
    )
    assert "fail closed" in content.lower() or "fail-closed" in content.lower(), (
        "R11 must fail closed on probe mismatch."
    )


def test_phase5_plan_r12_context_handoff_benchmark() -> None:
    """R12: Context handoff benchmark pack must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "too-little context" in content.lower() or "too-little" in content.lower(), (
        "R12 must eval too-little context scenarios."
    )
    assert "too-much context" in content.lower() or "too-much" in content.lower(), (
        "R12 must eval too-much context scenarios."
    )
    assert "wrong-context" in content.lower() or "wrong context" in content.lower(), (
        "R12 must eval wrong-context scenarios."
    )


# --- R13-R18 + P9 from Codex Entry 500/502 ---


def test_phase5_plan_r13_benchmark_pyramid() -> None:
    """R13: Benchmark pyramid gate must exist."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "benchmark pyramid" in content.lower(), (
        "R13 must define benchmark pyramid gate."
    )


def test_phase5_plan_r14_verifiability_contract() -> None:
    """R14: Verifiability contract — no LLM-as-judge."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "deterministic oracle" in content.lower(), (
        "R14 must require deterministic oracles."
    )
    assert "llm-as-judge" in content.lower() or "no llm" in content.lower(), (
        "R14 must prohibit LLM-as-judge for pass/fail."
    )


def test_phase5_plan_r16_cost_latency_quality() -> None:
    """R16: Cost/latency/quality triplet reporting required."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "resolve@1" in content.lower() or "cost per resolved" in content.lower(), (
        "R16 must require cost/quality/latency triplet reporting."
    )


def test_phase5_plan_r17_full_system_build() -> None:
    """R17: Full-system build track with greenfield tasks."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "greenfield" in content.lower(), (
        "R17 must include greenfield full-system build tasks."
    )


def test_phase5_plan_r18_tdd_enforcement() -> None:
    """R18: TDD enforcement mode for bug-fix tasks."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "tdd enforcement" in content.lower() or "failing test" in content.lower(), (
        "R18 must require failing test reproduction before fix."
    )


def test_phase5_plan_p9_subsprint_start_gate() -> None:
    """P9: Sub-sprint start gate with user approval."""
    path = _repo_root() / "docs/plan/phase5-agent-teams.md"
    content = path.read_text(encoding="utf-8")
    assert "sub-sprint start gate" in content.lower() or "start gate" in content.lower(), (
        "P9 must define sub-sprint start gate policy."
    )
    assert "user approval" in content.lower() or "explicit user" in content.lower(), (
        "P9 must require explicit user approval."
    )
