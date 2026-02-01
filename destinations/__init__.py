"""Destination factory and registry for transcript destinations."""

from typing import Any, Dict, Type

from .base import TranscriptDestination

# Registry of available destinations
DESTINATIONS: Dict[str, Type[TranscriptDestination]] = {}


def register_destination(name: str, cls: Type[TranscriptDestination]) -> None:
    """Register a destination class.

    Args:
        name: Destination type name (e.g., "google_docs", "obsidian")
        cls: Destination class (must extend TranscriptDestination)
    """
    DESTINATIONS[name] = cls


def create_destination(
    dest_type: str, config: Dict[str, Any], data_dir: str
) -> TranscriptDestination:
    """Factory function to create a destination instance.

    Args:
        dest_type: Type of destination ("google_docs", "obsidian", etc)
        config: Destination-specific configuration
        data_dir: Path to data directory for credentials/state

    Returns:
        Instance of the requested destination

    Raises:
        ValueError: If dest_type is not registered
    """
    if dest_type not in DESTINATIONS:
        available = ", ".join(DESTINATIONS.keys())
        raise ValueError(
            f"Unknown destination type: {dest_type}. Available: {available}"
        )

    dest_class = DESTINATIONS[dest_type]
    return dest_class(config, data_dir)


# Import and register destinations
def _register_all_destinations():
    """Import and register all available destinations."""
    try:
        from .google_docs import GoogleDocsDestination
        register_destination("google_docs", GoogleDocsDestination)
    except ImportError:
        pass  # Google Docs dependencies not available

    try:
        from .obsidian import ObsidianDestination
        register_destination("obsidian", ObsidianDestination)
    except ImportError:
        pass  # Obsidian destination not yet implemented


_register_all_destinations()

__all__ = [
    "TranscriptDestination",
    "create_destination",
    "register_destination",
    "DESTINATIONS",
]
