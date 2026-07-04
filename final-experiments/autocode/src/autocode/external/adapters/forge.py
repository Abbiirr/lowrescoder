"""Forge external harness adapter.

Maps Forge CLI native surfaces into the HarnessAdapter protocol:
- `forge --prompt <prompt>` for non-interactive runs
- `--conversation-id` for session tracking
- `--sandbox` for sandbox mode
- `conversation dump/resume/info/stats/clone` for transcript management
"""

from __future__ import annotations

import shutil
import subprocess
import uuid
from collections.abc import Iterator

from autocode.external.event_normalizer import (
    FORGE_KIND_MAP,
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


class ForgeAdapter:
    """Concrete HarnessAdapter for Forge CLI."""

    BINARY = "forge"

    def probe(self) -> HarnessProbe:
        binary = shutil.which(self.BINARY)
        if not binary:
            return HarnessProbe(
                kind=HarnessKind.FORGE,
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
            kind=HarnessKind.FORGE,
            binary=binary,
            available=True,
            version=version,
            capabilities=HarnessCapabilities(
                supports_resume=True,
                supports_fork=False,
                supports_structured_output=False,
                supports_streaming_events=False,
                supports_native_worktree=False,
                supports_native_plan_mode=False,
                supports_native_permission_modes=True,
                supports_transcript_export=True,
                supports_agent_spawn=True,
            ),
        )

    def start(self, request: StartRequest) -> SessionHandle:
        session_id = str(uuid.uuid4())[:8]
        return SessionHandle(
            kind=HarnessKind.FORGE,
            session_id=session_id,
            cwd=request.cwd,
            metadata={
                "prompt": request.prompt,
                "sandbox": request.sandbox_mode,
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
            kind=HarnessKind.FORGE,
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
        """Build the forge CLI command."""
        meta = session.metadata
        cmd = [self.BINARY, "--prompt", prompt]

        cmd.extend(["--conversation-id", session.session_id])

        if meta.get("sandbox"):
            cmd.extend(["--sandbox", meta["sandbox"]])
        if meta.get("resumed"):
            # Forge uses conversation resume
            cmd = [self.BINARY, "conversation", "resume", session.session_id]

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

        # Forge doesn't support structured streaming natively;
        # capture stdout as plain text events
        if proc.stdout:
            yield from normalize_stream(
                iter(proc.stdout),
                session.session_id,
                run.run_id,
                kind_map=FORGE_KIND_MAP,
            )

        proc.wait()

        yield make_event(
            HarnessEventType.RUN_FINISHED,
            session.session_id,
            run.run_id,
            payload={"exit_code": proc.returncode},
        )

    def capture_artifacts(self, session: SessionHandle) -> ArtifactBundle:
        """Capture transcript via `forge conversation dump` plus git diff."""
        changed = _detect_changed_files(session.cwd)
        try:
            result = subprocess.run(
                [self.BINARY, "conversation", "dump", session.session_id],
                cwd=session.cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return ArtifactBundle(
                    changed_files=tuple(changed),
                    metadata={
                        "session_id": session.session_id,
                        "transcript": result.stdout,
                    },
                )
        except (subprocess.TimeoutExpired, OSError):
            pass
        return ArtifactBundle(
            changed_files=tuple(changed),
            metadata={"session_id": session.session_id},
        )

    def snapshot_state(self, session: SessionHandle) -> SessionSnapshot:
        """Get session info via `forge conversation info`."""
        try:
            result = subprocess.run(
                [self.BINARY, "conversation", "info", session.session_id],
                cwd=session.cwd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return SessionSnapshot(
                    session_id=session.session_id,
                    cwd=session.cwd,
                    status="active",
                    metadata={"info": result.stdout},
                )
        except (subprocess.TimeoutExpired, OSError):
            pass
        return SessionSnapshot(
            session_id=session.session_id,
            cwd=session.cwd,
            status="unknown",
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
