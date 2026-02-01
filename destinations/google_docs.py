"""Google Docs destination for transcripts."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from .base import TranscriptDestination


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
                - use_weekly_docs (optional): Create one doc per week
            data_dir: Path to data directory for credentials/state
        """
        super().__init__(config, data_dir)
        self.service = None
        self.docs_created = []

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

    def prepare_for_memo(self, memo_datetime: datetime) -> str:
        """Get or create document and tab for the memo.

        Args:
            memo_datetime: When the memo was recorded

        Returns:
            Session ID in format "doc_id:tab_id"
        """
        doc_id = self._get_or_create_doc(memo_datetime)
        tab_id = self._get_or_create_tab_for_date(doc_id, memo_datetime)
        return f"{doc_id}:{tab_id}"

    def append_transcript(
        self,
        session_id: str,
        memo_name: str,
        timestamp: str,
        transcript: str,
        memo_datetime: datetime,
        filepath: str,
    ) -> None:
        """Append transcript to Google Doc tab.

        Args:
            session_id: "doc_id:tab_id" from prepare_for_memo
            memo_name: Name of the memo file
            timestamp: Formatted timestamp string
            transcript: The transcript text
            memo_datetime: Not used for Google Docs
            filepath: Not used for Google Docs (no metadata extraction)
        """
        doc_id, tab_id = session_id.split(":", 1)
        self._append_to_tab(doc_id, tab_id, memo_name, timestamp, transcript)

    def cleanup(self) -> None:
        """Print summary of documents created."""
        if self.docs_created:
            print("\n📄 Google Docs created:")
            for doc_id, title in self.docs_created:
                print(f"  • {title}")
                print(f"    https://docs.google.com/document/d/{doc_id}/edit")

    def get_cache_key(self, memo_datetime: datetime) -> str:
        """Get cache key based on organization mode.

        For weekly docs, return week identifier (Monday date).
        For single/daily docs, return date.

        Args:
            memo_datetime: Datetime object representing when the memo was recorded

        Returns:
            Cache key string
        """
        use_weekly_docs = self.config.get("use_weekly_docs", True)
        doc_id = self.config.get("doc_id")

        # If specific doc_id is set, use a constant key (all memos go to same doc)
        if doc_id:
            return "single_doc"

        # If weekly docs mode, use Monday as key
        if use_weekly_docs:
            return self._get_monday_of_week(memo_datetime)

        # Single doc mode (but no doc_id set) - use constant key
        return "single_doc"

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

    def _get_or_create_doc(self, memo_date: datetime) -> str:
        """Get existing doc ID for the week or create a new document.

        Creates one document per week (if enabled), named with the Monday date.
        """
        data_dir = Path(self.data_dir)
        docs_map_path = data_dir / "docs_by_week.json"

        # First check if user configured a specific doc ID
        if self.config.get("doc_id"):
            return self.config["doc_id"]

        # Check if weekly docs are enabled (default: True for backward compat)
        use_weekly_docs = self.config.get("use_weekly_docs", True)

        # Load existing mappings (use structured format)
        docs_map = {"mode": None, "weekly": {}, "single": None}
        if docs_map_path.exists():
            with open(docs_map_path) as f:
                loaded_map = json.load(f)
                # Handle legacy format (flat dict with week keys or single_doc key)
                if "mode" in loaded_map:
                    # New structured format
                    docs_map = loaded_map
                elif "single_doc" in loaded_map:
                    # Legacy single mode
                    docs_map = {
                        "mode": "single",
                        "weekly": {},
                        "single": loaded_map["single_doc"],
                    }
                else:
                    # Legacy weekly mode (has date keys like "2025-01-27")
                    docs_map = {"mode": "weekly", "weekly": loaded_map, "single": None}

        if not use_weekly_docs:
            # Single document mode
            if docs_map["single"]:
                return docs_map["single"]

            # Create single document
            doc_title = self.config.get("doc_title", "Voice Memo Transcripts")
            print(f"  Creating new Google Doc: '{doc_title}'")
            doc = self.service.documents().create(body={"title": doc_title}).execute()
            doc_id = doc["documentId"]

            # Save the mapping
            docs_map["mode"] = "single"
            docs_map["single"] = doc_id
            with open(docs_map_path, "w") as f:
                json.dump(docs_map, f, indent=2)

            self.docs_created.append((doc_id, doc_title))
            print(f"  Created doc with ID: {doc_id}")
            print(f"  URL: https://docs.google.com/document/d/{doc_id}/edit")

            return doc_id

        # Weekly docs mode
        monday_str = self._get_monday_of_week(memo_date)

        # Check if we already have a doc for this week
        if monday_str in docs_map["weekly"]:
            return docs_map["weekly"][monday_str]

        # Create new document for this week
        doc_title = f"{monday_str} Voice Memo Transcripts"
        print(f"  Creating new Google Doc: '{doc_title}'")
        doc = self.service.documents().create(body={"title": doc_title}).execute()
        doc_id = doc["documentId"]

        # Save the mapping
        docs_map["mode"] = "weekly"
        docs_map["weekly"][monday_str] = doc_id
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

    def _get_or_create_tab_for_date(self, doc_id: str, date: datetime) -> str:
        """Get existing tab for the date, or create a new one.

        Returns: tab_id for the date's tab
        """
        tab_date_format = self.config.get("tab_date_format", "%B %d, %Y")
        tab_title = date.strftime(tab_date_format)

        # Check if tab already exists
        existing_tabs = self._get_existing_tabs(doc_id)

        if tab_title in existing_tabs:
            print(f"  Using existing tab: '{tab_title}'")
            return existing_tabs[tab_title]

        # Create new tab
        print(f"  Creating new tab: '{tab_title}'")

        requests = [{"createTab": {"tabProperties": {"title": tab_title}}}]

        response = self.service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()

        # Extract the new tab ID from the response
        new_tab_id = response["replies"][0]["createTab"]["tabProperties"]["tabId"]

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
