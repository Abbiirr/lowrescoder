"""ExternalToolTracker — runtime discovery of external AI coding tools.

Detects Claude Code, Codex, OpenCode, Forge, and Gemini CLI on PATH.
Version probes with fail-closed behavior per R3/R11.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from autocode.external.harness_adapter import (
    HarnessCapabilities,
    HarnessKind,
    HarnessProbe,
)


@dataclass
class ExternalTool:
    """Detected external AI coding tool."""

    name: str
    binary: str
    version: str = ""
    available: bool = False
    supports_mcp: bool = False
    supports_json: bool = False
    capabilities: HarnessCapabilities = field(default_factory=HarnessCapabilities)

    def to_probe(self) -> HarnessProbe:
        """Convert discovery metadata into the canonical adapter probe format."""
        return HarnessProbe(
            kind=_HARNESS_KIND_BY_TOOL.get(self.name, HarnessKind.AUTOCODE_NATIVE),
            binary=self.binary,
            available=self.available,
            version=self.version,
            capabilities=self.capabilities,
        )


# Known tools and their binaries
KNOWN_TOOLS: dict[str, str] = {
    "claude_code": "claude",
    "codex": "codex",
    "opencode": "opencode",
    "forge": "forge",
    "gemini": "gemini",
}

# Minimum supported versions (fail-closed below these)
MIN_VERSIONS: dict[str, str] = {
    "claude_code": "1.0",
    "codex": "0.1",
    "opencode": "0.1",
    "forge": "0.1",
    "gemini": "0.1",
}

_CAPABILITIES_BY_TOOL: dict[str, HarnessCapabilities] = {
    "claude_code": HarnessCapabilities(
        supports_resume=True,
        supports_fork=True,
        supports_structured_output=True,
        supports_streaming_events=True,
        supports_native_worktree=True,
        supports_native_plan_mode=True,
        supports_native_permission_modes=True,
        supports_agent_spawn=True,
    ),
    "codex": HarnessCapabilities(
        supports_resume=True,
        supports_structured_output=True,
        supports_streaming_events=True,
        supports_native_permission_modes=True,
        supports_transcript_export=True,
        supports_agent_spawn=True,
    ),
    "opencode": HarnessCapabilities(
        supports_resume=True,
        supports_fork=True,
        supports_structured_output=True,
        supports_streaming_events=True,
        supports_native_plan_mode=True,
        supports_native_permission_modes=True,
        supports_transcript_export=True,
        supports_agent_spawn=True,
        supports_remote_attach=True,
    ),
    "forge": HarnessCapabilities(
        supports_resume=True,
        supports_fork=True,
        supports_streaming_events=True,
        supports_native_permission_modes=True,
        supports_transcript_export=True,
        supports_agent_spawn=True,
    ),
    "gemini": HarnessCapabilities(),
}

_HARNESS_KIND_BY_TOOL: dict[str, HarnessKind] = {
    "claude_code": HarnessKind.CLAUDE_CODE,
    "codex": HarnessKind.CODEX,
    "opencode": HarnessKind.OPENCODE,
    "forge": HarnessKind.FORGE,
    "gemini": HarnessKind.AUTOCODE_NATIVE,
}


class ExternalToolTracker:
    """Runtime discovery of external AI coding tools.

    Checks PATH for known tool binaries, probes versions,
    and reports capabilities.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ExternalTool] = {}

    def discover(self) -> list[ExternalTool]:
        """Check PATH for known tools and probe their versions."""
        tools: list[ExternalTool] = []
        for name, binary in KNOWN_TOOLS.items():
            tool = self._probe_tool(name, binary)
            self._tools[name] = tool
            tools.append(tool)
        return tools

    def get(self, name: str) -> ExternalTool | None:
        """Get a discovered tool by name."""
        return self._tools.get(name)

    @property
    def available_tools(self) -> list[ExternalTool]:
        """List tools that are available on this system."""
        return [t for t in self._tools.values() if t.available]

    @staticmethod
    def _probe_tool(name: str, binary: str) -> ExternalTool:
        """Probe a single tool: check PATH, get version."""
        path = shutil.which(binary)
        if not path:
            return ExternalTool(name=name, binary=binary)

        # Get version
        version = ""
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0]
        except Exception:
            pass

        # Capability probes
        supports_mcp = name in ("claude_code", "codex", "opencode")
        supports_json = name in ("claude_code", "codex", "opencode")

        return ExternalTool(
            name=name,
            binary=binary,
            version=version,
            available=True,
            supports_mcp=supports_mcp,
            supports_json=supports_json,
            capabilities=_CAPABILITIES_BY_TOOL.get(name, HarnessCapabilities()),
        )
