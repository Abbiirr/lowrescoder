"""Tests for LLM provider utilities."""

from __future__ import annotations

from hybridcoder.layer4.llm import ConversationHistory


class TestConversationHistory:
    """Test ConversationHistory management."""

    def test_add_and_get_messages(self) -> None:
        h = ConversationHistory(system_prompt="sys")
        h.add_user("hello")
        h.add_assistant("hi")
        msgs = h.get_messages()
        assert len(msgs) == 3
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "assistant"

    def test_trim_removes_pairs_not_singles(self) -> None:
        """Trim should remove user+assistant pairs, not leave orphans."""
        h = ConversationHistory(system_prompt="s")
        h.add_user("u1" * 100)
        h.add_assistant("a1" * 100)
        h.add_user("u2" * 100)
        h.add_assistant("a2" * 100)
        h.add_user("u3")
        h.add_assistant("a3")

        # Trim to a budget that forces removal of oldest pairs
        h.trim_to_budget(50)
        msgs = h.get_messages()

        # System prompt should always be preserved
        assert msgs[0]["role"] == "system"

        # No orphan assistant messages — every user has a matching assistant
        non_system = [m for m in msgs if m["role"] != "system"]
        for i in range(0, len(non_system) - 1, 2):
            assert non_system[i]["role"] == "user"
            if i + 1 < len(non_system):
                assert non_system[i + 1]["role"] == "assistant"

    def test_trim_preserves_system_prompt(self) -> None:
        h = ConversationHistory(system_prompt="keep me")
        h.add_user("x" * 1000)
        h.add_assistant("y" * 1000)
        h.trim_to_budget(10)
        assert h.get_messages()[0] == {"role": "system", "content": "keep me"}

    def test_token_estimate(self) -> None:
        h = ConversationHistory()
        h.add_user("a" * 400)  # ~100 tokens
        assert h.token_estimate() == 100
