from dataclasses import dataclass, field
import json
from pathlib import Path

CODEX_BASELINE = {
    "functionality": 0.615,    # 61.5% MindStudio 2025 (older Codex model)
    "swe_bench_verified": 0.32,
    # HarnessBench v2 (nyosegawa/harness-bench, 2026-05-04, 27 real-repo debugging tasks):
    "harnessbench_v2_codex_medium": 0.778,   # Codex gpt-5.5:medium  21/27
    "harnessbench_v2_codex_high":   0.704,   # Codex gpt-5.5:high    19/27
    "harnessbench_v2_codex_xhigh":  0.815,   # Codex gpt-5.5:xhigh   22/27 ← best
    "harnessbench_v2_claude_high":  0.741,   # Claude Opus 4.7:high  20/27
    "harnessbench_v2_claude_max":   0.630,   # Claude Opus 4.7:max   17/27
    "harnessbench_v2_claude48_xhigh": 0.560, # Claude Opus 4.8:xhigh 14/25 (2026-05-29)
    "harnessbench_v2_cursor_medium": 0.778,  # Cursor gpt-5.5:medium 21/27
    # Target to beat: Codex xhigh 81.5%
    # Maxxing at 3 variants: 1-(1-0.815)^3 = 93.6% theoretical
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