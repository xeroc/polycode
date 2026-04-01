"""Tests for ContextInjector and ContextRegistry."""

from typing import Any
from unittest.mock import MagicMock

from modules.context_injector import ContextInjector, ContextRegistry


class FakeInjector:
    """Test injector that returns a fixed dict."""

    name = "fake"
    keys = ["key_a", "key_b"]

    def collect(self, state: Any) -> dict[str, Any]:
        return {"key_a": "value_a", "key_b": "value_b"}


class AnotherInjector:
    """Second test injector."""

    name = "another"
    keys = ["key_c"]

    def collect(self, state: Any) -> dict[str, Any]:
        return {"key_c": "value_c"}


class OverlapInjector:
    """Injector that overlaps keys with FakeInjector."""

    name = "overlap"
    keys = ["key_a"]

    def collect(self, state: Any) -> dict[str, Any]:
        return {"key_a": "overwritten"}


class FailingInjector:
    """Injector that raises on collect."""

    name = "failing"
    keys = ["broken"]

    def collect(self, state: Any) -> dict[str, Any]:
        raise RuntimeError("boom")


def _setup():
    ContextRegistry.reset()


def test_register_and_collect():
    """Test basic register and collect_all."""
    _setup()
    ContextRegistry.register(FakeInjector())
    result = ContextRegistry.collect_all(None)
    assert result == {"key_a": "value_a", "key_b": "value_b"}


def test_multiple_injectors():
    """Test merging from multiple injectors."""
    _setup()
    ContextRegistry.register(FakeInjector())
    ContextRegistry.register(AnotherInjector())
    result = ContextRegistry.collect_all(None)
    assert result == {
        "key_a": "value_a",
        "key_b": "value_b",
        "key_c": "value_c",
    }


def test_key_overlap_warns():
    """Test that overlapping keys log a warning and overwrite."""
    _setup()
    ContextRegistry.register(FakeInjector())
    ContextRegistry.register(OverlapInjector())
    result = ContextRegistry.collect_all(None)
    assert result["key_a"] == "overwritten"
    assert result["key_b"] == "value_b"


def test_failing_injector_skipped():
    """Test that a failing injector doesn't break collect_all."""
    _setup()
    ContextRegistry.register(FakeInjector())
    ContextRegistry.register(FailingInjector())
    result = ContextRegistry.collect_all(None)
    assert result == {"key_a": "value_a", "key_b": "value_b"}


def test_get_injectors():
    """Test get_injectors returns copy."""
    _setup()
    inj = FakeInjector()
    ContextRegistry.register(inj)
    injectors = ContextRegistry.get_injectors()
    assert "fake" in injectors
    injectors.clear()
    assert "fake" in ContextRegistry.get_injectors()


def test_reset():
    """Test reset clears all injectors."""
    _setup()
    ContextRegistry.register(FakeInjector())
    ContextRegistry.reset()
    assert ContextRegistry.collect_all(None) == {}


def test_state_passed_to_collect():
    """Test that state is passed through to injectors."""
    _setup()

    class StateInjector:
        name = "state_test"
        keys = ["state_value"]

        def collect(self, state: Any) -> dict[str, Any]:
            return {"state_value": getattr(state, "value", "default")}

    ContextRegistry.register(StateInjector())
    state = MagicMock()
    state.value = "from_state"
    result = ContextRegistry.collect_all(state)
    assert result == {"state_value": "from_state"}


def test_protocol_conformance():
    """Test that FakeInjector satisfies ContextInjector protocol."""
    assert isinstance(FakeInjector(), ContextInjector)
    assert not isinstance("not_an_injector", ContextInjector)
