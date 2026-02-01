"""Google Docs destination for transcripts."""

import json
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from .base import TranscriptDestination


# ============================================================================
# Document Grouping Strategies
# ============================================================================


class DocGroupingStrategy(ABC):
    """Base class for document grouping strategies."""

    @abstractmethod
    def get_group_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        """Get the grouping key for document organization."""
        pass

    @abstractmethod
    def get_doc_title(self, group_key: str) -> str:
        """Get document title for this group."""
        pass


class WeeklyDocGrouping(DocGroupingStrategy):
    def get_group_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        weekday = memo_datetime.weekday()
        monday = memo_datetime - timedelta(days=weekday)
        return monday.strftime("%Y-%m-%d")

    def get_doc_title(self, group_key: str) -> str:
        return f"{group_key} Voice Memo Transcripts"


class MonthlyDocGrouping(DocGroupingStrategy):
    def get_group_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        return memo_datetime.strftime("%Y-%m")

    def get_doc_title(self, group_key: str) -> str:
        return f"{group_key} Voice Memo Transcripts"


class QuarterlyDocGrouping(DocGroupingStrategy):
    def get_group_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        quarter = (memo_datetime.month - 1) // 3 + 1
        return f"{memo_datetime.year}-Q{quarter}"

    def get_doc_title(self, group_key: str) -> str:
        return f"{group_key} Voice Memo Transcripts"


class YearlyDocGrouping(DocGroupingStrategy):
    def get_group_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        return str(memo_datetime.year)

    def get_doc_title(self, group_key: str) -> str:
        return f"{group_key} Voice Memo Transcripts"


class TagBasedDocGrouping(DocGroupingStrategy):
    def __init__(self, tag_pattern: str):
        self.tag_pattern = re.compile(tag_pattern)

    def get_group_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        # Extract tag from memo title metadata
        title = metadata.get("title", "")
        match = self.tag_pattern.search(title)
        if match:
            return f"tag-{match.group(1)}"
        return "untagged"

    def get_doc_title(self, group_key: str) -> str:
        if group_key.startswith("tag-"):
            tag = group_key[4:]  # Remove "tag-" prefix
            return f"#{tag} Voice Memo Transcripts"
        return "Untagged Voice Memo Transcripts"


class SingleDocGrouping(DocGroupingStrategy):
    def get_group_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        return "single"

    def get_doc_title(self, group_key: str) -> str:
        return "Voice Memo Transcripts"


# ============================================================================
# Tab Grouping Strategies
# ============================================================================


class TabGroupingStrategy(ABC):
    """Base class for tab grouping strategies."""

    @abstractmethod
    def get_tab_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        """Get the grouping key for tab organization."""
        pass

    @abstractmethod
    def get_tab_title(self, tab_key: str, memo_datetime: datetime) -> str:
        """Get tab title for this group."""
        pass


class DailyTabGrouping(TabGroupingStrategy):
    def __init__(self, date_format: str = "%B %d, %Y"):
        self.date_format = date_format

    def get_tab_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        return memo_datetime.strftime("%Y-%m-%d")

    def get_tab_title(self, tab_key: str, memo_datetime: datetime) -> str:
        return memo_datetime.strftime(self.date_format)


class WeeklyTabGrouping(TabGroupingStrategy):
    def get_tab_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        weekday = memo_datetime.weekday()
        monday = memo_datetime - timedelta(days=weekday)
        return monday.strftime("%Y-%m-%d")

    def get_tab_title(self, tab_key: str, memo_datetime: datetime) -> str:
        weekday = memo_datetime.weekday()
        monday = memo_datetime - timedelta(days=weekday)
        return f"Week of {monday.strftime('%B %d, %Y')}"


