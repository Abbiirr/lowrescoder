"""OpenCode external harness adapter.

Maps OpenCode CLI native surfaces into the HarnessAdapter protocol:
- `opencode run <prompt>` for non-interactive runs
- `--format json` for structured output
- `--continue <session>` / `--session` for continuation
- `--fork` for session forking
"""

from __future__ import annotations

import shutil
import subprocess
import uuid
from collections.abc import Iterator

from autocode.external.event_normalizer import (
    OPENCODE_KIND_MAP,
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


class OpenCodeAdapter:
    """Concrete HarnessAdapter for OpenCode CLI."""

    BINARY = "opencode"

    def probe(self) -> HarnessProbe:
        binary = shutil.which(self.BINARY)
        if not binary:
            return HarnessProbe(
                kind=HarnessKind.OPENCODE,
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
            kind=HarnessKind.OPENCODE,
            binary=binary,
            available=True,
            version=version,
            capabilities=HarnessCapabilities(
                supports_resume=True,
                supports_fork=True,
                supports_structured_output=True,
                supports_streaming_events=True,
                supports_native_worktree=False,
                supports_native_plan_mode=False,
                supports_native_permission_modes=False,
                supports_transcript_export=True,
                supports_remote_attach=True,
            ),
        )

    def start(self, request: StartRequest) -> SessionHandle:
        session_id = str(uuid.uuid4())[:8]
        return SessionHandle(
            kind=HarnessKind.OPENCODE,
            session_id=session_id,
            cwd=request.cwd,
            metadata={"prompt": request.prompt},
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
            kind=HarnessKind.OPENCODE,
            session_id=request.session_id,
            cwd=request.cwd or ".",
            metadata={"resumed": True, "fork": request.fork},
        )

    def interrupt(self, session: SessionHandle) -> None:
        proc = session.metadata.get("_process")
        if proc and proc.poll() is None:
            proc.terminate()

    def shutdown(self, session: SessionHandle) -> None:
        self.interrupt(session)

    def build_command(self, session: SessionHandle, prompt: str) -> list[str]:
        """Build the opencode CLI command."""
        meta = session.metadata
        cmd = [self.BINARY, "run", prompt, "--format", "json"]

        if meta.get("resumed"):
            cmd.extend(["--continue", session.session_id])
            if meta.get("fork"):
                cmd.append("--fork")

        return cmd

    def stream_events(self, run: RunHandle) -> Iterator[HarnessEvent]:
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
                kind_map=OPENCODE_KIND_MAP,
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
