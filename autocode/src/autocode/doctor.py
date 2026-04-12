"""AutoCode doctor — system readiness checks with remediation messages.

Usage: autocode doctor
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    """Result of a single readiness check."""

    name: str
    passed: bool
    message: str
    remediation: str = ""


def check_python_version() -> CheckResult:
    """Check 1: Python version >= 3.11."""
    version = sys.version_info
    passed = version >= (3, 11)
    msg = f"Python {version.major}.{version.minor}.{version.micro}"
    return CheckResult(
        name="python_version",
        passed=passed,
        message=msg,
        remediation="" if passed else "Install Python 3.11+: https://python.org/downloads/",
    )


def _get_llm_backend() -> tuple[str, str]:
    """Resolve the active LLM backend from config/env.

    Returns (provider, api_base) based on resolved config.
    """
    import os

    provider = os.environ.get("AUTOCODE_LLM_PROVIDER", "ollama")
    api_base = os.environ.get("AUTOCODE_LLM_API_BASE", "")
    if not api_base:
        try:
            from autocode.config import load_config

            config = load_config()
            provider = config.llm.provider
            api_base = getattr(config.llm, "api_base", "")
        except Exception:
            pass
    return provider, api_base


def check_llm_backend() -> CheckResult:
    """Check 2: LLM backend reachable (gateway or Ollama)."""
    import os

    provider, api_base = _get_llm_backend()

    # If using a gateway (openrouter provider with custom API base)
    if api_base and "localhost" in api_base:
        try:
            import urllib.request

            from autocode.gateway_auth import build_gateway_headers

            url = f"{api_base.rstrip('/')}/models"
            req = urllib.request.Request(url, headers=build_gateway_headers())
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return CheckResult(
                        name="llm_backend",
                        passed=True,
                        message=f"LLM gateway reachable at {api_base}",
                    )
        except Exception as e:
            return CheckResult(
                name="llm_backend",
                passed=False,
                message=f"LLM gateway not reachable: {e}",
                remediation=f"Start the gateway or check {api_base}",
            )

    # Direct Ollama
    if not shutil.which("ollama"):
        return CheckResult(
            name="llm_backend",
            passed=False,
            message="No LLM backend configured (no gateway, no Ollama)",
            remediation=(
                "Install Ollama (https://ollama.com/download) "
                "or configure a gateway via AUTOCODE_LLM_API_BASE"
            ),
        )
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return CheckResult(
            name="llm_backend",
            passed=result.returncode == 0,
            message=result.stdout.strip() or "Ollama found",
        )
    except Exception as e:
        return CheckResult(
            name="llm_backend",
            passed=False,
            message=f"Ollama error: {e}",
            remediation="Install Ollama: https://ollama.com/download",
        )


def check_l4_model() -> CheckResult:
    """Check 3: L4 model available (via gateway or Ollama)."""
    import os

    provider, api_base = _get_llm_backend()

    # If using gateway, check if model aliases respond
    if api_base and "localhost" in api_base:
        try:
            import json
            import urllib.request

            from autocode.gateway_auth import build_gateway_headers

            model = os.environ.get("AUTOCODE_MODEL", os.environ.get("OPENROUTER_MODEL", "coding"))
            data = json.dumps(
                {
                    "model": model,
                    "messages": [{"role": "user", "content": "ok"}],
                    "max_tokens": 1,
                }
            ).encode()
            req = urllib.request.Request(
                f"{api_base.rstrip('/')}/chat/completions",
                data=data,
                headers=build_gateway_headers({"Content-Type": "application/json"}),
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return CheckResult(
                        name="l4_model",
                        passed=True,
                        message=f"Model '{model}' responding via gateway",
                    )
        except Exception as e:
            return CheckResult(
                name="l4_model",
                passed=False,
                message=f"Gateway model check failed: {e}",
                remediation=f"Verify gateway at {api_base} and model alias",
            )

    # Direct Ollama
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return CheckResult(
                name="l4_model",
                passed=False,
                message="Could not list Ollama models",
                remediation="Run: ollama pull qwen3:8b",
            )
        models = result.stdout.lower()
        has_model = any(m in models for m in ("qwen3", "qwen2.5", "llama", "codestral"))
        return CheckResult(
            name="l4_model",
            passed=has_model,
            message="L4 model available" if has_model else "No suitable L4 model found",
            remediation="" if has_model else "Run: ollama pull qwen3:8b",
        )
    except Exception:
        return CheckResult(
            name="l4_model",
            passed=False,
            message="Ollama not reachable",
            remediation="Start Ollama: ollama serve",
        )


def check_retrieval_tier() -> CheckResult:
    """Check 4: Retrieval tier (BM25-only, hybrid, or persistent)."""
    try:
        from autocode.layer2.embeddings import (
            RETRIEVAL_TIER_DESCRIPTIONS,
            check_retrieval_tier,
        )

        tier = check_retrieval_tier()
        desc = RETRIEVAL_TIER_DESCRIPTIONS.get(tier, str(tier))
        return CheckResult(
            name="retrieval_tier",
            passed=True,
            message=f"{tier.value}: {desc}",
            remediation="",
        )
    except ImportError:
        return CheckResult(
            name="retrieval_tier",
            passed=False,
            message="Retrieval tier module not available",
            remediation="Check autocode installation",
        )


def check_tree_sitter() -> CheckResult:
    """Check 5: tree-sitter grammars loaded."""
    try:
        import tree_sitter  # noqa: F401
        import tree_sitter_python  # noqa: F401

        return CheckResult(
            name="tree_sitter",
            passed=True,
            message="tree-sitter + Python grammar available",
        )
    except ImportError as e:
        return CheckResult(
            name="tree_sitter",
            passed=False,
            message=f"tree-sitter error: {e}",
            remediation="Run: uv pip install tree-sitter tree-sitter-python",
        )


def check_git() -> CheckResult:
    """Check 6: Git available and project is git repo."""
    if not shutil.which("git"):
        return CheckResult(
            name="git",
            passed=False,
            message="Git not found on PATH",
            remediation="Install Git: https://git-scm.com/downloads",
        )
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        in_repo = result.returncode == 0
        return CheckResult(
            name="git",
            passed=in_repo,
            message="Git available, in a git repo"
            if in_repo
            else "Git available, not in a git repo",
            remediation="" if in_repo else "Run: git init",
        )
    except Exception as e:
        return CheckResult(
            name="git",
            passed=False,
            message=f"Git error: {e}",
        )


def check_autocode_command() -> CheckResult:
    """Check 7: autocode command is discoverable on PATH."""
    from autocode.packaging.installer import is_autocode_on_path

    if is_autocode_on_path():
        return CheckResult(
            name="autocode_command",
            passed=True,
            message="autocode command available on PATH",
        )

    return CheckResult(
        name="autocode_command",
        passed=False,
        message="autocode command not found on PATH",
        remediation=(
            "Install with: uv tool install --from . autocode and ensure ~/.local/bin is on PATH"
        ),
    )


def check_vram() -> CheckResult:
    """Check 8: VRAM sufficient (>= 6GB free)."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            free_mb = int(result.stdout.strip().split("\n")[0])
            passed = free_mb >= 6000
            return CheckResult(
                name="vram",
                passed=passed,
                message=f"VRAM free: {free_mb} MB",
                remediation="" if passed else "Close GPU-heavy applications to free VRAM",
            )
    except Exception:
        pass
    return CheckResult(
        name="vram",
        passed=True,
        message="No NVIDIA GPU detected (CPU mode OK)",
    )


