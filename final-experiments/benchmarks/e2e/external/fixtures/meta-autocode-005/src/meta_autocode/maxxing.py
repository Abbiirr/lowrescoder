"""Benchmark Maxxing - multi-variant strategy for meta-autocode.

This module implements a benchmark maxxing strategy that runs multiple variant
approaches per task and selects the best result based on score and resolution.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class VariantStrategy:
    """Strategy variant configuration for benchmark maxxing.
    
    Each variant has a name and additional prompt instructions that guide
    the agent toward a specific approach (test-first, minimal changes, direct implementation, etc.)
    """
    name: str
    prompt_suffix: str


@dataclass
class MaxxingResult:
    """Result from a single variant execution.
    
    Tracks which variant was used, the achieved score (0.0-1.0), whether the task
    was resolved, and the number of tool calls made.
    """
    variant: str
    score: float
    resolved: bool
    tool_calls: int


class BenchmarkMaxxer:
    """Multi-variant benchmark strategy that maximizes resolution probability.
    
    This strategy runs N variant approaches per task and returns the best result.
    The probability that at least one variant resolves is 1 - (1-p)^N, where p is
    the baseline resolution rate (e.g., 61.5% for Codex).
    """
    
    MAX_VARIANTS: int = 3
    
    def __init__(self, variants: Optional[list[VariantStrategy]] = None):
        """Initialize the benchmark maxxer with optional custom variants.
        
        Args:
            variants: List of VariantStrategy objects. If None, uses default variants.
        """
        if variants is None:
            self.variants = self._get_default_variants()
        else:
            self.variants = variants
    
    @staticmethod
    def pick_best(results: list[MaxxingResult]) -> MaxxingResult:
        """Select the best result from a list of variant results.
        
        Rules:
        1. Prefer resolved=True over resolved=False regardless of score
        2. Among resolved results, pick the highest score
        3. Among unresolved results, pick the highest score
        4. Raise ValueError if results list is empty
        
        Args:
            results: List of MaxxingResult objects from variant executions
            
        Returns:
            The best MaxxingResult according to the selection rules
            
        Raises:
            ValueError: If results list is empty
        """
        if not results:
            raise ValueError("Cannot pick best from empty results list")
        
        # Separate resolved and unresolved results
        resolved_results = [r for r in results if r.resolved]
        unresolved_results = [r for r in results if not r.resolved]
        
        # Prefer resolved over unresolved
        if resolved_results:
            # Among resolved, pick highest score
            return max(resolved_results, key=lambda r: r.score)
        elif unresolved_results:
            # Among unresolved, pick highest score
            return max(unresolved_results, key=lambda r: r.score)
        else:
            # This shouldn't happen due to the empty check above, but for safety
            raise ValueError("No valid results found")
    
    def simulate(self, results: list[MaxxingResult]) -> MaxxingResult:
        """Delegate to pick_best - integration point with PIV loop.
        
        This method acts as a wrapper around pick_best to provide a clean 
        interface for the PIV loop to select the best result.
        
        Args:
            results: List of MaxxingResult objects from variant executions
            
        Returns:
            The best MaxxingResult according to the selection rules
        """
        return self.pick_best(results)
    
    def _get_default_variants(self) -> list[VariantStrategy]:
        """Generate default variant strategies for benchmark maxxing.
        
        Returns:
            List of VariantStrategy objects covering different approach styles
        """
        return [
            VariantStrategy(
                name="tdd",
                prompt_suffix="Use test-driven development: write tests first, then implement code to pass them. Focus on edge cases and ensure comprehensive test coverage."
            ),
            VariantStrategy(
                name="minimal",
                prompt_suffix="Make minimal changes to resolve the task. Focus on simplicity and maintainability. Only modify what is necessary."
            ),
            VariantStrategy(
                name="direct",
                prompt_suffix="Implement the solution directly and efficiently. Focus on getting a working solution quickly with clean, straightforward code."
            ),
        ]