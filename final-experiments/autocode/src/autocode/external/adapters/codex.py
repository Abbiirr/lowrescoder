"""Codex external harness adapter.

Maps Codex CLI native surfaces into the HarnessAdapter protocol:
- `codex exec <prompt>` for non-interactive runs
- `codex exec resume <session>` for continuation
- JSONL output for structured streaming
- `--json` for structured final output
"""

from __future__ import annotations

import shutil
import subprocess
import uuid
from collections.abc import Iterator

from autocode.external.event_normalizer import (
    CODEX_KIND_MAP,
    make_event,
    normalize_stream,
)
from autocode.external.harness_adapter import (
    ArtifactBundle,
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


class CodexAdapter:
    """Concrete HarnessAdapter for Codex CLI."""

    BINARY = "codex"

    def probe(self) -> HarnessProbe:
        binary = shutil.which(self.BINARY)
        if not binary:
            return HarnessProbe(
                kind=HarnessKind.CODEX,
                binary=self.BINARY,
                available=False,
            )
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version = result.stdout.strip().split("\n")[0]
        except (subprocess.TimeoutExpired, OSError):
            version = "unknown"

        return HarnessProbe(
            kind=HarnessKind.CODEX,
            binary=binary,
            available=True,
            version=version,
            capabilities=HarnessCapabilities(
                supports_resume=True,
                supports_structured_output=True,
                supports_streaming_events=True,
                supports_native_worktree=False,
                supports_native_plan_mode=False,
                supports_native_permission_modes=True,
                supports_transcript_export=True,
            ),
        )

    def start(self, request: StartRequest) -> SessionHandle:
        session_id = str(uuid.uuid4())[:8]
        return SessionHandle(
            kind=HarnessKind.CODEX,
            session_id=session_id,
            cwd=request.cwd,
            metadata={
                "prompt": request.prompt,
                "sandbox_mode": request.sandbox_mode,
            },
        )

    def send(self, session: SessionHandle, prompt: PromptInput) -> RunHandle:
        run_id = str(uuid.uuid4())[:8]
        return RunHandle(
            session=session,
            run_id=run_id,
            metadata={"prompt": prompt.text},
        )

    def resume(self, request: ResumeRequest) -> SessionHandle:
        return SessionHandle(
            kind=HarnessKind.CODEX,
            session_id=request.session_id,
            cwd=request.cwd or ".",
            metadata={"resumed": True},
        )

    def interrupt(self, session: SessionHandle) -> None:
        proc = session.metadata.get("_process")
        if proc and proc.poll() is None:
            proc.terminate()

    def shutdown(self, session: SessionHandle) -> None:
        self.interrupt(session)

    def build_command(self, session: SessionHandle, prompt: str) -> list[str]:
        """Build the codex CLI command."""
        meta = session.metadata

        if meta.get("resumed"):
            cmd = [self.BINARY, "exec", "resume", session.session_id]
        else:
            cmd = [self.BINARY, "exec", prompt]

        cmd.append("--json")

        if meta.get("sandbox_mode"):
            cmd.extend(["--sandbox", meta["sandbox_mode"]])

        if meta.get("read_only"):
            cmd.append("--readonly")

        return cmd

    def stream_events(self, run: RunHandle) -> Iterator[HarnessEvent]:
        """Execute and stream normalized events from codex CLI."""
        session = run.session
        prompt = run.metadata.get("prompt", "")
        cmd = self.build_command(session, prompt)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=session.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as e:
            yield make_event(
                HarnessEventType.ERROR,
                session.session_id,
                run.run_id,
                payload={"error": str(e)},
            )
            return

        session.metadata["_process"] = proc

        yield make_event(
            HarnessEventType.SESSION_STARTED,
            session.session_id,
            run.run_id,
        )
        yield make_event(
            HarnessEventType.RUN_STARTED,
            session.session_id,
            run.run_id,
        )

        if proc.stdout:
            yield from normalize_stream(
                iter(proc.stdout),
                session.session_id,
                run.run_id,
                kind_map=CODEX_KIND_MAP,
            )

        proc.wait()

        yield make_event(
            HarnessEventType.RUN_FINISHED,
            session.session_id,
            run.run_id,
            payload={"exit_code": proc.returncode},
        )

    def capture_artifacts(self, session: SessionHandle) -> ArtifactBundle:
        """Capture artifacts including git diff of changed files."""
        changed = _detect_changed_files(session.cwd)
        return ArtifactBundle(
            changed_files=tuple(changed),
            metadata={"session_id": session.session_id},
        )

    def snapshot_state(self, session: SessionHandle) -> SessionSnapshot:
        """Snapshot with changed file detection."""
        changed = _detect_changed_files(session.cwd)
        proc = session.metadata.get("_process")
        status = "active" if proc and getattr(proc, "poll", lambda: None)() is None else "ended"
        return SessionSnapshot(
            session_id=session.session_id,
            cwd=session.cwd,
            status=status,
            changed_files=tuple(changed),
        )


def _detect_changed_files(cwd: str) -> list[str]:
    """Detect files changed in the working directory via git diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return []
