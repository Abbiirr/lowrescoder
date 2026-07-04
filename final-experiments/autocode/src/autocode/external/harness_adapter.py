"""Canonical external harness adapter contract.

This module defines the normalized control-plane boundary for orchestrating
native external harnesses such as Codex, Claude Code, OpenCode, and Forge.
Concrete adapters should map native CLI/runtime semantics into these types
without pretending unsupported capabilities exist.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class HarnessKind(StrEnum):
    """Supported harness families."""

    AUTOCODE_NATIVE = "autocode_native"
    CODEX = "codex"
    CLAUDE_CODE = "claude_code"
    OPENCODE = "opencode"
    FORGE = "forge"


class HarnessEventType(StrEnum):
    """Normalized event types emitted by native harness adapters."""

    SESSION_STARTED = "session_started"
    RUN_STARTED = "run_started"
    STDOUT = "stdout"
    STDERR = "stderr"
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    APPROVAL = "approval"
    ARTIFACT = "artifact"
    RESULT = "result"
    ERROR = "error"
    RUN_FINISHED = "run_finished"
    SESSION_CLOSED = "session_closed"


@dataclass(frozen=True)
class HarnessCapabilities:
    """Capability flags advertised by a concrete harness adapter."""

    supports_resume: bool = False
    supports_fork: bool = False
    supports_structured_output: bool = False
    supports_streaming_events: bool = False
    supports_native_worktree: bool = False
    supports_native_plan_mode: bool = False
    supports_native_permission_modes: bool = False
    supports_transcript_export: bool = False
    supports_agent_spawn: bool = False
    supports_remote_attach: bool = False


@dataclass(frozen=True)
class HarnessProbe:
    """Discovery result for one harness family."""

    kind: HarnessKind
    binary: str
    available: bool
    version: str = ""
    capabilities: HarnessCapabilities = field(default_factory=HarnessCapabilities)
    notes: str = ""


@dataclass(frozen=True)
class StartRequest:
    """Parameters for starting a fresh native harness session."""

    cwd: str
    prompt: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    worktree: str | None = None
    permission_mode: str | None = None
    sandbox_mode: str | None = None
    plan_mode: bool = False
    read_only: bool = False
    extra_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromptInput:
    """User-like prompt payload passed into a running native harness."""

    text: str
    stdin_text: str | None = None
    structured_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResumeRequest:
    """Parameters for continuing a previously created native harness session."""

    session_id: str
    cwd: str | None = None
    prompt: PromptInput | None = None
    fork: bool = False
    extra_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionHandle:
    """Opaque session metadata tracked by AutoCode."""

    kind: HarnessKind
    session_id: str
    cwd: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunHandle:
    """Opaque run metadata tracked by AutoCode."""

    session: SessionHandle
    run_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HarnessEvent:
    """One normalized event emitted by a concrete adapter."""

    event_type: HarnessEventType
    session_id: str
    run_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


@dataclass(frozen=True)
class ArtifactBundle:
    """Transcript-first artifact capture from a native harness session."""

    transcript_path: str | None = None
    export_path: str | None = None
    changed_files: tuple[str, ...] = ()
    executed_commands: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionSnapshot:
    """Current known state of a native harness session."""

    session_id: str
    cwd: str
    status: str
    last_run_id: str | None = None
    changed_files: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class HarnessAdapter(Protocol):
    """Capability-aware contract for native external harness orchestration."""

    def probe(self) -> HarnessProbe: ...

    def start(self, request: StartRequest) -> SessionHandle: ...

    def send(self, session: SessionHandle, prompt: PromptInput) -> RunHandle: ...

    def resume(self, request: ResumeRequest) -> SessionHandle: ...

    def interrupt(self, session: SessionHandle) -> None: ...

    def shutdown(self, session: SessionHandle) -> None: ...

    def stream_events(self, run: RunHandle) -> Iterator[HarnessEvent]: ...

    def capture_artifacts(self, session: SessionHandle) -> ArtifactBundle: ...

    def snapshot_state(self, session: SessionHandle) -> SessionSnapshot: ...
