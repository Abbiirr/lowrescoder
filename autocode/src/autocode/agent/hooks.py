"""Hook lifecycle runtime.

Claude-Code-style hook bus with five lifecycle events:

- ``SessionStart`` — fires once per session (advisory; never blocks)
- ``PreToolUse`` — fires before a tool call; **can block the call**
- ``PostToolUse`` — fires after a tool call (advisory; never blocks)
- ``Stop`` — fires at end of turn on success (advisory)
- ``StopFailure`` — fires at end of turn on failure (advisory)

Hooks are external shell commands configured in ``.claude/settings.json`` at
project scope and/or ``~/.claude/settings.json`` at user scope. Both are
merged, project-first.

## Blocking protocol

PreToolUse hooks can block a tool call by either:

1. Exiting with a non-zero status code, OR
2. Printing a JSON object on stdout with ``{"block": true, "reason": "..."}``.

Timeouts also block. All other events discard block signals.

## Payload / I/O

The JSON-serialized payload is written to hook stdin. The runtime injects
canonical keys (``event``, ``tool_name`` if applicable) in addition to any
caller-supplied dict. Hooks receive two environment variables:

- ``AUTOCODE_EVENT`` — the event name (matches enum value)
- ``AUTOCODE_SESSION_ID`` — the session id if the payload contained one
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from autocode.agent.auto_verify import AutoVerifyConfig, verify_after_edit
from autocode.agent.drift import (
    ContextStalenessDetector,
    SchemaDriftDetector,
    ToolConsistencyDetector,
    format_drift_warning,
)
from autocode.agent.git_aware_staging import stage_post_edit
from autocode.agent.scratch import ScratchStore, is_scratch_stub
from autocode.session.file_snapshot import snapshot_files


class HookEvent(StrEnum):
    """Lifecycle events a hook can register for."""

    SESSION_START = "SessionStart"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"


class HookSource(StrEnum):
    PROJECT = "project"
    USER = "user"


class Hook(Protocol):
    """Internal declarative hook contract used by AgentLoop integrations."""

    def should_run(self) -> bool:
        """Return False to skip this hook for the current dispatch."""
        ...

    def pre_tool_call(self, tc: Any) -> None:
        ...

    def post_tool_call_success(self, tc: Any, result: str) -> str | None:
        ...

    async def post_tool_call_success_async(self, tc: Any, result: str) -> str | None:
        ...

    def post_tool_call_error(self, tc: Any, exc: BaseException) -> None:
        ...

    def pre_turn(self, turn_id: str) -> None:
        ...

    def post_turn(self, turn_id: str, status: str) -> None:
        ...

    def on_token(self, text: str) -> None:
        ...


class HookDispatcher:
    """Ordered, exception-isolating dispatcher for internal hooks."""

    def __init__(self, hooks: list[Hook] | None = None) -> None:
        self._hooks: list[Hook] = list(hooks or [])

    def register(self, hook: Hook) -> None:
        self._hooks.append(hook)

    def hooks(self) -> list[Hook]:
        return list(self._hooks)

    def pre_tool_call(self, tc: Any) -> None:
        for hook in self._active_hooks():
            self._call(hook.pre_tool_call, tc)

    def post_tool_call_success(self, tc: Any, result: str) -> str:
        current = result
        for hook in self._active_hooks():
            override = self._call(hook.post_tool_call_success, tc, current)
            if override is not None:
                current = str(override)
        return current

    async def post_tool_call_success_async(self, tc: Any, result: str) -> str:
        current = result
        for hook in self._active_hooks():
            method = getattr(hook, "post_tool_call_success_async", None)
            if method is None:
                continue
            override = await self._call_async(method, tc, current)
            if override is not None:
                current = str(override)
        return current

    def post_tool_call_error(self, tc: Any, exc: BaseException) -> None:
        for hook in self._active_hooks():
            self._call(hook.post_tool_call_error, tc, exc)

    def pre_turn(self, turn_id: str) -> None:
        for hook in self._active_hooks():
            self._call(hook.pre_turn, turn_id)

    def post_turn(self, turn_id: str, status: str) -> None:
        for hook in self._active_hooks():
            self._call(hook.post_turn, turn_id, status)

    def on_token(self, text: str) -> None:
        for hook in self._active_hooks():
            self._call(hook.on_token, text)

    def _active_hooks(self) -> list[Hook]:
        active: list[Hook] = []
        for hook in self._hooks:
            should_run = getattr(hook, "should_run", None)
            if should_run is None:
                active.append(hook)
                continue
            try:
                if should_run():
                    active.append(hook)
            except Exception:  # noqa: BLE001
                continue
        return active

    @staticmethod
    def _call(method: Any, *args: Any) -> Any:
        try:
            return method(*args)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    async def _call_async(method: Any, *args: Any) -> Any:
        try:
            return await method(*args)
        except Exception:  # noqa: BLE001
            return None


class AgentHookBase:
    """No-op base class for internal hook adapters."""

    def should_run(self) -> bool:
        return True

    def pre_tool_call(self, tc: Any) -> None:
        return None

    def post_tool_call_success(self, tc: Any, result: str) -> str | None:
        return None

    async def post_tool_call_success_async(self, tc: Any, result: str) -> str | None:
        return None

    def post_tool_call_error(self, tc: Any, exc: BaseException) -> None:
        return None

    def pre_turn(self, turn_id: str) -> None:
        return None

    def post_turn(self, turn_id: str, status: str) -> None:
        return None

    def on_token(self, text: str) -> None:
        return None


class ScratchOffloadHook(AgentHookBase):
    """Offload large tool outputs before context truncation."""

    def __init__(
        self,
        *,
        scratch_store: ScratchStore | None,
        telemetry_emit: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._scratch_store = scratch_store
        self._telemetry_emit = telemetry_emit
        self._turn_id = "turn-000"

    def should_run(self) -> bool:
        return self._scratch_store is not None

    def pre_turn(self, turn_id: str) -> None:
        self._turn_id = turn_id

    def post_tool_call_success(self, tc: Any, result: str) -> str | None:
        if self._scratch_store is None or is_scratch_stub(result):
            return None
        original_result_bytes = len(result.encode("utf-8", errors="replace"))
        offloaded = self._scratch_store.offload_if_large(
            tc.name,
            tc.arguments,
            result,
            turn_id=self._turn_id,
        )
        if self._scratch_store.last_offload is None:
            return None
        if self._telemetry_emit is not None:
            self._telemetry_emit(
                "tool_output_offloaded",
                {
                    "tool_name": tc.name,
                    "result_bytes": original_result_bytes,
                    "scratch_path": self._scratch_store.last_offload.path,
                },
            )
        return offloaded


class GitAwareStagingHook(AgentHookBase):
    """Stage files touched by successful mutating tools and append a proposal."""

    def __init__(
        self,
        *,
        project_root: Path | None,
        extract_touched_files: Callable[[Any], list[str]],
    ) -> None:
        self._project_root = project_root
        self._extract_touched_files = extract_touched_files

    def should_run(self) -> bool:
        return self._project_root is not None

    def post_tool_call_success(self, tc: Any, result: str) -> str | None:
        if self._project_root is None:
            return None
        touched = self._extract_touched_files(tc)
        if not touched:
            return None
        staging = stage_post_edit(touched, project_root=self._project_root)
        if not staging.staged:
            return None
        staging_note = (
            "Git-aware staging: staged "
            f"{', '.join(staging.files)}.\n"
            f"Proposed commit message: {staging.proposed_commit_message}"
        )
        return f"{result}\n\n{staging_note}"


class PerToolCheckpointHook(AgentHookBase):
    """Create per-tool file snapshots before approved mutating tools execute."""

    def __init__(
        self,
        *,
        checkpoint_store: Any | None,
        task_store: Any | None,
        project_root: Path | None,
        session_id: str,
        extract_touched_files: Callable[[Any], list[str]],
    ) -> None:
        self._checkpoint_store = checkpoint_store
        self._task_store = task_store
        self._project_root = project_root
        self._session_id = session_id
        self._extract_touched_files = extract_touched_files
        self._tool_call_idx = 0

    def should_run(self) -> bool:
        return (
            self._checkpoint_store is not None
            and self._task_store is not None
            and self._project_root is not None
        )

    def pre_tool_call(self, tc: Any) -> None:
        if self._checkpoint_store is None or self._task_store is None or self._project_root is None:
            return
        touched = self._extract_touched_files(tc)
        if not touched:
            return
        snap_dir = Path.home() / ".autocode" / "snapshots" / self._session_id / tc.id
        snap_dir.mkdir(parents=True, exist_ok=True)
        snapshot_files(self._project_root, snap_dir, touched)
        self._checkpoint_store.save_per_tool_checkpoint(
            self._task_store,
            tool_call_id=tc.id,
            tool_name=tc.name,
            tool_call_idx=self._tool_call_idx,
            kind="pre_tool",
            files_touched=touched,
            label=f"pre {tc.name}",
        )
        self._tool_call_idx += 1


class AutoVerifyHook(AgentHookBase):
    """Run post-edit verification after successful mutating tool calls."""

    def __init__(
        self,
        *,
        project_root: Path | None,
        config: AutoVerifyConfig | None,
        verify_after_edit: Callable[..., Awaitable[Any]] = verify_after_edit,
        extract_touched_files: Callable[[Any], list[str]],
        pop_cost_limit_warning: Callable[[], tuple[float, float] | None] | None = None,
    ) -> None:
        self._project_root = project_root
        self._config = config or AutoVerifyConfig()
        self._verify_after_edit = verify_after_edit
        self._extract_touched_files = extract_touched_files
        self._pop_cost_limit_warning = pop_cost_limit_warning
        self._verification_failure_count = 0

    def should_run(self) -> bool:
        return self._project_root is not None and self._config.enabled

    async def post_tool_call_success_async(self, tc: Any, result: str) -> str | None:
        if self._project_root is None or not self._config.enabled:
            return None
        touched = self._extract_touched_files(tc)
        if not touched:
            return None
        try:
            verification = await self._verify_after_edit(
                touched,
                project_root=self._project_root,
                config=self._config,
            )
        except Exception as exc:  # noqa: BLE001
            return f"{result}\n\nVerification unavailable: {type(exc).__name__}: {exc}"
        if not verification.checked_files:
            return None
        if verification.ok:
            self._verification_failure_count = 0
            return f"{result}\n\n{verification.to_system_message(project_root=self._project_root)}"

        self._verification_failure_count += 1
        note = verification.to_system_message(project_root=self._project_root)
        cost_warning = self._pop_cost_limit_warning() if self._pop_cost_limit_warning else None
        if cost_warning is not None:
            total, limit = cost_warning
            note = (
                f"{note}\n"
                "Verification retry halted: cost limit reached "
                f"(${total:.2f} used, ${limit:.2f} limit)."
            )
        elif self._verification_failure_count >= self._config.max_iterations:
            plural = "s" if self._config.max_iterations != 1 else ""
            note = (
                f"{note}\n"
                f"Verification failed after {self._config.max_iterations} iteration{plural}. "
                "No automatic rollback was performed. Use /rollback to inspect or restore "
                "a user-confirmed checkpoint."
            )
        return f"{result}\n\n{note}"


class DriftDetectionHook(AgentHookBase):
    """Observe tool results and queue drift warnings for the next model turn."""

    def __init__(
        self,
        *,
        schema_detector: SchemaDriftDetector,
        consistency_detector: ToolConsistencyDetector,
        staleness_detector: ContextStalenessDetector | None = None,
        telemetry_emit: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._schema_detector = schema_detector
        self._consistency_detector = consistency_detector
        self._staleness_detector = staleness_detector
        self._telemetry_emit = telemetry_emit
        self._warnings: list[str] = []

    def pre_turn(self, turn_id: str) -> None:
        self._consistency_detector.reset_turn()
        self._warnings.clear()

    def post_tool_call_success(self, tc: Any, result: str) -> str | None:
        observed = _parse_json_result(result)
        warnings = [
            self._schema_detector.observe(tc.name, tc.arguments, observed),
            self._consistency_detector.observe(tc.name, tc.arguments, observed),
        ]
        if self._staleness_detector is not None and tc.name == "memory_read_topic":
            slug = tc.arguments.get("slug")
            if slug:
                warnings.append(self._staleness_detector.check_fact_freshness(str(slug)))
        for warning in warnings:
            if warning is None:
                continue
            self._warnings.append(format_drift_warning(warning))
            if self._telemetry_emit is not None:
                self._telemetry_emit(
                    "tool_drift_detected",
                    {
                        "tool_name": warning.tool_name or tc.name,
                        "drift_kind": warning.kind,
                        "severity": warning.severity,
                    },
                )
        return None

    def drain_warnings(self) -> list[str]:
        warnings = list(self._warnings)
        self._warnings.clear()
        return warnings


def _parse_json_result(result: Any) -> Any:
    if not isinstance(result, str):
        return result
    stripped = result.strip()
    if not stripped:
        return result
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return result


@dataclass(frozen=True)
class HookDefinition:
    """Configuration for one hook registered to one event."""

    event: HookEvent
    command: list[str]
    matcher: str = "*"
    timeout_s: float = 5.0
    source: HookSource = HookSource.PROJECT


@dataclass
class HookResult:
    """Result of firing one hook."""

    hook: HookDefinition
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    blocked: bool = False
    block_reason: str = ""


@dataclass
class HookRegistry:
    """Registry of hooks, loaded from project + user settings.json."""

    hooks: list[HookDefinition] = field(default_factory=list)
    project_root: Path = field(default_factory=Path.cwd)

    # ----- loading -----

    @classmethod
    def load(
        cls,
        project_root: Path | str,
        user_root: Path | str | None,
    ) -> HookRegistry:
        """Read project and user ``.claude/settings.json`` into a registry.

        Missing / malformed files degrade to empty.
        """
        project_root = Path(project_root)
        hooks: list[HookDefinition] = []

        hooks.extend(cls._load_from(project_root, HookSource.PROJECT))
        if user_root is not None:
            hooks.extend(cls._load_from(Path(user_root), HookSource.USER))

        return cls(hooks=hooks, project_root=project_root)

    @staticmethod
    def _load_from(root: Path, source: HookSource) -> list[HookDefinition]:
        settings_path = root / ".claude" / "settings.json"
        if not settings_path.is_file():
            return []
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        hooks_section = data.get("hooks") if isinstance(data, dict) else None
        if not isinstance(hooks_section, dict):
            return []

        out: list[HookDefinition] = []
        for event_name, defs in hooks_section.items():
            try:
                event = HookEvent(event_name)
            except ValueError:
                continue  # unknown event → ignore
            if not isinstance(defs, list):
                continue
            for entry in defs:
                if not isinstance(entry, dict):
                    continue
                command = entry.get("command")
                if not isinstance(command, list) or not command:
                    continue
                matcher = entry.get("matcher", "*")
                timeout_s = float(entry.get("timeout_s", 5.0))
                out.append(
                    HookDefinition(
                        event=event,
                        command=[str(c) for c in command],
                        matcher=str(matcher) if matcher else "*",
                        timeout_s=max(0.05, timeout_s),
                        source=source,
                    )
                )
        return out

    # ----- query -----

    def hooks_for(self, event: HookEvent) -> list[HookDefinition]:
        return [h for h in self.hooks if h.event == event]

    # ----- fire -----

    def fire(
        self,
        event: HookEvent,
        payload: dict[str, Any],
        *,
        tool_name: str = "",
    ) -> list[HookResult]:
        """Fire all hooks matching ``event`` (filtered by matcher).

        For PreToolUse, stops iteration once a hook blocks. For other events,
        every hook runs.
        """
        hooks = self.hooks_for(event)
        if not hooks:
            return []

        # Canonical payload keys
        canonical = dict(payload)
        canonical["event"] = event.value
        if tool_name:
            canonical["tool_name"] = tool_name

        stdin_bytes = (json.dumps(canonical) + "\n").encode("utf-8")
        env = self._build_env(event, canonical)

        results: list[HookResult] = []
        for hook in hooks:
            if not self._matches(hook, tool_name):
                continue
            result = self._run_hook(hook, stdin_bytes, env)
            results.append(result)
            if event == HookEvent.PRE_TOOL_USE and result.blocked:
                break
        return results

    # ----- helpers -----

    @staticmethod
    def _build_env(event: HookEvent, payload: dict[str, Any]) -> dict[str, str]:
        env = os.environ.copy()
        env["AUTOCODE_EVENT"] = event.value
        sid = payload.get("session_id")
        if isinstance(sid, str):
            env["AUTOCODE_SESSION_ID"] = sid
        tn = payload.get("tool_name")
        if isinstance(tn, str):
            env["AUTOCODE_TOOL_NAME"] = tn
        return env

    @staticmethod
    def _matches(hook: HookDefinition, tool_name: str) -> bool:
        matcher = hook.matcher
        if matcher == "*":
            return True
        if not tool_name:
            # Non-tool events skip matcher filtering entirely.
            return True
        try:
            return re.fullmatch(matcher, tool_name) is not None
        except re.error:
            return matcher == tool_name

    def _run_hook(
        self,
        hook: HookDefinition,
        stdin: bytes,
        env: dict[str, str],
    ) -> HookResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(  # noqa: S603 — hooks are user-authored by design
                hook.command,
                input=stdin,
                env=env,
                cwd=str(self.project_root),
                capture_output=True,
                timeout=hook.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            return HookResult(
                hook=hook,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=duration_ms,
                blocked=hook.event == HookEvent.PRE_TOOL_USE,
                block_reason="hook timeout",
            )
        except (OSError, ValueError) as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return HookResult(
                hook=hook,
                exit_code=-2,
                stdout="",
                stderr=str(exc),
                duration_ms=duration_ms,
                blocked=False,
                block_reason="",
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")

        blocked = False
        reason = ""
        if hook.event == HookEvent.PRE_TOOL_USE:
            if proc.returncode != 0:
                blocked = True
                reason = stderr.strip() or f"exit={proc.returncode}"
            else:
                json_block = self._parse_block(stdout)
                if json_block is not None:
                    blocked = json_block.get("block", False)
                    reason = str(json_block.get("reason", ""))

        return HookResult(
            hook=hook,
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            blocked=blocked,
            block_reason=reason,
        )

    @staticmethod
    def _parse_block(stdout: str) -> dict[str, Any] | None:
        stripped = stdout.strip()
        if not stripped.startswith("{"):
            return None
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    # ----- convenience -----

    @staticmethod
    def is_blocking(results: list[HookResult]) -> bool:
        return any(r.blocked for r in results)


__all__ = [
    "AgentHookBase",
    "AutoVerifyHook",
    "DriftDetectionHook",
    "GitAwareStagingHook",
    "Hook",
    "HookDefinition",
    "HookDispatcher",
    "HookEvent",
    "HookRegistry",
    "HookResult",
    "HookSource",
    "PerToolCheckpointHook",
    "ScratchOffloadHook",
]