class TimeOfDayTabGrouping(TabGroupingStrategy):
    def __init__(self, time_ranges: Dict[str, Tuple[int, int]]):
        self.time_ranges = time_ranges

    def get_tab_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        hour = memo_datetime.hour
        for name, (start, end) in self.time_ranges.items():
            if start <= hour < end:
                return name.lower().replace(" ", "-")
        return "unknown"

    def get_tab_title(self, tab_key: str, memo_datetime: datetime) -> str:
        # Find the original name from config
        for name, (start, end) in self.time_ranges.items():
            if name.lower().replace(" ", "-") == tab_key:
                return f"{name} ({start}:00-{end}:00)"
        return "Unknown Time"


class DurationTabGrouping(TabGroupingStrategy):
    def __init__(self, duration_ranges: Dict[str, Tuple[int, float]]):
        self.duration_ranges = duration_ranges

    def get_tab_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        duration = metadata.get("duration", 0)
        for name, (min_dur, max_dur) in self.duration_ranges.items():
            if min_dur <= duration < max_dur:
                return name.lower().replace(" ", "-")
        return "unknown"

    def get_tab_title(self, tab_key: str, memo_datetime: datetime) -> str:
        for name in self.duration_ranges.keys():
            if name.lower().replace(" ", "-") == tab_key:
                return name
        return "Unknown Duration"


class NoTabGrouping(TabGroupingStrategy):
    def get_tab_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        return "all"  # All memos in one "tab" (really just the doc body)

    def get_tab_title(self, tab_key: str, memo_datetime: datetime) -> str:
        return ""  # No tab title needed


class TagBasedTabGrouping(TabGroupingStrategy):
    def __init__(self, tag_pattern: str):
        self.tag_pattern = re.compile(tag_pattern)

    def get_tab_key(self, memo_datetime: datetime, metadata: Dict) -> str:
        title = metadata.get("title", "")
        match = self.tag_pattern.search(title)
        if match:
            return f"tag-{match.group(1)}"
        return "untagged"

    def get_tab_title(self, tab_key: str, memo_datetime: datetime) -> str:
        if tab_key.startswith("tag-"):
            tag = tab_key[4:]
            return f"#{tag}"
        return "Untagged"


