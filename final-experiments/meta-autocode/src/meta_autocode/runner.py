"""MetaAutocodeRunner - Integration layer for meta-autocode Phase 4.

This module wires together:
- ProgressiveContextLoader (ranks files by query relevance)
- BenchmarkMaxxer (multi-variant strategy with best-result selection)

Into a single pipeline that simulates task resolution with scored results.
"""
from dataclasses import dataclass
from typing import Optional
from time import time

from meta_autocode.context import ProgressiveContextLoader
from meta_autocode.maxxing import BenchmarkMaxxer, MaxxingResult


@dataclass
class RunResult:
    """Result of a MetaAutocodeRunner simulation.
    
    Tracks the outcome of simulating a task resolution, including which
    strategy variant was most effective and contextual information.
    
    Fields:
    - task_id: Identifier for the task being simulated
    - resolved: Whether the task was resolved (True if files were ranked)
    - score: Quality score (0.0-1.0) based on context quality
    - tool_calls: Number of tool interactions (varies by variant)
    - variant_used: Name of the selected strategy variant
    - wall_time_s: Wall-clock time taken for the simulation
    - context_top_file: Path to the top-ranked file (None if no files)
    """
    task_id: str
    resolved: bool
    score: float
    tool_calls: int
    variant_used: str
    wall_time_s: float
    context_top_file: Optional[str] = None


class MetaAutocodeRunner:
    """Integration layer that wires together all meta-autocode components.
    
    This runner:
    1. Ranks files by query relevance using ProgressiveContextLoader
    2. Simulates multiple strategy variants using BenchmarkMaxxer
    3. Selects the best variant result
    4. Returns a comprehensive RunResult with all tracking data
    
    The class exposes either context_loader or maxxer (or both) as attributes.
    """
    
    def __init__(self):
        """Initialize the MetaAutocodeRunner with internal components.
        
        Creates a BenchmarkMaxxer instance with default variants and
        prepares the context loader factory.
        """
        self._maxxer = BenchmarkMaxxer()
        self._context_loader_factory = ProgressiveContextLoader
    
    @property
    def maxxer(self) -> BenchmarkMaxxer:
        """Expose the BenchmarkMaxxer instance."""
        return self._maxxer
    
    @property
    def context_loader(self) -> type[ProgressiveContextLoader]:
        """Expose the ProgressiveContextLoader class."""
        return self._context_loader_factory
    
    def simulate(self, task_id: str, files: dict[str, str], query: str) -> RunResult:
        """Simulate task resolution by running the full meta-autocode pipeline.
        
        Steps:
        1. Rank files by query relevance using ProgressiveContextLoader.rank()
        2. Create mock MaxxingResult for each variant
        3. Select the best variant using BenchmarkMaxxer.pick_best()
        4. Return comprehensive RunResult with all tracking data
        
        Args:
            task_id: Unique identifier for the task
            files: Dictionary mapping file paths to their contents
            query: Query/intent description for the task
            
        Returns:
            RunResult containing the simulation outcome and tracking data
        """
        start_time = time()
        
        # Step 1: Rank files by query relevance
        ranked_entries = self._context_loader_factory(files).rank(query)
        context_top_file = ranked_entries[0].path if ranked_entries else None
        
        # Step 2: Create mock MaxxingResult for each variant
        maxxing_results = []
        for i, variant in enumerate(self._maxxer.variants):
            # Mock score based on context quality
            score = min(1.0, len(ranked_entries) * 0.15) if ranked_entries else 0.0
            
            # Mock resolved status - True if there are ranked files
            resolved = len(ranked_entries) > 0
            
            # Mock tool calls - vary by variant index
            tool_calls = 5 + i * 3
            
            result = MaxxingResult(
                variant=variant.name,
                score=score,
                resolved=resolved,
                tool_calls=tool_calls
            )
            maxxing_results.append(result)
        
        # Step 3: Select the best variant
        best_result = self._maxxer.pick_best(maxxing_results)
        
        # Step 4: Calculate wall time
        wall_time_s = time() - start_time
        
        # Step 5: Return comprehensive RunResult
        return RunResult(
            task_id=task_id,
            resolved=best_result.resolved,
            score=best_result.score,
            tool_calls=best_result.tool_calls,
            variant_used=best_result.variant,
            wall_time_s=wall_time_s,
            context_top_file=context_top_file
        )