def check_disk_space() -> CheckResult:
    """Check 9: Disk space sufficient (>= 2GB free)."""
    try:
        import shutil as sh

        usage = sh.disk_usage(Path.cwd())
        free_gb = usage.free / (1024**3)
        passed = free_gb >= 2.0
        return CheckResult(
            name="disk_space",
            passed=passed,
            message=f"Disk free: {free_gb:.1f} GB",
            remediation="" if passed else "Free up disk space (need >= 2 GB)",
        )
    except Exception as e:
        return CheckResult(
            name="disk_space",
            passed=False,
            message=f"Could not check disk: {e}",
        )


ALL_CHECKS = [
    check_python_version,
    check_llm_backend,
    check_l4_model,
    check_retrieval_tier,
    check_tree_sitter,
    check_git,
    check_autocode_command,
    check_vram,
    check_disk_space,
]


def run_doctor() -> list[CheckResult]:
    """Run all 8 readiness checks and return results."""
    return [check() for check in ALL_CHECKS]


def format_report(results: list[CheckResult]) -> str:
    """Format check results as a human-readable report."""
    lines = ["AutoCode Doctor — System Readiness Report", "=" * 45]
    passed = sum(1 for r in results if r.passed)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"  [{status}] {r.name}: {r.message}")
        if not r.passed and r.remediation:
            lines.append(f"         Fix: {r.remediation}")
    lines.append(f"\n{passed}/{len(results)} checks passed")
    return "\n".join(lines)


def doctor_json(results: list[CheckResult]) -> list[dict[str, object]]:
    """Return results as JSON-serializable list."""
    return [
        {
            "name": r.name,
            "passed": r.passed,
            "message": r.message,
            "remediation": r.remediation,
        }
        for r in results
    ]
