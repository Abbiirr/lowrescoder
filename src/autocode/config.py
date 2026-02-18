"""Configuration system for AutoCode.

Loads config with precedence: env vars > project YAML > global YAML > defaults.
Based on LLD Phase 3, Section 2.3.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env EARLY — before any config parsing so env vars participate in precedence
load_dotenv()


# --- Sub-config models ---


class LLMConfig(BaseModel):
    """Layer 4 LLM backend configuration."""

    provider: Literal["ollama", "openrouter"] = Field(
        default="ollama", description="L4 backend (local-first default)"
    )
    model: str = Field(default="qwen3:8b", description="L4 model name")
    api_base: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    context_length: int = Field(default=8192, gt=0, description="Max context window")
    reasoning_enabled: bool = Field(default=True, description="Enable thinking/reasoning tokens")


class Layer3Config(BaseModel):
    """Layer 3 constrained generation config (llama-cpp-python + Outlines)."""

    enabled: bool = True
    model_path: str = Field(
        default="~/.autocode/models/qwen2.5-coder-1.5b-q4_k_m.gguf",
        description="Path to L3 GGUF model file",
    )
    grammar_constrained: bool = True


class Layer1Config(BaseModel):
    """Layer 1 deterministic analysis config."""

    enabled: bool = True
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")
    cache_max_entries: int = Field(default=500, ge=1, description="Max LRU cache entries")


class Layer2Config(BaseModel):
    """Layer 2 retrieval and context config."""

    enabled: bool = True
    embedding_model: str = Field(default="jinaai/jina-embeddings-v2-base-code")
    search_top_k: int = Field(default=10, ge=1)
    chunk_size: int = Field(default=1000, gt=0)
    hybrid_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="BM25 vs vector weight")
    db_path: str = Field(default="~/.autocode/index.lancedb", description="LanceDB index path")
    relevance_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    max_files: int = Field(default=50000, ge=1, description="Max files to index")
    repomap_budget: int = Field(default=600, ge=1, description="Repo map token budget")
    context_budget: int = Field(default=5000, ge=1, description="Total context token budget")


class Layer4Config(BaseModel):
    """Layer 4 agentic workflow config."""

    enabled: bool = True
    max_retries: int = Field(default=3, ge=0)


class EditConfig(BaseModel):
    """Edit system configuration."""

    format: Literal["whole_file", "search_replace"] = "whole_file"
    fuzzy_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    auto_commit: bool = True


class GitConfig(BaseModel):
    """Git integration configuration."""

    auto_commit: bool = True
    commit_prefix: str = "[AI]"


class ShellConfig(BaseModel):
    """Sandboxed shell execution configuration."""

    enabled: bool = False
    timeout: int = Field(default=30, ge=1)
    max_timeout: int = Field(default=300, ge=1)
    allowed_commands: list[str] = Field(
        default=["pytest", "python", "pip", "uv", "git", "ruff", "mypy"]
    )
    blocked_commands: list[str] = Field(default=["rm -rf", "sudo", "curl", "wget"])
    allow_network: bool = False


class UIConfig(BaseModel):
    """CLI UI configuration."""

    theme: Literal["dark", "light", "auto"] = "dark"
    show_diff: bool = True
    confirm_edits: bool = True
    stream_output: bool = True
    verbose: bool = False


class TUIConfig(BaseModel):
    """Textual TUI configuration."""

    approval_mode: Literal["read-only", "suggest", "auto"] = "suggest"
    session_db_path: str = "~/.autocode/sessions.db"
    max_iterations: int = 10
    show_tool_calls: bool = True
    alternate_screen: bool = False


class TrainingLogConfig(BaseModel):
    """Training-grade event logging for dataset generation."""

    enabled: bool = False  # Opt-in only
    blob_dir: str = "blobs"  # Relative to log_dir
    blob_min_size: int = Field(default=1024, ge=0, description="Min bytes to externalize to blob")
    max_episodes_per_session: int = Field(default=200, ge=10)


class LoggingConfig(BaseModel):
    """Logging and observability configuration."""

    console_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "WARNING"
    file_enabled: bool = True
    file_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"
    log_dir: str = "logs"
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    max_files: int = Field(default=5, ge=1, le=50)
    debug_prompts: bool = False
    training: TrainingLogConfig = Field(default_factory=TrainingLogConfig)


class AgentConfig(BaseModel):
    """Agent orchestration configuration (Phase 4)."""

    compaction_threshold: float = Field(default=0.75, ge=0.5, le=0.95)
    compaction_kept_messages: int = Field(default=4, ge=1)
    tool_result_max_tokens: int = Field(default=500, ge=50)
    max_subagents: int = Field(default=3, ge=1)  # Sprint 4B
    subagent_max_iterations: int = Field(default=5, ge=1)  # Sprint 4B
    subagent_timeout_seconds: int = Field(default=30, ge=5)  # Sprint 4B
    memory_max_entries: int = Field(default=50, ge=10)  # Sprint 4C
    memory_decay_factor: float = Field(default=0.95, ge=0.5, le=1.0)  # Sprint 4C
    memory_context_max_tokens: int = Field(default=500, ge=50)  # Sprint 4C


# --- Top-level config ---


class AutoCodeConfig(BaseModel):
    """Top-level AutoCode configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    layer1: Layer1Config = Field(default_factory=Layer1Config)
    layer2: Layer2Config = Field(default_factory=Layer2Config)
    layer3: Layer3Config = Field(default_factory=Layer3Config)
    layer4: Layer4Config = Field(default_factory=Layer4Config)
    edit: EditConfig = Field(default_factory=EditConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    shell: ShellConfig = Field(default_factory=ShellConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    tui: TUIConfig = Field(default_factory=TUIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)


# Backward-compat alias
HybridCoderConfig = AutoCodeConfig


# --- Config loading ---

_GLOBAL_CONFIG_DIR = Path.home() / ".autocode"
_GLOBAL_CONFIG_FILE = _GLOBAL_CONFIG_DIR / "config.yaml"
_PROJECT_CONFIG_FILE = ".autocode.yaml"

# Legacy paths for backward compatibility
_LEGACY_CONFIG_DIR = Path.home() / ".hybridcoder"
_LEGACY_CONFIG_FILE = _LEGACY_CONFIG_DIR / "config.yaml"
_LEGACY_PROJECT_CONFIG_FILE = ".hybridcoder.yaml"


def _load_yaml(path: Path) -> dict[str, object]:
    """Load a YAML file, returning empty dict if missing."""
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    return {}


def _deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    """Recursively merge override into base (override wins)."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = value
    return result


def _get_legacy_env(new_name: str, legacy_name: str) -> str | None:
    """Check new env var first, fall back to legacy with deprecation warning."""
    value = os.environ.get(new_name)
    if value is not None:
        return value
    legacy_value = os.environ.get(legacy_name)
    if legacy_value is not None:
        warnings.warn(
            f"Environment variable {legacy_name} is deprecated, use {new_name} instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return legacy_value
    return None


def _apply_env_overrides(data: dict[str, object]) -> dict[str, object]:
    """Apply environment variable overrides.

    Env vars follow pattern: AUTOCODE_<SECTION>_<KEY>
    Example: AUTOCODE_LLM_PROVIDER=openrouter

    Legacy HYBRIDCODER_* env vars are supported with deprecation warning.
    """
    env_map: dict[tuple[str, str], tuple[str, str]] = {
        ("AUTOCODE_LLM_PROVIDER", "HYBRIDCODER_LLM_PROVIDER"): ("llm", "provider"),
        ("AUTOCODE_LLM_MODEL", "HYBRIDCODER_LLM_MODEL"): ("llm", "model"),
        ("AUTOCODE_LLM_API_BASE", "HYBRIDCODER_LLM_API_BASE"): ("llm", "api_base"),
        ("AUTOCODE_LLM_TEMPERATURE", "HYBRIDCODER_LLM_TEMPERATURE"): ("llm", "temperature"),
        ("AUTOCODE_LLM_MAX_TOKENS", "HYBRIDCODER_LLM_MAX_TOKENS"): ("llm", "max_tokens"),
        ("AUTOCODE_UI_VERBOSE", "HYBRIDCODER_UI_VERBOSE"): ("ui", "verbose"),
        ("AUTOCODE_LOG_LEVEL", "HYBRIDCODER_LOG_LEVEL"): ("logging", "console_level"),
        ("AUTOCODE_LOG_DEBUG_PROMPTS", "HYBRIDCODER_LOG_DEBUG_PROMPTS"): (
            "logging",
            "debug_prompts",
        ),
    }

    for (new_var, legacy_var), (section, key) in env_map.items():
        value = _get_legacy_env(new_var, legacy_var)
        if value is not None:
            if section not in data:
                data[section] = {}
            section_dict = data[section]
            if isinstance(section_dict, dict):
                section_dict[key] = value

    return data


def _apply_ollama_env(data: dict[str, object]) -> dict[str, object]:
    """Apply OLLAMA_HOST and OLLAMA_MODEL env vars when provider is ollama."""
    host = os.environ.get("OLLAMA_HOST")
    model = os.environ.get("OLLAMA_MODEL")
    provider_env = _get_legacy_env("AUTOCODE_LLM_PROVIDER", "HYBRIDCODER_LLM_PROVIDER")

    llm = data.get("llm")
    if not isinstance(llm, dict):
        llm = {}
        data["llm"] = llm

    provider = llm.get("provider", provider_env or "ollama")
    if provider == "ollama":
        if host:
            llm["api_base"] = host
        if model:
            llm["model"] = model

    return data


def _apply_openrouter_env(data: dict[str, object]) -> dict[str, object]:
    """If OpenRouter env vars are set and no explicit provider override, configure OpenRouter."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL")
    provider_env = _get_legacy_env("AUTOCODE_LLM_PROVIDER", "HYBRIDCODER_LLM_PROVIDER")

    # Only auto-configure OpenRouter if explicitly opted in via env
    if provider_env == "openrouter" and api_key:
        if "llm" not in data:
            data["llm"] = {}
        llm = data["llm"]
        if isinstance(llm, dict):
            llm["provider"] = "openrouter"
            # Only set api_base if user hasn't specified a custom one
            if "api_base" not in llm or llm["api_base"] == "http://localhost:11434":
                llm["api_base"] = "https://openrouter.ai/api/v1"
            if model:
                llm["model"] = model

    return data


def _resolve_global_config() -> tuple[Path, Path]:
    """Resolve global config dir and file, with legacy fallback.

    Returns (config_dir, config_file). Uses ~/.autocode/ if it exists,
    falls back to ~/.hybridcoder/ with deprecation warning.
    """
    if _GLOBAL_CONFIG_DIR.exists():
        return _GLOBAL_CONFIG_DIR, _GLOBAL_CONFIG_FILE
    if _LEGACY_CONFIG_DIR.exists():
        warnings.warn(
            f"Using legacy config directory {_LEGACY_CONFIG_DIR}. "
            f"Please rename to {_GLOBAL_CONFIG_DIR}.",
            DeprecationWarning,
            stacklevel=3,
        )
        return _LEGACY_CONFIG_DIR, _LEGACY_CONFIG_FILE
    # Neither exists — use new path (will be created on first save)
    return _GLOBAL_CONFIG_DIR, _GLOBAL_CONFIG_FILE


def _resolve_project_config(root: Path) -> Path:
    """Resolve project config file, with legacy fallback."""
    new_path = root / _PROJECT_CONFIG_FILE
    if new_path.exists():
        return new_path
    legacy_path = root / _LEGACY_PROJECT_CONFIG_FILE
    if legacy_path.exists():
        warnings.warn(
            f"Using legacy project config {legacy_path}. "
            f"Please rename to {new_path}.",
            DeprecationWarning,
            stacklevel=3,
        )
        return legacy_path
    return new_path


def load_config(
    project_root: Path | None = None,
) -> AutoCodeConfig:
    """Load config with full precedence chain.

    Priority: env vars > project YAML > global YAML > defaults
    """
    # 1. Start with empty (defaults come from Pydantic)
    data: dict[str, object] = {}

    # 2. Global YAML (with legacy fallback)
    _config_dir, config_file = _resolve_global_config()
    global_data = _load_yaml(config_file)
    data = _deep_merge(data, global_data)

    # 3. Project YAML (with legacy fallback)
    root = project_root or Path.cwd()
    project_config = _resolve_project_config(root)
    project_data = _load_yaml(project_config)
    data = _deep_merge(data, project_data)

    # 4. Environment variable overrides
    data = _apply_env_overrides(data)
    data = _apply_ollama_env(data)
    data = _apply_openrouter_env(data)

    config = AutoCodeConfig.model_validate(data)

    # Fix #5: If provider is openrouter but api_base is still the Ollama default,
    # auto-correct to OpenRouter base URL
    ollama_default = "http://localhost:11434"
    if config.llm.provider == "openrouter" and config.llm.api_base == ollama_default:
        config.llm.api_base = "https://openrouter.ai/api/v1"

    return config


def save_config(config: AutoCodeConfig, path: Path | None = None) -> Path:
    """Save config to YAML file. Defaults to global config."""
    target = path or _GLOBAL_CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)
    return target


def get_config_path() -> Path:
    """Return path to global config file."""
    return _GLOBAL_CONFIG_FILE


def check_config(config: AutoCodeConfig) -> list[str]:
    """Validate config and return list of warnings/issues."""
    warnings_list: list[str] = []

    if config.llm.provider == "ollama":
        # Check if Ollama is likely reachable
        if not config.llm.api_base.startswith("http"):
            warnings_list.append(
                f"Ollama api_base doesn't look like a URL: {config.llm.api_base}"
            )

    if config.llm.provider == "openrouter":
        if not os.environ.get("OPENROUTER_API_KEY"):
            warnings_list.append("OpenRouter selected but OPENROUTER_API_KEY not set")

    if config.layer3.enabled:
        model_path = Path(config.layer3.model_path).expanduser()
        if not model_path.exists():
            warnings_list.append(f"L3 model not found: {model_path}")

    return warnings_list
