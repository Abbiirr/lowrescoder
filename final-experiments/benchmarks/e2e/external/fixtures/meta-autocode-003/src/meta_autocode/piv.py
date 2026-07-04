from dataclasses import dataclass, field
from typing import Any


@dataclass
class PIVPlan:
    task_description: str
    files_to_read: list[str] = field(default_factory=list)
    changes_needed: list[dict[str, str]] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    verify_command: str = "./verify.sh"


@dataclass
class PIVResult:
    phase: str   # "plan", "implement", or "validate"
    success: bool
    tool_calls_used: int
    error_output: str = ""
    iterations: int = 1


class EnhancedPIVStrategy:
    MAX_ITERATIONS = 3

    def describe(self) -> str:
        return (
            "The EnhancedPIVStrategy implements a robust Plan-Implement-Validate loop that "
            "systematically approaches coding tasks by first creating a detailed plan (PLAN), "
            "then executing the necessary code changes (IMPLEMENT), and finally validating the "
            "results against tests and requirements (VALIDATE). This iterative process allows "
            "the agent to handle complex tasks efficiently, detect failures early, and ensure "
            "high-quality outcomes. The loop is designed to maximize success rate while "
            "minimizing unnecessary tool calls through intelligent retry logic and verification."
        )

    def get_overlay(self) -> dict[str, Any]:
        return {
            "max_edit_retries": 3,
            "additional_prompt_guidance": (
                "Always validate your changes against the test suite. If tests fail, analyze "
                "the failure pattern and adjust your approach accordingly. Remember to check "
                "edge cases and ensure backward compatibility."
            ),
            "require_verifier_signal_before_retry": True,
        }