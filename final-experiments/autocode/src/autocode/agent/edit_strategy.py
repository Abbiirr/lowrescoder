"""Edit strategy abstraction — multiple edit formats per model capability.

Based on Aider's architecture: the edit format is chosen by model/task,
not hardcoded. Models that excel at structured output use editblock;
models that prefer whole-file output use wholefile; etc.

Strategies:
- editblock: search/replace blocks (default, most precise)
- wholefile: rewrite entire file (simple models)
- udiff: unified diff format (models trained on diffs)
- patch: git-style patch (for models that know git)
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EditRequest:
    """A request to edit a file."""

    file: str
    instruction: str
    current_content: str = ""


@dataclass
class EditResult:
    """Result of applying an edit."""

    file: str
    success: bool
    new_content: str = ""
    error: str = ""
    strategy_used: str = ""


class EditStrategy(ABC):
    """Base class for edit format strategies."""

    name: str = "base"

    @abstractmethod
    def format_prompt(self, request: EditRequest) -> str:
        """Format the edit instruction for the LLM."""
        ...

    @abstractmethod
    def parse_response(self, response: str, request: EditRequest) -> EditResult:
        """Parse the LLM response into an edit result."""
        ...


class EditBlockStrategy(EditStrategy):
    """Search/replace block format (Aider's default).

    LLM produces SEARCH/REPLACE blocks:
    <<<<<<< SEARCH
    old code
    =======
    new code
    >>>>>>> REPLACE
    """

    name = "editblock"

    def format_prompt(self, request: EditRequest) -> str:
        return (
            f"Edit the file `{request.file}` to: {request.instruction}\n\n"
            f"Current content:\n```\n{request.current_content}\n```\n\n"
            "Respond with SEARCH/REPLACE blocks:\n"
            "<<<<<<< SEARCH\n"
            "exact lines to find\n"
            "=======\n"
            "replacement lines\n"
            ">>>>>>> REPLACE"
        )

    def parse_response(self, response: str, request: EditRequest) -> EditResult:
        content = request.current_content
        # Parse SEARCH/REPLACE blocks
        pattern = r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE"
        matches = re.findall(pattern, response, re.DOTALL)

        if not matches:
            return EditResult(
                file=request.file, success=False,
                error="No SEARCH/REPLACE blocks found",
                strategy_used=self.name,
            )

        for search, replace in matches:
            if search in content:
                content = content.replace(search, replace, 1)
            else:
                return EditResult(
                    file=request.file, success=False,
                    error="SEARCH block not found in file",
                    strategy_used=self.name,
                )

        return EditResult(
            file=request.file, success=True,
            new_content=content, strategy_used=self.name,
        )


class WholeFileStrategy(EditStrategy):
    """Whole file rewrite (for simpler models).

    LLM produces the entire new file content.
    """

    name = "wholefile"

    def format_prompt(self, request: EditRequest) -> str:
        return (
            f"Rewrite the file `{request.file}` to: {request.instruction}\n\n"
            f"Current content:\n```\n{request.current_content}\n```\n\n"
            "Write the complete new file content inside a code block."
        )

    def parse_response(self, response: str, request: EditRequest) -> EditResult:
        # Extract code block
        match = re.search(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL)
        if match:
            content = match.group(1)
            return EditResult(
                file=request.file, success=True,
                new_content=content, strategy_used=self.name,
            )
        return EditResult(
            file=request.file, success=False,
            error="No code block found in response",
            strategy_used=self.name,
        )


class UDiffStrategy(EditStrategy):
    """Unified diff format (for models trained on diffs).

    LLM produces unified diff output.
    """

    name = "udiff"

    def format_prompt(self, request: EditRequest) -> str:
        return (
            f"Edit `{request.file}` to: {request.instruction}\n\n"
            f"Current content:\n```\n{request.current_content}\n```\n\n"
            "Respond with a unified diff (--- a/ +++ b/ format)."
        )

    def parse_response(self, response: str, request: EditRequest) -> EditResult:
        # Simple unified diff parser
        lines = request.current_content.splitlines(keepends=True)
        result_lines = list(lines)

        # Find diff hunks
        hunk_pattern = r"@@ -(\d+),?\d* \+\d+,?\d* @@"
        in_diff = False

        for line in response.splitlines():
            if line.startswith("@@"):
                in_diff = True
                match = re.match(hunk_pattern, line)
                if match:
                    pass  # Track position
            elif in_diff and line.startswith("-"):
                pass  # Remove line
            elif in_diff and line.startswith("+"):
                pass  # Add line

        # For now, fall back to editblock if diff parsing is incomplete
        return EditResult(
            file=request.file, success=False,
            error="Unified diff parsing not fully implemented — use editblock",
            strategy_used=self.name,
        )


# Strategy registry
STRATEGIES: dict[str, EditStrategy] = {
    "editblock": EditBlockStrategy(),
    "wholefile": WholeFileStrategy(),
    "udiff": UDiffStrategy(),
}

# Model → preferred strategy mapping
MODEL_STRATEGY_MAP: dict[str, str] = {
    "gpt-4": "editblock",
    "gpt-4o": "editblock",
    "claude": "editblock",
    "qwen": "wholefile",
    "deepseek": "editblock",
    "codestral": "editblock",
    "llama": "wholefile",
    "gemma": "wholefile",
}


def select_strategy(model_name: str = "", task_type: str = "") -> EditStrategy:
    """Select the best edit strategy for a model/task combination.

    Checks model name against known preferences, falls back to editblock.
    """
    model_lower = model_name.lower()
    for prefix, strategy_name in MODEL_STRATEGY_MAP.items():
        if prefix in model_lower:
            return STRATEGIES[strategy_name]

    # Default: editblock (most reliable)
    return STRATEGIES["editblock"]
