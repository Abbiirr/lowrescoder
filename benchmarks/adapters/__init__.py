"""Agent adapters for unified benchmark runner.

Each adapter wraps an agentic coding tool so it can be driven by the
unified benchmark harness with identical prompts, budgets, and grading.
"""

from __future__ import annotations

from .base import AgentAdapter, AgentResult, BenchmarkTask, BudgetProfile

__all__ = ["AgentAdapter", "AgentResult", "BenchmarkTask", "BudgetProfile"]
