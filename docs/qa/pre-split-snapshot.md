# Pre-Split Snapshot — 2026-03-20

## File Counts
| Area | Files |
|------|-------|
| src/autocode/ | 130 |
| cmd/autocode-tui/ | 38 |
| scripts/ | 369 |
| tests/ | 178 |
| docs/ | 1411 |
| benchmarks/ | 15 |
| training_data/ | 19 |
| sandboxes/ | 2097 dirs |

## Test Baseline
- 1229 passed, 6 failed (5 adapter test drift + 1 integration), 8 skipped

## Pre-existing Test Failures
- test_openrouter_non_streaming (integration, provider)
- test_build_prompt_includes_source_candidates (adapter format drift)
- test_build_prompt_normal_uses_write_file (adapter format drift)
- test_build_feedback_prompt_repeated_failure_warning (adapter format drift)
- test_build_feedback_prompt_zero_diff_points_to_candidate_files (adapter format drift)
- test_is_docker_exec_infra_output (removed method)

## Benchmark Scores
- B7-B14: 39/40 (97.5%)
- B15-B29: 16/17 (94.1%)
- Combined: 55/57 (96.5%)
