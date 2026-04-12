# Manual AI Bug Test Report Template

Last updated: 2026-04-11
Purpose: strict PASS/FAIL artifact template for every manual AI verification run.

## Usage

1. Copy this file into `docs/qa/test-results/` or `autocode/docs/qa/test-results/`.
2. Name it with the date and scope, for example:
   - `20260411-go-tui-slash-provider-manual.md`
   - `20260411-inline-repo-grounding-manual.md`
3. Fill every required field.
4. Mark every scenario `PASS`, `FAIL`, `PARTIAL`, or `N/A`.
5. If any scenario is `FAIL`, include a blocker section and do not call the work complete.

## Metadata

- Date:
- Tester:
- Scope:
- Frontend:
  - `autocode chat`
  - `autocode chat --tui`
  - Go TUI binary/path
- Profile:
  - `default`
  - `claude_like`
- Repo root / cwd:
- Branch / worktree:
- Provider:
- Model:
- API base:
- Terminal size(s):
- Environment facts:
  - `command -v autocode`:
  - `autocode --version`:
  - `AUTOCODE_PROFILE`:
  - `AUTOCODE_LLM_PROVIDER`:
  - `AUTOCODE_LLM_API_BASE`:
  - `LITELLM_API_KEY` set?:
  - `LITELLM_MASTER_KEY` set?:
  - `OPENROUTER_API_KEY` set?:

## Gateway Preflight

- Unauthenticated `curl http://localhost:4000/v1/models`:
  - Result:
- Authenticated `curl -H "Authorization: Bearer $LITELLM_API_KEY" http://localhost:4000/v1/models`:
  - Result:
- Interpretation:
  - [ ] gateway healthy and auth required
  - [ ] gateway down / connection refused
  - [ ] other

## Scenario Matrix

| ID | Scenario | Result | Notes |
|----|----------|--------|-------|
| 1 | Bare slash discovery (`/`) | PASS / FAIL / PARTIAL / N/A | |
| 2 | `/help` parity with visible command surface | PASS / FAIL / PARTIAL / N/A | |
| 3 | `/model` current-model and listing behavior | PASS / FAIL / PARTIAL / N/A | |
| 4 | `/provider` visibility / switching | PASS / FAIL / PARTIAL / N/A | |
| 5 | Repo-local grounding (`check the files in this repo`) | PASS / FAIL / PARTIAL / N/A | |
| 6 | Prompt/tool-surface consistency (`list_files` / `tool_search`) | PASS / FAIL / PARTIAL / N/A | |
| 7 | Resize idle | PASS / FAIL / PARTIAL / N/A | |
| 8 | Resize during streaming | PASS / FAIL / PARTIAL / N/A | |
| 9 | `/loop` behavior if touched by the change | PASS / FAIL / PARTIAL / N/A | |
| 10 | Error surface quality (gateway/model/unknown command) | PASS / FAIL / PARTIAL / N/A | |

## Detailed Runs

### 1. Bare Slash Discovery
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
  - screenshot:
  - transcript:
- Severity if failed:

### 2. `/help` Parity
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

### 3. `/model`
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

### 4. `/provider`
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

### 5. Repo-Local Grounding
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

### 6. Prompt / Tool-Surface Consistency
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

### 7. Resize Idle
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

### 8. Resize During Streaming
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

### 9. `/loop`
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

### 10. Error Surface Quality
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

## Additional Cases

Add any extra scenario introduced by the change under test.

### Extra Case A
- Prompt / action:
- Expected:
- Observed:
- Result:
- Evidence:
- Severity if failed:

## Blockers

- Blocker 1:
- Blocker 2:

## Open Questions

- Question 1:
- Question 2:

## Verdict

- Overall result:
  - [ ] PASS
  - [ ] PASS WITH NITS
  - [ ] NEEDS WORK
  - [ ] BLOCKED
- Safe to claim feature complete?:
  - [ ] yes
  - [ ] no
- Follow-up required:
  - [ ] yes
  - [ ] no

## Follow-up Work

1.
2.
3.
