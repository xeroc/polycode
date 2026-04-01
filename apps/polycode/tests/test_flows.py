"""Tests for flow system."""

from bootstrap import get_module_registry
from flows.base import KickoffIssue
from flows.protocol import FlowDef
from modules.registry import FlowRegistry


def dummy_kickoff_func(issue: KickoffIssue):
    pass


def test_register_flow():
    """Clean flow registry for each test."""
    registry = get_module_registry().flow_registry
    registry.register(
        FlowDef(
            name="test-flow",
            kickoff_func=dummy_kickoff_func,
            description="Test flow",
        )
    )
    assert registry.get_flow("test-flow") is not None


def test_get_flow_for_label():
    """Test that get_flow_for_label matches correctly."""
    registry = get_module_registry().flow_registry
    registry.register(
        FlowDef(
            name="test-flow-2",
            kickoff_func=dummy_kickoff_func,
            description="Test flow",
            supported_labels=["implement2"],
        )
    )

    flow = registry.get_flow_for_label("polycode:implement2")
    assert flow is not None
    assert flow.name == "test-flow-2"


def test_get_flow_for_label_priority():
    """Test that higher priority flow wins when multiple match."""
    registry = get_module_registry().flow_registry
    registry.register(
        FlowDef(
            name="test-flow",
            kickoff_func=dummy_kickoff_func,
            description="Test flow",
            supported_labels=["implement"],
            priority=1,
        )
    )
    registry.register(
        FlowDef(
            name="priority-flow",
            kickoff_func=dummy_kickoff_func,
            description="Priority flow",
            supported_labels=["implement"],
            priority=5,
        )
    )

    flow = registry.get_flow_for_label("polycode:implement")
    assert flow is not None
    assert flow.name == "priority-flow"


def test_get_flow_for_label_no_prefix():
    """Test that get_flow_for_label requires prefix."""
    registry = get_module_registry().flow_registry
    registry.register(
        FlowDef(
            name="test-flow",
            kickoff_func=dummy_kickoff_func,
            description="Test flow",
            supported_labels=["implement"],
        )
    )
    # Label without prefix should not match
    assert registry.get_flow_for_label("implement") is None

    # Label with prefix should match
    assert registry.get_flow_for_label("polycode:implement") is not None


def test_collect_from_modules():
    """Test collecting flows from modules."""
    registry = FlowRegistry()

    class MockModule:
        name = "mock"
        version = "1.0.0"
        dependencies = []
        flows = [FlowDef(name="mock", kickoff_func=dummy_kickoff_func)]

        @classmethod
        def on_load(cls, context):
            pass

        @classmethod
        def register_hooks(cls, pm):
            pass

        @classmethod
        def get_flows(cls):
            return cls.flows

    modules = {"mock": MockModule}
    count = registry.collect_from_modules(modules)

    assert count == 1


def test_flow_registry_singleton():
    """Test that the flow registry is a singleton."""
    registry1 = get_module_registry().flow_registry
    registry2 = get_module_registry().flow_registry
    assert registry1 is registry2
