"""Recipe/workflow YAML loading and execution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class RecipeValidationError(ValueError):
    """Raised when a recipe YAML file is malformed."""


@dataclass(frozen=True)
class RecipeStep:
    """One recipe step."""

    prompt: str | None = None
    task: str | None = None
    subagent: str | None = None


@dataclass(frozen=True)
class Recipe:
    """Validated recipe definition."""

    name: str
    goal: str
    steps: tuple[RecipeStep, ...]
    path: Path


def bundled_recipe_dir() -> Path:
    """Return the package-local bundled recipe directory."""
    return Path(__file__).resolve().parent / "recipes"


class RecipeRegistry:
    """Discover and validate global, project-local, and bundled recipes."""

    def __init__(self, *, project_root: Path, home: Path | None = None) -> None:
        self.project_root = Path(project_root)
        self.home = Path(home).expanduser() if home is not None else Path.home()

    def list(self) -> list[Recipe]:
        recipes: dict[str, Recipe] = {}
        for directory in self._recipe_dirs():
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.yaml")):
                recipe = load_recipe(path)
                recipes[recipe.name] = recipe
        return [recipes[name] for name in sorted(recipes)]

    def get(self, name: str) -> Recipe:
        for recipe in self.list():
            if recipe.name == name:
                return recipe
        raise KeyError(name)

    def _recipe_dirs(self) -> tuple[Path, Path, Path]:
        return (
            bundled_recipe_dir(),
            self.home / ".autocode" / "recipes",
            self.project_root / ".autocode" / "recipes",
        )


def load_recipe(path: Path) -> Recipe:
    """Load and validate one YAML recipe."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RecipeValidationError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise RecipeValidationError(f"{path}: recipe must be a mapping")
    name = str(raw.get("name") or path.stem).strip()
    goal = str(raw.get("goal") or "").strip()
    raw_steps = raw.get("steps")
    if not name:
        raise RecipeValidationError(f"{path}: name is required")
    if not goal:
        raise RecipeValidationError(f"{path}: goal is required")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise RecipeValidationError(f"{path}: recipe must contain at least one step")
    steps = tuple(_load_step(path, step) for step in raw_steps)
    return Recipe(name=name, goal=goal, steps=steps, path=path)


def _load_step(path: Path, raw: Any) -> RecipeStep:
    if not isinstance(raw, dict):
        raise RecipeValidationError(f"{path}: each step must be a mapping")
    step = RecipeStep(
        prompt=_optional_str(raw.get("prompt")),
        task=_optional_str(raw.get("task")),
        subagent=_optional_str(raw.get("subagent")),
    )
    if not (step.prompt or step.task or step.subagent):
        raise RecipeValidationError(
            f"{path}: each step must include prompt, task, or subagent"
        )
    return step


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
