"""Tests for tool metadata expansion (PLAN.md Section 0.4)."""

from autocode.agent.tools import ToolDefinition, ToolRegistry


class TestToolMetadataDefaults:
    """Test that default metadata values are sensible."""

    def test_default_concurrency_safe(self) -> None:
        """Default concurrency_safe is True."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={},
            handler=lambda: "ok",
        )
        assert tool.concurrency_safe is True

    def test_default_interruptible(self) -> None:
        """Default interruptible is False."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={},
            handler=lambda: "ok",
        )
        assert tool.interruptible is False

    def test_default_output_budget(self) -> None:
        """Default output_budget_tokens is 1000."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={},
            handler=lambda: "ok",
        )
        assert tool.output_budget_tokens == 1000

    def test_default_direct_call(self) -> None:
        """Default direct_call_eligible is True."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={},
            handler=lambda: "ok",
        )
        assert tool.direct_call_eligible is True

    def test_default_orchestrated(self) -> None:
        """Default orchestrated_eligible is True."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={},
            handler=lambda: "ok",
        )
        assert tool.orchestrated_eligible is True


class TestToolMetadataCustom:
    """Test setting custom metadata."""

    def test_custom_concurrency(self) -> None:
        """Can set concurrency_safe to False."""
        tool = ToolDefinition(
            name="shell_tool",
            description="Runs shell commands",
            parameters={},
            handler=lambda: "ok",
            concurrency_safe=False,
        )
        assert tool.concurrency_safe is False

    def test_custom_interruptible(self) -> None:
        """Can set interruptible to True."""
        tool = ToolDefinition(
            name="long_tool",
            description="Long running tool",
            parameters={},
            handler=lambda: "ok",
            interruptible=True,
        )
        assert tool.interruptible is True

    def test_custom_output_budget(self) -> None:
        """Can set custom output budget."""
        tool = ToolDefinition(
            name="search_tool",
            description="Search tool",
            parameters={},
            handler=lambda: "ok",
            output_budget_tokens=5000,
        )
        assert tool.output_budget_tokens == 5000

    def test_restricted_tool(self) -> None:
        """Tools can be restricted to orchestrated-only."""
        tool = ToolDefinition(
            name="internal_tool",
            description="Internal tool",
            parameters={},
            handler=lambda: "ok",
            direct_call_eligible=False,
            orchestrated_eligible=True,
        )
        assert tool.direct_call_eligible is False
        assert tool.orchestrated_eligible is True


class TestToolMetadataInRegistry:
    """Test that metadata is accessible via registry."""

    def test_metadata_in_registry(self) -> None:
        """Registry tools preserve metadata."""
        registry = ToolRegistry()
        tool = ToolDefinition(
            name="meta_test",
            description="Metadata test",
            parameters={},
            handler=lambda: "ok",
            concurrency_safe=False,
            output_budget_tokens=2000,
        )
        registry.register(tool)
        stored = registry.get("meta_test")
        assert stored is not None
        assert stored.concurrency_safe is False
        assert stored.output_budget_tokens == 2000
