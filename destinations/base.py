"""Base class for transcript destinations."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class TranscriptDestination(ABC):
    """Abstract base class for transcript destinations.

    All destination implementations must provide methods to:
    1. Initialize and authenticate with the destination service
    2. Prepare a destination for a new memo (get/create document/file)
    3. Append transcript content to the destination
    4. Clean up and provide summary information
    5. Validate configuration before use
    """

    def __init__(self, config: Dict[str, Any], data_dir: str):
        """Initialize the destination with configuration.

        Args:
            config: Destination-specific configuration dict
            data_dir: Path to data directory for credentials/state
        """
        self.config = config
        self.data_dir = data_dir

    @abstractmethod
    def validate_config(self) -> None:
        """Validate that the configuration is correct.

        Raises:
            ValueError: If configuration is invalid or missing required fields
            FileNotFoundError: If required files don't exist
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the destination (authenticate, setup services, etc).

        Called once before processing any memos.

        Raises:
            Exception: If initialization fails
        """
        pass

    @abstractmethod
    def prepare_for_memo(self, memo_datetime: Any) -> str:
        """Prepare destination for a new memo (get/create document, file, etc).

        Args:
            memo_datetime: Datetime object representing when the memo was recorded

        Returns:
            session_id: Identifier for this destination session (e.g., "doc_id:tab_id",
                       file path, etc). This will be passed to append_transcript.

        Raises:
            Exception: If preparation fails
        """
        pass

    @abstractmethod
    def append_transcript(
        self,
        session_id: str,
        memo_name: str,
        timestamp: str,
        transcript: str,
        memo_datetime: Any,
        filepath: str,
    ) -> None:
        """Append a transcript to the destination.

        Args:
            session_id: Session identifier from prepare_for_memo
            memo_name: Name of the memo file
            timestamp: Formatted timestamp string
            transcript: The transcript text
            memo_datetime: Datetime object representing when memo was recorded
            filepath: Path to the original audio file (for metadata extraction)

        Raises:
            Exception: If appending fails
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources and print summary information.

        Called after all memos have been processed.
        """
        pass

    def get_cache_key(self, memo_datetime: Any) -> str:
        """Get cache key for session caching.

        Override this method if your destination uses organization other than daily.
        For example, weekly docs should return the week identifier.

        Args:
            memo_datetime: Datetime object representing when the memo was recorded

        Returns:
            Cache key string (default: YYYY-MM-DD)
        """
        return memo_datetime.strftime("%Y-%m-%d")
