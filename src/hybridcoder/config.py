"""Configuration system for HybridCoder.

Loads config with precedence: env vars > project YAML > global YAML > defaults.
Based on LLD Phase 3, Section 2.3.
"""

from __future__ import annotations

import os
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
        default="~/.hybridcoder/models/qwen2.5-coder-1.5b-q4_k_m.gguf",
        description="Path to L3 GGUF model file",
    )
    grammar_constrained: bool = True


class Layer1Config(BaseModel):
    """Layer 1 deterministic analysis config."""

    enabled: bool = True
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")


class Layer2Config(BaseModel):
    """Layer 2 retrieval and context config."""

    enabled: bool = True
    embedding_model: str = Field(default="jinaai/jina-embeddings-v2-base-code")
    search_top_k: int = Field(default=10, ge=1)
    chunk_size: int = Field(default=1000, gt=0)
    hybrid_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="BM25 vs vector weight")


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
    session_db_path: str = "~/.hybridcoder/sessions.db"
    max_iterations: int = 10
    show_tool_calls: bool = True
    alternate_screen: bool = False


# --- Top-level config ---


class HybridCoderConfig(BaseModel):
    """Top-level HybridCoder configuration."""

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


# --- Config loading ---

_GLOBAL_CONFIG_DIR = Path.home() / ".hybridcoder"
_GLOBAL_CONFIG_FILE = _GLOBAL_CONFIG_DIR / "config.yaml"
_PROJECT_CONFIG_FILE = ".hybridcoder.yaml"


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


def _apply_env_overrides(data: dict[str, object]) -> dict[str, object]:
    """Apply environment variable overrides.

    Env vars follow pattern: HYBRIDCODER_<SECTION>_<KEY>
    Example: HYBRIDCODER_LLM_PROVIDER=openrouter
    """
    env_map: dict[str, tuple[str, str]] = {
        "HYBRIDCODER_LLM_PROVIDER": ("llm", "provider"),
        "HYBRIDCODER_LLM_MODEL": ("llm", "model"),
        "HYBRIDCODER_LLM_API_BASE": ("llm", "api_base"),
        "HYBRIDCODER_LLM_TEMPERATURE": ("llm", "temperature"),
        "HYBRIDCODER_LLM_MAX_TOKENS": ("llm", "max_tokens"),
        "HYBRIDCODER_UI_VERBOSE": ("ui", "verbose"),
    }

    for env_var, (section, key) in env_map.items():
        value = os.environ.get(env_var)
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
    provider_env = os.environ.get("HYBRIDCODER_LLM_PROVIDER")

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
    provider_env = os.environ.get("HYBRIDCODER_LLM_PROVIDER")

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


def load_config(
    project_root: Path | None = None,
) -> HybridCoderConfig:
    """Load config with full precedence chain.

    Priority: env vars > project YAML > global YAML > defaults
    """
    # 1. Start with empty (defaults come from Pydantic)
    data: dict[str, object] = {}

    # 2. Global YAML
    global_data = _load_yaml(_GLOBAL_CONFIG_FILE)
    data = _deep_merge(data, global_data)

    # 3. Project YAML
    root = project_root or Path.cwd()
    project_data = _load_yaml(root / _PROJECT_CONFIG_FILE)
    data = _deep_merge(data, project_data)

    # 4. Environment variable overrides
    data = _apply_env_overrides(data)
    data = _apply_ollama_env(data)
    data = _apply_openrouter_env(data)

    config = HybridCoderConfig.model_validate(data)

    # Fix #5: If provider is openrouter but api_base is still the Ollama default,
    # auto-correct to OpenRouter base URL
    ollama_default = "http://localhost:11434"
    if config.llm.provider == "openrouter" and config.llm.api_base == ollama_default:
        config.llm.api_base = "https://openrouter.ai/api/v1"

    return config


def save_config(config: HybridCoderConfig, path: Path | None = None) -> Path:
    """Save config to YAML file. Defaults to global config."""
    target = path or _GLOBAL_CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)
    return target


def get_config_path() -> Path:
    """Return path to global config file."""
    return _GLOBAL_CONFIG_FILE


def check_config(config: HybridCoderConfig) -> list[str]:
    """Validate config and return list of warnings/issues."""
    warnings: list[str] = []

    if config.llm.provider == "ollama":
        # Check if Ollama is likely reachable
        if not config.llm.api_base.startswith("http"):
            warnings.append(f"Ollama api_base doesn't look like a URL: {config.llm.api_base}")

    if config.llm.provider == "openrouter":
        if not os.environ.get("OPENROUTER_API_KEY"):
            warnings.append("OpenRouter selected but OPENROUTER_API_KEY not set")

    if config.layer3.enabled:
        model_path = Path(config.layer3.model_path).expanduser()
        if not model_path.exists():
            warnings.append(f"L3 model not found: {model_path}")

    return warnings
