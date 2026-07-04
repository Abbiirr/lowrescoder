import pytest
from src.processor import process, batch_process
from src.store import save, load, all_keys, clear


@pytest.fixture(autouse=True)
def reset_store():
    clear()


def test_process_basic():
    assert process(["hello", "world"]) == ["HELLO", "WORLD"]


def test_process_strips_whitespace():
    assert process(["  hi  "]) == ["HI"]


def test_process_raises_on_empty():
    with pytest.raises(ValueError):
        process([""])


def test_batch_process():
    result = batch_process({"a": ["x"], "b": ["y", "z"]})
    assert result == {"a": ["X"], "b": ["Y", "Z"]}


def test_store_save_and_load():
    save("run1", ["A", "B"])
    assert load("run1") == ["A", "B"]
    assert "run1" in all_keys()


def test_store_missing_key_returns_none():
    assert load("nonexistent") is None