class GoogleDocsDestination(TranscriptDestination):
    """Destination that writes transcripts to Google Docs.

    Creates one document per week (if use_weekly_docs is True),
    with one tab per day. Supports both weekly and single-document modes.
    """

    SCOPES = ["https://www.googleapis.com/auth/documents"]

    def __init__(self, config: Dict[str, Any], data_dir: str):
        """Initialize Google Docs destination.

        Args:
            config: Configuration with keys:
                - doc_id (optional): Specific document ID to use
                - doc_title (optional): Title for new documents
                - tab_date_format (optional): strftime format for tab titles
                - use_weekly_docs (optional): Create one doc per week (legacy)
                - doc_grouping (optional): Document grouping strategy
                - tab_grouping (optional): Tab grouping strategy
            data_dir: Path to data directory for credentials/state
        """
        super().__init__(config, data_dir)
        self.service = None
        self.docs_created = []

        # Initialize grouping strategies
        self.doc_strategy = self._create_doc_grouping_strategy()
        self.tab_strategy = self._create_tab_grouping_strategy()

    def _create_doc_grouping_strategy(self) -> DocGroupingStrategy:
        """Create document grouping strategy based on config."""
        # Handle backward compatibility
        if self.config.get("doc_id"):
            return SingleDocGrouping()

        if "use_weekly_docs" in self.config and self.config["use_weekly_docs"] is False:
            return SingleDocGrouping()

        # New configuration
        grouping = self.config.get("doc_grouping", "weekly").lower()

        if grouping == "weekly":
            return WeeklyDocGrouping()
        elif grouping == "monthly":
            return MonthlyDocGrouping()
        elif grouping == "quarterly":
            return QuarterlyDocGrouping()
        elif grouping == "yearly":
            return YearlyDocGrouping()
        elif grouping == "tag":
            pattern = self.config.get("doc_tag_pattern", r"#(\w+)")
            return TagBasedDocGrouping(pattern)
        elif grouping == "single":
            return SingleDocGrouping()
        else:
            raise ValueError(f"Unknown doc_grouping: {grouping}")

    def _create_tab_grouping_strategy(self) -> TabGroupingStrategy:
        """Create tab grouping strategy based on config."""
        grouping = self.config.get("tab_grouping", "daily").lower()

        if grouping == "daily":
            date_format = self.config.get("tab_date_format", "%B %d, %Y")
            return DailyTabGrouping(date_format)
        elif grouping == "weekly":
            return WeeklyTabGrouping()
        elif grouping == "time-of-day":
            ranges = self.config.get("tab_time_ranges", {
                "Morning": (6, 12),
                "Afternoon": (12, 18),
                "Evening": (18, 24),
                "Night": (0, 6)
            })
            return TimeOfDayTabGrouping(ranges)
        elif grouping == "duration":
            ranges = self.config.get("tab_duration_ranges", {
                "Quick Notes": (0, 120),
                "Standard": (120, 600),
                "Extended": (600, float('inf'))
            })
            return DurationTabGrouping(ranges)
        elif grouping == "none":
            return NoTabGrouping()
        elif grouping == "tag":
            pattern = self.config.get("tab_tag_pattern", self.config.get("doc_tag_pattern", r"#(\w+)"))
            return TagBasedTabGrouping(pattern)
        else:
            raise ValueError(f"Unknown tab_grouping: {grouping}")

    def validate_config(self) -> None:
        """Validate that credentials.json exists."""
        creds_path = Path(self.data_dir) / "credentials.json"
        if not creds_path.exists():
            raise FileNotFoundError(
                f"Google credentials not found at {creds_path}\n"
                "Please follow the setup instructions in README.md"
            )

    def initialize(self) -> None:
        """Initialize Google Docs service."""
        creds = self._get_credentials()
        self.service = build("docs", "v1", credentials=creds)

    def prepare_for_memo(self, memo_datetime: datetime, filepath: str = None) -> str:
        """Get or create document and tab for the memo.

        Args:
            memo_datetime: When the memo was recorded
            filepath: Path to audio file (for metadata extraction)

        Returns:
            Session ID in format "doc_id:tab_id" or "doc_id" if no tabs
        """
        # Extract metadata if filepath provided
        metadata = {}
        if filepath:
            from .utils import extract_audio_metadata
            metadata = extract_audio_metadata(filepath)

        doc_id = self._get_or_create_doc(memo_datetime, metadata)
        tab_id = self._get_or_create_tab(doc_id, memo_datetime, metadata)

        if tab_id:
            return f"{doc_id}:{tab_id}"
        else:
            return doc_id  # No tabs mode

    def append_transcript(
        self,
        session_id: str,
        memo_name: str,
        timestamp: str,
        transcript: str,
        memo_datetime: datetime,
        filepath: str,
    ) -> None:
        """Append transcript to Google Doc tab (or document body if no tabs).

        Args:
            session_id: "doc_id:tab_id" from prepare_for_memo, or just "doc_id" if no tabs
            memo_name: Name of the memo file
            timestamp: Formatted timestamp string
            transcript: The transcript text
            memo_datetime: When memo was recorded
            filepath: Path to audio file
        """
        # Parse session_id
        if ":" in session_id:
            doc_id, tab_id = session_id.split(":", 1)
        else:
            doc_id = session_id
            tab_id = None

        if tab_id:
            self._append_to_tab(doc_id, tab_id, memo_name, timestamp, transcript)
        else:
            # No tabs mode - append to document body
            self._append_to_doc_body(doc_id, memo_name, timestamp, transcript)

    def cleanup(self) -> None:
        """Print summary of documents created."""
        if self.docs_created:
            print("\n📄 Google Docs created:")
            for doc_id, title in self.docs_created:
                print(f"  • {title}")
                print(f"    https://docs.google.com/document/d/{doc_id}/edit")

    def get_cache_key(self, memo_datetime: datetime, filepath: str = None) -> str:
        """Get cache key for session reuse optimization.

        Returns a key that groups memos that should share the same doc/tab.

        Args:
            memo_datetime: Datetime object representing when the memo was recorded
            filepath: Optional path to audio file for metadata extraction

        Returns:
            Cache key string
        """
        # Extract metadata if filepath provided
        metadata = {}
        if filepath:
            from .utils import extract_audio_metadata
            metadata = extract_audio_metadata(filepath)

        # Special case: user-specified doc ID
        if self.config.get("doc_id"):
            doc_key = "single_doc"
        else:
            doc_key = self.doc_strategy.get_group_key(memo_datetime, metadata)

        # Get tab key if using tabs
        if isinstance(self.tab_strategy, NoTabGrouping):
            tab_key = ""
        else:
            tab_key = self.tab_strategy.get_tab_key(memo_datetime, metadata)

        return f"{doc_key}:{tab_key}" if tab_key else doc_key

    def _get_credentials(self) -> Credentials:
        """Get or refresh Google API credentials."""
        data_dir = Path(self.data_dir)
        token_path = data_dir / "token.json"
        creds_path = data_dir / "credentials.json"

        creds = None

        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_path.exists():
                    raise FileNotFoundError(
                        f"Google credentials not found at {creds_path}\n"
                        "Please follow the setup instructions in README.md"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for next run
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return creds

    def _get_monday_of_week(self, date: datetime) -> str:
        """Get the Monday of the week for a given date in YYYY-MM-DD format."""
        weekday = date.weekday()
        days_to_monday = weekday
        monday = date - timedelta(days=days_to_monday)
        return monday.strftime("%Y-%m-%d")

    def _get_or_create_doc(self, memo_date: datetime, metadata: Dict = None) -> str:
        """Get existing doc ID for the group or create a new document.

        Uses the configured grouping strategy to determine document organization.
        """
        if metadata is None:
            metadata = {}

        data_dir = Path(self.data_dir)
        docs_map_path = data_dir / "docs_by_week.json"  # Keep filename for backward compat

        # First check if user configured a specific doc ID
        if self.config.get("doc_id"):
            return self.config["doc_id"]

        # Get group key from strategy
        group_key = self.doc_strategy.get_group_key(memo_date, metadata)

        # Load existing mappings
        docs_map = {"groups": {}}
        if docs_map_path.exists():
            with open(docs_map_path) as f:
                loaded_map = json.load(f)
                # Handle legacy format
                if "mode" in loaded_map:
                    # Old structured format - migrate to new format
                    if loaded_map["mode"] == "weekly":
                        docs_map["groups"] = loaded_map.get("weekly", {})
                    elif loaded_map["mode"] == "single":
                        docs_map["groups"] = {"single": loaded_map.get("single")}
                elif "groups" in loaded_map:
                    # New format
                    docs_map = loaded_map
                else:
                    # Legacy flat format - assume weekly
                    docs_map["groups"] = loaded_map

        # Check if we already have a doc for this group
        if group_key in docs_map["groups"]:
            return docs_map["groups"][group_key]

        # Create new document for this group
        doc_title = self.doc_strategy.get_doc_title(group_key)
        print(f"  Creating new Google Doc: '{doc_title}'")
        doc = self.service.documents().create(body={"title": doc_title}).execute()
        doc_id = doc["documentId"]

        # Save the mapping
        docs_map["groups"][group_key] = doc_id
        with open(docs_map_path, "w") as f:
            json.dump(docs_map, f, indent=2)

        self.docs_created.append((doc_id, doc_title))
        print(f"  Created doc with ID: {doc_id}")
        print(f"  URL: https://docs.google.com/document/d/{doc_id}/edit")

        return doc_id

    def _get_existing_tabs(self, doc_id: str) -> dict[str, str]:
        """Get a mapping of tab titles to tab IDs for the document.

        Returns: dict mapping tab_title -> tab_id
        """
        doc = self.service.documents().get(
            documentId=doc_id, includeTabsContent=True
        ).execute()

        tabs = {}

        if "tabs" in doc:
            for tab in doc["tabs"]:
                tab_props = tab.get("tabProperties", {})
                tab_id = tab_props.get("tabId", "")
                tab_title = tab_props.get("title", "")
                if tab_id and tab_title:
                    tabs[tab_title] = tab_id

        return tabs

    def _get_or_create_tab(self, doc_id: str, memo_datetime: datetime, metadata: Dict = None) -> str:
        """Get existing tab or create a new one based on grouping strategy.

        Returns: tab_id for the memo's tab (or None if using NoTabGrouping)
        """
        if metadata is None:
            metadata = {}

        # Check if we're using tabs at all
        if isinstance(self.tab_strategy, NoTabGrouping):
            # No tabs mode - return None to indicate writing to doc body
            return None

        # Get tab key and title from strategy
        tab_key = self.tab_strategy.get_tab_key(memo_datetime, metadata)
        tab_title = self.tab_strategy.get_tab_title(tab_key, memo_datetime)

        # Check if tab already exists
        existing_tabs = self._get_existing_tabs(doc_id)

        if tab_title in existing_tabs:
            print(f"  Using existing tab: '{tab_title}'")
            return existing_tabs[tab_title]

        # Create new tab
        print(f"  Creating new tab: '{tab_title}'")

        requests = [{"addDocumentTab": {"tabProperties": {"title": tab_title}}}]

        response = self.service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()

        # Extract the new tab ID from the response
        new_tab_id = response["replies"][0]["addDocumentTab"]["tabId"]

        # Add a header to the new tab
        header_text = f"📅 {tab_title}\n\nVoice Memo Transcripts\n\n"

        self.service.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1, "tabId": new_tab_id},
                            "text": header_text,
                        }
                    }
                ]
            },
        ).execute()

        return new_tab_id

    def _get_tab_end_index(self, doc_id: str, tab_id: str) -> int:
        """Get the end index of content in a specific tab."""
        doc = self.service.documents().get(
            documentId=doc_id, includeTabsContent=True
        ).execute()

        if "tabs" in doc:
            for tab in doc["tabs"]:
                if tab.get("tabProperties", {}).get("tabId") == tab_id:
                    doc_tab = tab.get("documentTab", {})
                    body = doc_tab.get("body", {})
                    content = body.get("content", [])
                    if content:
                        return content[-1].get("endIndex", 1) - 1

        return 1

    def _append_to_tab(
        self, doc_id: str, tab_id: str, memo_name: str, timestamp: str, transcript: str
    ):
        """Append a transcription to a specific tab in the Google Doc."""
        content = f"\n{'─'*50}\n"
        content += f"📝 {memo_name}\n"
        content += f"🕐 {timestamp}\n"
        content += f"{'─'*50}\n\n"
        content += transcript
        content += "\n\n"

        # Get current tab content length
        end_index = self._get_tab_end_index(doc_id, tab_id)

        # Insert at end of tab
        requests = [
            {
                "insertText": {
                    "location": {"index": end_index, "tabId": tab_id},
                    "text": content,
                }
            }
        ]

        self.service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()

    def _append_to_doc_body(
        self, doc_id: str, memo_name: str, timestamp: str, transcript: str
    ):
        """Append a transcription to the document body (no tabs)."""
        # Get current end index of document
        doc = self.service.documents().get(documentId=doc_id).execute()
        end_index = doc["body"]["content"][-1]["endIndex"] - 1

        content = f"\n{'─'*50}\n"
        content += f"📝 {memo_name}\n"
        content += f"🕐 {timestamp}\n"
        content += f"{'─'*50}\n\n"
        content += transcript
        content += "\n\n"

        requests = [
            {
                "insertText": {
                    "location": {"index": end_index},
                    "text": content,
                }
            }
        ]

        self.service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()
