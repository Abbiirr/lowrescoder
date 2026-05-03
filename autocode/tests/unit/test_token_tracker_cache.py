"""Token tracker cache-accounting tests."""

from __future__ import annotations


def test_token_usage_billable_input_cost_factor_accounts_for_cache() -> None:
    from autocode.agent.token_tracker import TokenUsage

    usage = TokenUsage(
        prompt_tokens=1000,
        completion_tokens=50,
        cached_input_tokens=500,
        cache_creation_tokens=100,
    )

    assert usage.reasoning_tokens == 0
    assert usage.billable_input_cost_factor == 0.675


def test_token_tracker_record_cache_aggregates_by_provider() -> None:
    from autocode.agent.token_tracker import TokenTracker

    tracker = TokenTracker()
    tracker.record(
        prompt_tokens=1000,
        completion_tokens=100,
        provider="openrouter / anthropic/claude",
        cached_input_tokens=200,
        cache_creation_tokens=50,
        reasoning_tokens=25,
    )
    tracker.record_cache(
        provider="openrouter / anthropic/claude",
        cache_read_tokens=300,
        cache_write_tokens=20,
    )

    total = tracker.total
    by_provider = tracker.by_provider("openrouter / anthropic/claude")

    assert total.cached_input_tokens == 500
    assert total.cache_creation_tokens == 70
    assert total.reasoning_tokens == 25
    assert by_provider.cached_input_tokens == 500
    assert by_provider.cache_creation_tokens == 70
    assert tracker.summary()


def test_token_tracker_snapshot_round_trip() -> None:
    from autocode.agent.token_tracker import TokenTracker

    tracker = TokenTracker()
    tracker.record(
        prompt_tokens=1000,
        completion_tokens=100,
        provider="openrouter / anthropic/claude",
        cached_input_tokens=200,
        cache_creation_tokens=50,
        reasoning_tokens=25,
    )

    restored = TokenTracker()
    restored.load_snapshot(tracker.to_snapshot())

    assert restored.total.prompt_tokens == 1000
    assert restored.total.cached_input_tokens == 200
    assert restored.total.cache_creation_tokens == 50
    assert restored.total.reasoning_tokens == 25
    assert restored.by_provider("openrouter / anthropic/claude").completion_tokens == 100


def test_session_store_persists_token_usage_snapshot(tmp_path) -> None:
    from autocode.agent.token_tracker import TokenTracker
    from autocode.session.store import SessionStore

    store = SessionStore(tmp_path / "sessions.db")
    session_id = store.create_session("test", model="coding", provider="openrouter")
    tracker = TokenTracker()
    tracker.record(
        prompt_tokens=1000,
        completion_tokens=100,
        provider="openrouter / anthropic/claude",
        cached_input_tokens=200,
        cache_creation_tokens=50,
        reasoning_tokens=25,
    )

    store.save_token_usage(session_id, tracker.to_snapshot())

    restored = TokenTracker()
    restored.load_snapshot(store.load_token_usage(session_id))
    assert restored.total.prompt_tokens == 1000
    assert restored.total.cache_creation_tokens == 50
    assert restored.providers == ["openrouter / anthropic/claude"]
