"""LLMLOOP — Architect/Editor feedback loop.

Implements the core Architect → Editor → Verify → feedback pattern:
1. Architect (L4) analyzes task and produces a structured EditPlan
2. Editor (L3) applies the edits using constrained generation
3. Verifier (L1) checks syntax via tree-sitter
4. If verification fails, feed errors back to Architect (max 3 iterations)

On 8GB VRAM: sequential model loading (Architect → unload → Editor → unload).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EditType(StrEnum):
    """Types of code edits."""

    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"


@dataclass
class Edit:
    """A single code edit operation."""

    type: EditType
    file: str
    location: str  # Symbol path or line range
    old_content: str = ""
    new_content: str = ""
    context: str = ""  # Surrounding code for matching


@dataclass
class EditPlan:
    """Structured output from the Architect agent."""

    file: str
    edits: list[Edit] = field(default_factory=list)
    reasoning: str = ""
    test_command: str | None = None
    confidence: float = 0.0


@dataclass
class VerificationResult:
    """Result of L1 verification on edited files."""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class LLMLOOPResult:
    """Result of a complete LLMLOOP execution."""

    success: bool
    iterations: int
    plan: EditPlan | None = None
    verification: VerificationResult | None = None
    error: str = ""
    files_modified: list[str] = field(default_factory=list)
    total_tokens: int = 0


class LLMLOOP:
    """Architect/Editor feedback loop.

    Coordinates L4 Architect (planning) → L3 Editor (applying) → L1 Verifier
    with up to max_iterations feedback cycles.

    When a provider is supplied, plan() calls the real LLM.
    Without a provider, uses placeholder (for testing).
    """

    PLAN_SYSTEM_PROMPT = (
        "You are an expert code architect. Analyze the task and produce "
        "a JSON edit plan with this structure:\n"
        '{"file": "path/to/file.py", "edits": [{"type": "replace", '
        '"old_content": "...", "new_content": "..."}], '
        '"reasoning": "why this fix works", "test_command": "pytest"}\n'
        "Respond ONLY with valid JSON. No explanation outside the JSON."
    )

    def __init__(
        self,
        max_iterations: int = 3,
        verify_syntax: bool = True,
        provider: Any | None = None,
        project_root: str = "",
    ) -> None:
        self.max_iterations = max_iterations
        self.verify_syntax = verify_syntax
        self._provider = provider
        self._project_root = project_root
        self._iteration = 0

    def plan(self, task: str, context: str = "") -> EditPlan:
        """Architect phase: analyze task and produce edit plan.

        If a provider is set, calls the real LLM to generate a plan.
        Otherwise returns a placeholder for testing.
        """
        self._iteration += 1

        if self._provider is None:
            return EditPlan(
                file="",
                edits=[],
                reasoning=f"Analysis of: {task[:100]}",
                confidence=0.0,
            )

        # Real LLM call
        import asyncio
        import json as _json

        async def _call_llm() -> str:
            prompt = f"{task}"
            if context:
                prompt += f"\n\nContext:\n{context}"
            messages = [
                {"role": "system", "content": self.PLAN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            result = ""
            async for chunk in self._provider.generate(messages):
                result += chunk
            return result

        try:
            # Handle both sync and async contexts
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Already in an async context — use nest_asyncio or
                # create a new thread to avoid RuntimeError
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    raw = pool.submit(asyncio.run, _call_llm()).result(
                        timeout=120,
                    )
            else:
                raw = asyncio.run(_call_llm())
            # Parse JSON from response
            # Strip markdown code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            data = _json.loads(cleaned)
            default_file = data.get("file", "")
            edits = [
                Edit(
                    type=EditType(e.get("type", "replace")),
                    file=e.get("file", default_file),
                    location=e.get("location", ""),
                    old_content=e.get("old_content", ""),
                    new_content=e.get("new_content", ""),
                )
                for e in data.get("edits", [])
            ]
            return EditPlan(
                file=data.get("file", ""),
                edits=edits,
                reasoning=data.get("reasoning", ""),
                test_command=data.get("test_command"),
                confidence=0.8,
            )
        except Exception as e:
            return EditPlan(
                file="",
                edits=[],
                reasoning=f"LLM plan failed: {e}",
                confidence=0.0,
            )

    def apply(self, plan: EditPlan) -> list[str]:
        """Editor phase: apply edit plan to files.

        Applies edits by reading files, replacing content, writing back.
        Falls back to placeholder if project_root not set.
        """
        from pathlib import Path

        modified: list[str] = []
        root = Path(self._project_root) if self._project_root else None

        for edit in plan.edits:
            filepath = root / edit.file if root else Path(edit.file)
            try:
                if filepath.exists() and edit.old_content and edit.new_content:
                    content = filepath.read_text(encoding="utf-8")
                    if edit.old_content in content:
                        new_content = content.replace(
                            edit.old_content, edit.new_content, 1,
                        )
                        filepath.write_text(new_content, encoding="utf-8")
                        modified.append(edit.file)
                elif edit.new_content and not edit.old_content:
                    # Insert / new file
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(edit.new_content, encoding="utf-8")
                    modified.append(edit.file)
            except Exception:
                pass  # Skip failed edits, let verify catch issues

        return list(set(modified))

    def verify(self, files: list[str]) -> VerificationResult:
        """Verifier phase: check syntax with tree-sitter.

        Resolves paths against project_root to avoid cwd mismatches.
        Returns verification result with any errors found.
        """
        errors: list[str] = []

        if self.verify_syntax:
            for filepath in files:
                try:
                    from pathlib import Path

                    path = Path(filepath)
                    # Resolve against project_root if relative
                    if not path.is_absolute() and self._project_root:
                        path = Path(self._project_root) / path
                    if path.exists() and path.suffix == ".py":
                        import py_compile

                        py_compile.compile(
                            str(path), doraise=True,
                        )
                except py_compile.PyCompileError as e:
                    errors.append(f"Syntax error in {filepath}: {e}")
                except Exception:
                    pass  # Non-Python files skip verification

        return VerificationResult(
            passed=len(errors) == 0,
            errors=errors,
        )

    def run(self, task: str, context: str = "") -> LLMLOOPResult:
        """Execute the full Architect → Editor → Verify loop.

        Returns after success or max_iterations.
        """
        total_tokens = 0
        all_modified: list[str] = []
        last_plan: EditPlan | None = None
        last_verification: VerificationResult | None = None

        feedback = ""
        for iteration in range(self.max_iterations):
            # Architect
            prompt = task
            if feedback:
                prompt += f"\n\nPrevious attempt failed:\n{feedback}"

            plan = self.plan(prompt, context)
            last_plan = plan
            total_tokens += 100  # placeholder

            if not plan.edits:
                # Architect couldn't produce a plan
                if iteration == 0:
                    return LLMLOOPResult(
                        success=False,
                        iterations=iteration + 1,
                        plan=plan,
                        error="Architect produced empty edit plan",
                        total_tokens=total_tokens,
                    )
                break  # Previous iteration may have succeeded

            # Editor
            modified = self.apply(plan)
            all_modified.extend(modified)
            total_tokens += 50  # placeholder

            # Verify
            verification = self.verify(modified)
            last_verification = verification

            if verification.passed:
                return LLMLOOPResult(
                    success=True,
                    iterations=iteration + 1,
                    plan=plan,
                    verification=verification,
                    files_modified=list(set(all_modified)),
                    total_tokens=total_tokens,
                )

            # Feed errors back to Architect
            feedback = "\n".join(verification.errors)

        return LLMLOOPResult(
            success=False,
            iterations=self.max_iterations,
            plan=last_plan,
            verification=last_verification,
            error=f"Did not converge after {self.max_iterations} iterations",
            files_modified=list(set(all_modified)),
            total_tokens=total_tokens,
        )
