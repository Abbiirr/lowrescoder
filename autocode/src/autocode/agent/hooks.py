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
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


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
    "HookDefinition",
    "HookEvent",
    "HookRegistry",
    "HookResult",
    "HookSource",
]
