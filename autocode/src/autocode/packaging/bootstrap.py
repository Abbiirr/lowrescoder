"""First-run bootstrap — detect missing dependencies and guide setup.

Handles Ollama detection, model pulling, and initial configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from autocode.packaging.installer import is_autocode_on_path
from autocode.packaging.platform_detect import PlatformInfo, detect_platform


@dataclass
class BootstrapStep:
    """A single bootstrap step with status."""

    name: str
    description: str
    required: bool = True
    completed: bool = False
    error: str = ""
    remediation: str = ""


@dataclass
class BootstrapResult:
    """Result of the bootstrap process."""

    steps: list[BootstrapStep] = field(default_factory=list)
    platform: PlatformInfo | None = None
    ready: bool = False

    @property
    def passed_count(self) -> int:
        return sum(1 for s in self.steps if s.completed)

    @property
    def failed_required(self) -> list[BootstrapStep]:
        return [s for s in self.steps if s.required and not s.completed]

    def summary(self) -> str:
        lines = ["AutoCode First-Run Setup", "=" * 40]
        for step in self.steps:
            status = "OK" if step.completed else "NEEDED"
            req = " (required)" if step.required else " (optional)"
            lines.append(f"  [{status}] {step.name}{req}")
            if not step.completed and step.remediation:
                lines.append(f"         -> {step.remediation}")
        lines.append(f"\n{self.passed_count}/{len(self.steps)} steps complete")
        if self.ready:
            lines.append("AutoCode is ready to use!")
        else:
            lines.append("Please complete the required steps above.")
        return "\n".join(lines)


def run_bootstrap() -> BootstrapResult:
    """Run first-run bootstrap checks."""
    platform_info = detect_platform()
    steps: list[BootstrapStep] = []

    # Step 1: Python version
    py_ok = tuple(int(x) for x in platform_info.python_version.split(".")[:2]) >= (3, 11)
    steps.append(BootstrapStep(
        name="Python 3.11+",
        description="Required Python version",
        completed=py_ok,
        remediation="Install Python 3.11+: https://python.org/downloads/",
    ))

    # Step 2: Git
    steps.append(BootstrapStep(
        name="Git",
        description="Version control",
        completed=platform_info.git_installed,
        remediation="Install Git: https://git-scm.com/downloads",
    ))

    # Step 3: Ollama (for local models)
    steps.append(BootstrapStep(
        name="Ollama",
        description="Local LLM runtime",
        required=False,  # Can use gateway instead
        completed=platform_info.ollama_installed,
        remediation="Install Ollama: https://ollama.com/download",
    ))

    # Step 4: RAM check
    ram_ok = platform_info.ram_total_mb >= 8000
    steps.append(BootstrapStep(
        name="RAM >= 8GB",
        description="Minimum RAM for local models",
        required=False,
        completed=ram_ok,
        remediation=f"Current: {platform_info.ram_total_mb}MB. Recommend 16GB+.",
    ))

    # Step 5: Disk space
    disk_ok = platform_info.disk_free_gb >= 2.0
    steps.append(BootstrapStep(
        name="Disk >= 2GB free",
        description="Space for models and data",
        completed=disk_ok,
        remediation=f"Current: {platform_info.disk_free_gb:.1f}GB free. Need >= 2GB.",
    ))

    # Step 6: autocode CLI discoverability
    steps.append(BootstrapStep(
        name="AutoCode CLI",
        description="`autocode` command available on PATH",
        required=False,
        completed=is_autocode_on_path(),
        remediation=(
            "Install with `uv tool install --from . autocode` "
            "and ensure ~/.local/bin is on PATH"
        ),
    ))

    # Step 7: Recommended mode
    steps.append(BootstrapStep(
        name=f"Mode: {platform_info.recommended_mode}",
        description="Recommended operation mode",
        required=False,
        completed=True,
    ))

    result = BootstrapResult(
        steps=steps,
        platform=platform_info,
        ready=len([s for s in steps if s.required and not s.completed]) == 0,
    )
    return result
