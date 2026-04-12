"""Tests for task-family strategy overlays (PLAN.md Section 3.1-3.3)."""

from autocode.agent.strategy_overlays import (
    OVERLAYS,
    StagnationDetector,
    TaskFamily,
    classify_task,
    get_overlay,
    verifier_aware_retry_guidance,
)


class TestTaskFamilyClassification:
    """Test task family classification from task descriptions."""

    def test_html_output_family(self) -> None:
        """HTML/filter tasks classify as HTML_OUTPUT."""
        assert classify_task("break-filter-js-from-html") == TaskFamily.HTML_OUTPUT

    def test_python_build_family(self) -> None:
        """Cython/build tasks classify as PYTHON_BUILD."""
        assert classify_task("build-cython-ext") == TaskFamily.PYTHON_BUILD

    def test_general_family(self) -> None:
        """Unknown tasks classify as GENERAL."""
        assert classify_task("refactor the auth module") == TaskFamily.GENERAL

    def test_html_keywords(self) -> None:
        """Multiple HTML keywords still classify correctly."""
        assert classify_task("parse and extract html css") == TaskFamily.HTML_OUTPUT

    def test_build_keywords(self) -> None:
        """Multiple build keywords classify correctly."""
        assert classify_task("compile extension with setup.py") == TaskFamily.PYTHON_BUILD

    def test_mixed_keywords_picks_best(self) -> None:
        """When both match, picks the higher-scoring family."""
        result = classify_task("html build extension")
        assert result in (TaskFamily.HTML_OUTPUT, TaskFamily.PYTHON_BUILD)


class TestStrategyOverlays:
    """Test overlay configuration per task family."""

    def test_all_families_have_overlays(self) -> None:
        """Every TaskFamily has a corresponding overlay."""
        for family in TaskFamily:
            assert family in OVERLAYS

    def test_html_overlay_prefers_read_edit(self) -> None:
        """HTML overlay prefers read_file and edit_file."""
        overlay = OVERLAYS[TaskFamily.HTML_OUTPUT]
        assert "read_file" in overlay.preferred_tools
        assert "edit_file" in overlay.preferred_tools

    def test_build_overlay_requires_verifier(self) -> None:
        """Python build overlay requires verifier signal."""
        overlay = OVERLAYS[TaskFamily.PYTHON_BUILD]
        assert overlay.require_verifier_signal_before_retry is True

    def test_general_overlay_no_verifier_requirement(self) -> None:
        """General overlay does not require verifier signal."""
        overlay = OVERLAYS[TaskFamily.GENERAL]
        assert overlay.require_verifier_signal_before_retry is False


class TestGetOverlay:
    """Test the get_overlay convenience function."""

    def test_returns_correct_overlay(self) -> None:
        """get_overlay returns overlay matching the classified family."""
        overlay = get_overlay("break-filter-js-from-html")
        assert overlay.family == TaskFamily.HTML_OUTPUT

    def test_returns_general_for_unknown(self) -> None:
        """get_overlay returns GENERAL for unknown tasks."""
        overlay = get_overlay("refactor the auth module")
        assert overlay.family == TaskFamily.GENERAL


class TestStagnationDetector:
    """Test stagnation detection (Section 3.3)."""

    def test_no_stagnation_initially(self) -> None:
        """No stagnation detected on first few calls."""
        detector = StagnationDetector(max_identical_results=3)
        assert detector.check("bash", "output1") is None
        assert detector.check("bash", "output1") is None

    def test_stagnation_detected(self) -> None:
        """Stagnation detected when identical results repeat."""
        detector = StagnationDetector(max_identical_results=3)
        detector.check("bash", "same output")
        detector.check("bash", "same output")
        result = detector.check("bash", "same output")
        assert result is not None
        assert "STAGNATION" in result

    def test_no_stagnation_with_different_results(self) -> None:
        """No stagnation when results differ."""
        detector = StagnationDetector(max_identical_results=3)
        detector.check("bash", "output1")
        detector.check("bash", "output2")
        result = detector.check("bash", "output3")
        assert result is None

    def test_stagnation_message_contains_guidance(self) -> None:
        """Stagnation message contains actionable guidance."""
        detector = StagnationDetector(max_identical_results=3)
        detector.check("bash", "same")
        detector.check("bash", "same")
        msg = detector.check("bash", "same")
        assert "change your approach" in msg


class TestVerifierAwareRetry:
    """Test verifier-aware retry guidance (Section 3.2)."""

    def test_no_guidance_on_first_try(self) -> None:
        """No guidance on first attempt."""
        result = verifier_aware_retry_guidance("bash", "error: failed", 0, 3)
        assert result is None

    def test_guidance_on_retry_with_error(self) -> None:
        """Guidance provided when retrying with error signal."""
        result = verifier_aware_retry_guidance("bash", "error: build failed", 1, 3)
        assert result is not None
        assert "extract the exact error" in result

    def test_max_retries_reached(self) -> None:
        """Max retries produces stop message."""
        result = verifier_aware_retry_guidance("bash", "error", 3, 3)
        assert result is not None
        assert "MAX RETRIES" in result

    def test_no_guidance_without_error(self) -> None:
        """No guidance when result has no error signal."""
        result = verifier_aware_retry_guidance("bash", "success", 1, 3)
        assert result is None
