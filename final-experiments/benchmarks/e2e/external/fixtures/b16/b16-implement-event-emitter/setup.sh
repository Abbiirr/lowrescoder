#!/usr/bin/env bash
# Setup for b16-implement-event-emitter
# Creates a spec and test file for a typed event emitter.
set -euo pipefail

# Specification document
cat > spec.md << 'SPEC'
# Typed Event Emitter Specification

## Overview

Implement an `EventEmitter` class that provides a publish-subscribe pattern
for event-driven communication.

## Class: `EventEmitter`

### Constructor

```python
EventEmitter()
```

Creates an event emitter with no registered listeners.

### Methods

#### `on(event: str, callback: callable) -> callable`

Register a callback for an event. The callback will be called every time
the event is emitted. Returns the callback (for use as a decorator).

Multiple callbacks can be registered for the same event. They are called
in the order they were registered.

#### `once(event: str, callback: callable) -> callable`

Register a callback that will be called only once, then automatically
removed. Returns the callback.

#### `emit(event: str, *args, **kwargs) -> bool`

Emit an event, calling all registered callbacks with the provided arguments.
Returns `True` if the event had any listeners, `False` otherwise.

`once` listeners are removed after being called.

#### `off(event: str, callback: callable) -> bool`

Remove a specific callback from an event. Returns `True` if the callback
was found and removed, `False` otherwise.

#### `remove_all_listeners(event: str = None) -> None`

If `event` is provided, remove all listeners for that event.
If `event` is `None`, remove all listeners for all events.

#### `listeners(event: str) -> list`

Return a list of all callbacks registered for an event.
Returns an empty list if no listeners exist.

#### `listener_count(event: str) -> int`

Return the number of listeners registered for an event.

### Properties

#### `event_names -> list[str]`

Return a list of all event names that have at least one listener.

## Module

The class must be importable as:
```python
from event_emitter import EventEmitter
```
SPEC

# Test file
cat > test_event_emitter.py << 'PYTHON'
"""Tests for typed event emitter."""
import pytest
from event_emitter import EventEmitter


class TestEventEmitterOn:
    def test_on_and_emit(self):
        ee = EventEmitter()
        results = []
        ee.on("data", lambda x: results.append(x))
        ee.emit("data", 42)
        assert results == [42]

    def test_multiple_listeners(self):
        ee = EventEmitter()
        results = []
        ee.on("data", lambda x: results.append(f"a:{x}"))
        ee.on("data", lambda x: results.append(f"b:{x}"))
        ee.emit("data", 1)
        assert results == ["a:1", "b:1"]

    def test_listener_order_preserved(self):
        ee = EventEmitter()
        order = []
        ee.on("evt", lambda: order.append(1))
        ee.on("evt", lambda: order.append(2))
        ee.on("evt", lambda: order.append(3))
        ee.emit("evt")
        assert order == [1, 2, 3]

    def test_on_returns_callback(self):
        ee = EventEmitter()
        cb = lambda: None
        result = ee.on("evt", cb)
        assert result is cb

    def test_emit_with_kwargs(self):
        ee = EventEmitter()
        results = []
        ee.on("data", lambda name="": results.append(name))
        ee.emit("data", name="alice")
        assert results == ["alice"]


class TestEventEmitterOnce:
    def test_once_fires_once(self):
        ee = EventEmitter()
        results = []
        ee.once("data", lambda x: results.append(x))
        ee.emit("data", 1)
        ee.emit("data", 2)
        assert results == [1]

    def test_once_returns_callback(self):
        ee = EventEmitter()
        cb = lambda: None
        result = ee.once("evt", cb)
        assert result is cb

    def test_once_removed_after_emit(self):
        ee = EventEmitter()
        ee.once("evt", lambda: None)
        assert ee.listener_count("evt") == 1
        ee.emit("evt")
        assert ee.listener_count("evt") == 0


class TestEventEmitterEmit:
    def test_emit_returns_true_with_listeners(self):
        ee = EventEmitter()
        ee.on("evt", lambda: None)
        assert ee.emit("evt") is True

    def test_emit_returns_false_without_listeners(self):
        ee = EventEmitter()
        assert ee.emit("evt") is False

    def test_emit_unknown_event(self):
        ee = EventEmitter()
        assert ee.emit("nonexistent") is False

    def test_emit_multiple_args(self):
        ee = EventEmitter()
        results = []
        ee.on("data", lambda a, b, c: results.append((a, b, c)))
        ee.emit("data", 1, 2, 3)
        assert results == [(1, 2, 3)]


class TestEventEmitterOff:
    def test_off_removes_listener(self):
        ee = EventEmitter()
        results = []
        cb = lambda: results.append(1)
        ee.on("evt", cb)
        ee.off("evt", cb)
        ee.emit("evt")
        assert results == []

    def test_off_returns_true_when_found(self):
        ee = EventEmitter()
        cb = lambda: None
        ee.on("evt", cb)
        assert ee.off("evt", cb) is True

    def test_off_returns_false_when_not_found(self):
        ee = EventEmitter()
        assert ee.off("evt", lambda: None) is False

    def test_off_only_removes_specific_listener(self):
        ee = EventEmitter()
        results = []
        cb1 = lambda: results.append(1)
        cb2 = lambda: results.append(2)
        ee.on("evt", cb1)
        ee.on("evt", cb2)
        ee.off("evt", cb1)
        ee.emit("evt")
        assert results == [2]


class TestEventEmitterManagement:
    def test_remove_all_for_event(self):
        ee = EventEmitter()
        ee.on("a", lambda: None)
        ee.on("a", lambda: None)
        ee.on("b", lambda: None)
        ee.remove_all_listeners("a")
        assert ee.listener_count("a") == 0
        assert ee.listener_count("b") == 1

    def test_remove_all_global(self):
        ee = EventEmitter()
        ee.on("a", lambda: None)
        ee.on("b", lambda: None)
        ee.remove_all_listeners()
        assert ee.listener_count("a") == 0
        assert ee.listener_count("b") == 0

    def test_listeners_returns_list(self):
        ee = EventEmitter()
        cb = lambda: None
        ee.on("evt", cb)
        assert cb in ee.listeners("evt")

    def test_listeners_empty_for_unknown(self):
        ee = EventEmitter()
        assert ee.listeners("unknown") == []

    def test_listener_count(self):
        ee = EventEmitter()
        ee.on("evt", lambda: None)
        ee.on("evt", lambda: None)
        assert ee.listener_count("evt") == 2

    def test_event_names(self):
        ee = EventEmitter()
        ee.on("a", lambda: None)
        ee.on("b", lambda: None)
        names = ee.event_names
        assert "a" in names
        assert "b" in names

    def test_event_names_excludes_empty(self):
        ee = EventEmitter()
        ee.on("a", lambda: None)
        cb = lambda: None
        ee.on("b", cb)
        ee.off("b", cb)
        names = ee.event_names
        assert "a" in names
        assert "b" not in names
PYTHON

# Empty implementation
cat > event_emitter.py << 'PYTHON'
"""Typed event emitter / pub-sub.

Implement according to spec.md.
"""

# TODO: Implement EventEmitter class
PYTHON

echo "Setup complete. Event emitter spec and tests created."
