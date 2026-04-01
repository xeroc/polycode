"""Tests for ContextRegistry."""

from typing import Any
from unittest.mock import MagicMock

from modules.registry import ContextRegistry


def _collect_a(state: Any) -> dict[str, Any]:
    return {"key_a": "value_a", "key_b": "value_b"}


def _collect_c(state: Any) -> dict[str, Any]:
    return {"key_c": "value_c"}


def _collect_overlap(state: Any) -> dict[str, Any]:
    return {"key_a": "overwritten"}


def _collect_failing(state: Any) -> dict[str, Any]:
    raise RuntimeError("boom")


def _fresh_registry() -> ContextRegistry:
    return ContextRegistry()


def test_register_and_collect():
    reg = _fresh_registry()
    reg.register("fake", _collect_a)
    result = reg.collect_all(None)
    assert result == {"key_a": "value_a", "key_b": "value_b"}


def test_multiple_collectors():
    reg = _fresh_registry()
    reg.register("fake", _collect_a)
    reg.register("another", _collect_c)
    result = reg.collect_all(None)
    assert result == {
        "key_a": "value_a",
        "key_b": "value_b",
        "key_c": "value_c",
    }


def test_key_overlap_warns():
    reg = _fresh_registry()
    reg.register("fake", _collect_a)
    reg.register("overlap", _collect_overlap)
    result = reg.collect_all(None)
    assert result["key_a"] == "overwritten"
    assert result["key_b"] == "value_b"


def test_failing_collector_skipped():
    reg = _fresh_registry()
    reg.register("fake", _collect_a)
    reg.register("failing", _collect_failing)
    result = reg.collect_all(None)
    assert result == {"key_a": "value_a", "key_b": "value_b"}


def test_list_collectors():
    reg = _fresh_registry()
    reg.register("fake", _collect_a)
    assert reg.list_collectors() == ["fake"]


def test_state_passed_through():
    reg = _fresh_registry()

    def _state_fn(state: Any) -> dict[str, Any]:
        return {"state_value": getattr(state, "value", "default")}

    reg.register("state_test", _state_fn)
    state = MagicMock()
    state.value = "from_state"
    result = reg.collect_all(state)
    assert result == {"state_value": "from_state"}


def test_collect_from_modules():
    reg = _fresh_registry()

    class FakeModule:
        @classmethod
        def get_context_collectors(cls) -> list[tuple[str, Any]]:
            return [("fake", _collect_a)]

    class EmptyModule:
        pass

    modules = {"fake": FakeModule, "empty": EmptyModule}
    count = reg.collect_from_modules(modules)
    assert count == 1
    assert "fake" in reg.list_collectors()
