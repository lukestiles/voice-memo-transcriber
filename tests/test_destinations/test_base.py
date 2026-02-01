"""Tests for the base TranscriptDestination class."""

import pytest
from destinations.base import TranscriptDestination
from destinations import create_destination, register_destination


class ConcreteDestination(TranscriptDestination):
    """Concrete implementation for testing."""

    def validate_config(self):
        pass

    def initialize(self):
        pass

    def prepare_for_memo(self, memo_datetime):
        return "test_session"

    def append_transcript(self, session_id, memo_name, timestamp, transcript, memo_datetime, filepath):
        pass

    def cleanup(self):
        pass


class IncompleteDestination(TranscriptDestination):
    """Missing required methods."""
    pass


def test_abstract_base_class_cannot_be_instantiated():
    """Test that TranscriptDestination cannot be instantiated directly."""
    with pytest.raises(TypeError):
        TranscriptDestination({}, "/tmp")


def test_incomplete_implementation_cannot_be_instantiated():
    """Test that incomplete implementations cannot be instantiated."""
    with pytest.raises(TypeError):
        IncompleteDestination({}, "/tmp")


def test_complete_implementation_can_be_instantiated():
    """Test that complete implementations can be instantiated."""
    dest = ConcreteDestination({"key": "value"}, "/tmp/data")
    assert dest.config == {"key": "value"}
    assert dest.data_dir == "/tmp/data"


def test_factory_with_unknown_destination():
    """Test that factory raises error for unknown destination type."""
    with pytest.raises(ValueError, match="Unknown destination type: unknown"):
        create_destination("unknown", {}, "/tmp")


def test_factory_with_registered_destination():
    """Test that factory creates registered destinations."""
    # Register test destination
    register_destination("test_dest", ConcreteDestination)

    # Create instance
    dest = create_destination("test_dest", {"key": "value"}, "/tmp/data")

    assert isinstance(dest, ConcreteDestination)
    assert dest.config == {"key": "value"}
    assert dest.data_dir == "/tmp/data"
