"""Obsidian destination for transcripts."""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from .base import TranscriptDestination
from .utils import extract_audio_metadata, format_duration


class ObsidianDestination(TranscriptDestination):
    """Destination that writes transcripts to Obsidian vault as markdown files.

    Creates daily or weekly markdown files with YAML frontmatter,
    organized by date with proper Obsidian formatting.
    """

    def __init__(self, config: Dict[str, Any], data_dir: str):
        """Initialize Obsidian destination.

        Args:
            config: Configuration with keys:
                - vault_path (required): Path to Obsidian vault
                - folder (optional): Subfolder for transcripts (default: "Voice Memos")
                - organize_by (optional): "daily" or "weekly" (default: "daily")
                - date_format (optional): strftime format for filenames (default: "%Y-%m-%d")
                - include_frontmatter (optional): Add YAML frontmatter (default: True)
                - include_tags (optional): Add #voice-memo tag (default: True)
                - include_metadata (optional): Extract audio metadata (default: True)
            data_dir: Path to data directory (not used by Obsidian)
        """
        super().__init__(config, data_dir)
        self.vault_path = None
        self.folder_path = None
        self.memo_count = {}  # Track memos per file for frontmatter updates

    def validate_config(self) -> None:
        """Validate that vault path exists and is a valid Obsidian vault."""
        if "vault_path" not in self.config:
            raise ValueError("vault_path is required in Obsidian config")

        vault_path = Path(os.path.expanduser(self.config["vault_path"]))

        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {vault_path}")

        if not vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {vault_path}")

        # Check for .obsidian directory
        obsidian_dir = vault_path / ".obsidian"
        if not obsidian_dir.exists():
            raise ValueError(
                f"Not a valid Obsidian vault (missing .obsidian directory): {vault_path}"
            )

    def initialize(self) -> None:
        """Initialize Obsidian destination (create folder if needed)."""
        self.validate_config()

        self.vault_path = Path(os.path.expanduser(self.config["vault_path"]))
        folder = self.config.get("folder", "Voice Memos")
        self.folder_path = self.vault_path / folder

        # Create folder if it doesn't exist
        self.folder_path.mkdir(parents=True, exist_ok=True)

    def prepare_for_memo(self, memo_datetime: datetime) -> str:
        """Prepare markdown file for the memo (daily or weekly).

        Args:
            memo_datetime: When the memo was recorded

        Returns:
            File path to the markdown file
        """
        organize_by = self.config.get("organize_by", "daily")
        date_format = self.config.get("date_format", "%Y-%m-%d")

        if organize_by == "weekly":
            # Get Monday of the week
            monday = self._get_monday_of_week(memo_datetime)
            filename = f"{monday.strftime(date_format)} Week.md"
            file_path = self.folder_path / filename

            if not file_path.exists():
                self._create_file_with_header(
                    file_path, monday, organize_by="weekly"
                )
        else:  # daily
            filename = f"{memo_datetime.strftime(date_format)}.md"
            file_path = self.folder_path / filename

            if not file_path.exists():
                self._create_file_with_header(
                    file_path, memo_datetime, organize_by="daily"
                )

        return str(file_path)

    def append_transcript(
        self,
        session_id: str,
        memo_name: str,
        timestamp: str,
        transcript: str,
        memo_datetime: datetime,
        filepath: str,
    ) -> None:
        """Append transcript to Obsidian markdown file.

        Args:
            session_id: File path from prepare_for_memo
            memo_name: Name of the memo file
            timestamp: Formatted timestamp string
            transcript: The transcript text
            memo_datetime: When memo was recorded
            filepath: Path to audio file (for metadata extraction)
        """
        file_path = Path(session_id)

        # Extract metadata if enabled
        metadata = {}
        if self.config.get("include_metadata", True):
            metadata = extract_audio_metadata(filepath)

        # Format the content
        content = self._format_transcript_entry(
            memo_name, timestamp, transcript, metadata
        )

        # Append to file
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content)

        # Update memo count in frontmatter
        self._update_memo_count(file_path)

    def cleanup(self) -> None:
        """Print summary of vault location."""
        if self.folder_path:
            print(f"\n📝 Transcripts saved to Obsidian vault:")
            print(f"  {self.folder_path}")

    def get_cache_key(self, memo_datetime: datetime) -> str:
        """Get cache key based on organization mode.

        For weekly organization, return Monday date.
        For daily organization, return the date.

        Args:
            memo_datetime: Datetime object representing when the memo was recorded

        Returns:
            Cache key string
        """
        organize_by = self.config.get("organize_by", "daily")

        if organize_by == "weekly":
            monday = self._get_monday_of_week(memo_datetime)
            return monday.strftime("%Y-%m-%d")
        else:
            return memo_datetime.strftime("%Y-%m-%d")

    def _get_monday_of_week(self, date: datetime) -> datetime:
        """Get the Monday of the week for a given date."""
        weekday = date.weekday()
        days_to_monday = weekday
        monday = date - timedelta(days=days_to_monday)
        return monday

    def _create_file_with_header(
        self, file_path: Path, date: datetime, organize_by: str = "daily"
    ) -> None:
        """Create a new markdown file with frontmatter and header.

        Args:
            file_path: Path to the file to create
            date: Date for the file
            organize_by: "daily" or "weekly"
        """
        include_frontmatter = self.config.get("include_frontmatter", True)
        include_tags = self.config.get("include_tags", True)

        content = ""

        # Add frontmatter
        if include_frontmatter:
            content += "---\n"
            content += f"date: {date.strftime('%Y-%m-%d')}\n"
            content += "type: voice-memo-transcript\n"

            if include_tags:
                content += "tags: [voice-memo]\n"

            if organize_by == "weekly":
                # Use the Monday date for week calculation (consistent with file naming)
                monday = self._get_monday_of_week(date)
                week_num = monday.isocalendar()[1]
                year = monday.isocalendar()[0]  # Use ISO year (handles year boundaries)
                content += f"week: {year}-W{week_num:02d}\n"

            content += "memo_count: 0\n"
            content += "---\n\n"

        # Add header
        if organize_by == "weekly":
            monday = self._get_monday_of_week(date)
            header = f"# Voice Memos - Week of {monday.strftime('%B %d, %Y')}\n\n"
        else:
            header = f"# Voice Memos - {date.strftime('%B %d, %Y')}\n\n"

        content += header

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Initialize memo count
        self.memo_count[str(file_path)] = 0

    def _format_transcript_entry(
        self, memo_name: str, timestamp: str, transcript: str, metadata: Dict[str, Any]
    ) -> str:
        """Format a transcript entry in Obsidian markdown.

        Args:
            memo_name: Name of the memo
            timestamp: Formatted timestamp
            transcript: The transcript text
            metadata: Audio metadata dict

        Returns:
            Formatted markdown string
        """
        # Get title and sanitize for markdown
        title = metadata.get("title", memo_name)
        # Escape backslashes and backticks that could break markdown
        title = title.replace("\\", "\\\\").replace("`", "\\`")

        content = "---\n\n"
        content += f"## {title}\n\n"
        content += f"**Recorded:** {timestamp}\n"

        # Add metadata if available
        if "duration" in metadata:
            duration_str = format_duration(metadata["duration"])
            content += f"**Duration:** {duration_str}\n"

        if "device" in metadata:
            content += f"**Device:** {metadata['device']}\n"

        content += "\n"
        content += transcript
        content += "\n\n"

        return content

    def _update_memo_count(self, file_path: Path) -> None:
        """Update the memo_count field in the frontmatter.

        Args:
            file_path: Path to the markdown file
        """
        if not self.config.get("include_frontmatter", True):
            return

        file_key = str(file_path)

        # Read file once
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Increment count
        if file_key not in self.memo_count:
            # Extract current count from frontmatter
            if "memo_count: " in content:
                try:
                    start = content.index("memo_count: ") + len("memo_count: ")
                    end = content.index("\n", start)
                    current_count = int(content[start:end])
                    self.memo_count[file_key] = current_count
                except (ValueError, IndexError):
                    self.memo_count[file_key] = 0
            else:
                self.memo_count[file_key] = 0

        self.memo_count[file_key] += 1
        new_count = self.memo_count[file_key]

        # Update memo_count in frontmatter only (before first closing ---)
        # This ensures we only replace in frontmatter, not in content

        # Match memo_count in the frontmatter (between --- markers)
        pattern = r"(---\n(?:.*\n)*?)(memo_count:\s*\d+)(\n(?:.*\n)*?---)"
        replacement = rf"\g<1>memo_count: {new_count}\g<3>"

        updated_content = re.sub(pattern, replacement, content, count=1)

        # Write updated content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
