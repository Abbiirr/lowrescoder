"""Tests for the canonical external harness adapter contract."""

from __future__ import annotations

from collections.abc import Iterator

from autocode.external.harness_adapter import (
    ArtifactBundle,
    HarnessAdapter,
    HarnessCapabilities,
    HarnessEvent,
    HarnessEventType,
    HarnessKind,
    HarnessProbe,
    PromptInput,
    ResumeRequest,
    RunHandle,
    SessionHandle,
    SessionSnapshot,
    StartRequest,
)


class _DummyAdapter:
    def probe(self) -> HarnessProbe:
        return HarnessProbe(
            kind=HarnessKind.CODEX,
            binary="codex",
            available=True,
            capabilities=HarnessCapabilities(supports_resume=True),
        )

    def start(self, request: StartRequest) -> SessionHandle:
        return SessionHandle(kind=HarnessKind.CODEX, session_id="s1", cwd=request.cwd)

    def send(self, session: SessionHandle, prompt: PromptInput) -> RunHandle:
        return RunHandle(session=session, run_id="r1", metadata={"prompt": prompt.text})

    def resume(self, request: ResumeRequest) -> SessionHandle:
        return SessionHandle(
            kind=HarnessKind.CODEX,
            session_id=request.session_id,
            cwd=request.cwd or ".",
        )

    def interrupt(self, session: SessionHandle) -> None:
        return None

    def shutdown(self, session: SessionHandle) -> None:
        return None

    def stream_events(self, run: RunHandle) -> Iterator[HarnessEvent]:
        yield HarnessEvent(
            event_type=HarnessEventType.RUN_STARTED,
            session_id=run.session.session_id,
            run_id=run.run_id,
        )

    def capture_artifacts(self, session: SessionHandle) -> ArtifactBundle:
        return ArtifactBundle(changed_files=("a.py",))

    def snapshot_state(self, session: SessionHandle) -> SessionSnapshot:
        return SessionSnapshot(
            session_id=session.session_id,
            cwd=session.cwd,
            status="running",
            last_run_id="r1",
        )


def test_harness_adapter_protocol_runtime_check() -> None:
    """Concrete adapters should satisfy the runtime-checkable protocol."""
    assert isinstance(_DummyAdapter(), HarnessAdapter)


def test_start_request_supports_read_only_and_plan_flags() -> None:
    """StartRequest carries the native-session control-plane knobs."""
    request = StartRequest(
        cwd="/repo",
        prompt="inspect auth flow",
        read_only=True,
        plan_mode=True,
        permission_mode="plan",
        sandbox_mode="workspace-write",
    )
    assert request.read_only is True
    assert request.plan_mode is True
    assert request.permission_mode == "plan"
    assert request.sandbox_mode == "workspace-write"


def test_harness_probe_preserves_capabilities() -> None:
    """Probe objects should carry the capability matrix unchanged."""
    caps = HarnessCapabilities(
        supports_resume=True,
        supports_structured_output=True,
        supports_transcript_export=True,
    )
    probe = HarnessProbe(
        kind=HarnessKind.CLAUDE_CODE,
        binary="claude",
        available=True,
        version="2.1.90",
        capabilities=caps,
    )
    assert probe.capabilities.supports_resume is True
    assert probe.capabilities.supports_structured_output is True
    assert probe.capabilities.supports_transcript_export is True


def test_harness_event_and_artifact_models() -> None:
    """Event and artifact dataclasses expose transcript-first metadata."""
    session = SessionHandle(kind=HarnessKind.OPENCODE, session_id="s1", cwd="/repo")
    run = RunHandle(session=session, run_id="r1")
    event = HarnessEvent(
        event_type=HarnessEventType.STDOUT,
        session_id=session.session_id,
        run_id=run.run_id,
        raw_text="hello",
    )
    artifacts = ArtifactBundle(
        transcript_path="logs/session.jsonl",
        changed_files=("src/app.py",),
        executed_commands=("opencode run",),
    )
    assert event.raw_text == "hello"
    assert artifacts.transcript_path == "logs/session.jsonl"
    assert artifacts.changed_files == ("src/app.py",)
