from dataclasses import dataclass, field
import json
from pathlib import Path

CODEX_BASELINE = {
    "functionality": 0.615,   # 61.5% from MindStudio harness benchmark 2025
    "swe_bench_verified": 0.32,
}


@dataclass
class BenchmarkScore:
    task_id: str
    resolved: bool
    tool_calls: int
    wall_time_s: float
    piv_iterations: int = 1
    failure_type: str = ""


@dataclass
class SessionScores:
    scores: list[BenchmarkScore] = field(default_factory=list)

    @property
    def resolve_rate(self) -> float:
        if not self.scores:
            return 0.0
        resolved_count = sum(1 for s in self.scores if s.resolved)
        return resolved_count / len(self.scores)

    @property
    def avg_tool_calls(self) -> float:
        resolved_scores = [s for s in self.scores if s.resolved]
        if not resolved_scores:
            return 0.0
        return sum(s.tool_calls for s in resolved_scores) / len(resolved_scores)

    def vs_codex(self) -> dict[str, float]:
        meta_rate = self.resolve_rate
        codex_rate = CODEX_BASELINE["functionality"]
        delta = meta_rate - codex_rate
        beats_codex = delta > 0
        return {
            "meta_autocode_rate": meta_rate,
            "codex_baseline": codex_rate,
            "delta": delta,
            "beats_codex": beats_codex,
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({
            "resolve_rate": self.resolve_rate,
            "avg_tool_calls": self.avg_tool_calls,
            "vs_codex": self.vs_codex(),
            "tasks": [vars(s) for s in self.scores],
        }, indent=2))