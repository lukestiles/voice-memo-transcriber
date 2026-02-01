"""Tests for Obsidian destination."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from destinations.obsidian import ObsidianDestination


@pytest.fixture
def obsidian_vault(temp_dir):
    """Create a mock Obsidian vault."""
    vault_path = temp_dir / "ObsidianVault"
    vault_path.mkdir()
    (vault_path / ".obsidian").mkdir()
    return vault_path


@pytest.fixture
def obsidian_config(obsidian_vault):
    """Configuration for Obsidian destination."""
    return {
        "vault_path": str(obsidian_vault),
        "folder": "Voice Memos",
        "organize_by": "daily",
        "date_format": "%Y-%m-%d",
        "include_frontmatter": True,
        "include_tags": True,
        "include_metadata": True,
    }


@pytest.fixture
def obsidian_dest(obsidian_config, config_dir):
    """Create an ObsidianDestination instance."""
    return ObsidianDestination(obsidian_config, str(config_dir))


@pytest.mark.unit
class TestObsidianValidation:
    """Test configuration validation."""

    def test_validate_config_missing_vault_path(self, config_dir):
        """Test validation fails when vault_path is missing."""
        config = {}
        dest = ObsidianDestination(config, str(config_dir))

        with pytest.raises(ValueError, match="vault_path is required"):
            dest.validate_config()

    def test_validate_config_vault_not_exists(self, temp_dir, config_dir):
        """Test validation fails when vault doesn't exist."""
        config = {"vault_path": str(temp_dir / "nonexistent")}
        dest = ObsidianDestination(config, str(config_dir))

        with pytest.raises(FileNotFoundError, match="Vault path does not exist"):
            dest.validate_config()

    def test_validate_config_not_directory(self, temp_dir, config_dir):
        """Test validation fails when vault path is a file."""
        file_path = temp_dir / "notadir.txt"
        file_path.touch()

        config = {"vault_path": str(file_path)}
        dest = ObsidianDestination(config, str(config_dir))

        with pytest.raises(ValueError, match="not a directory"):
            dest.validate_config()

    def test_validate_config_not_obsidian_vault(self, temp_dir, config_dir):
        """Test validation fails when directory is not an Obsidian vault."""
        vault_path = temp_dir / "NotAVault"
        vault_path.mkdir()

        config = {"vault_path": str(vault_path)}
        dest = ObsidianDestination(config, str(config_dir))

        with pytest.raises(ValueError, match="Not a valid Obsidian vault"):
            dest.validate_config()

    def test_validate_config_success(self, obsidian_dest):
        """Test validation succeeds with valid vault."""
        obsidian_dest.validate_config()


@pytest.mark.unit
class TestObsidianInitialization:
    """Test initialization."""

    def test_initialize_creates_folder(self, obsidian_dest, obsidian_vault):
        """Test that initialize creates the folder."""
        obsidian_dest.initialize()

        folder_path = obsidian_vault / "Voice Memos"
        assert folder_path.exists()
        assert folder_path.is_dir()

    def test_initialize_with_existing_folder(self, obsidian_dest, obsidian_vault):
        """Test initialize works with existing folder."""
        folder_path = obsidian_vault / "Voice Memos"
        folder_path.mkdir()

        obsidian_dest.initialize()

        assert folder_path.exists()


@pytest.mark.unit
class TestFileCreation:
    """Test file creation."""

    def test_prepare_for_memo_daily(self, obsidian_dest, obsidian_vault):
        """Test preparing for a memo in daily mode."""
        obsidian_dest.initialize()
        memo_date = datetime(2025, 1, 30, 14, 30, 0)

        file_path = obsidian_dest.prepare_for_memo(memo_date)

        expected_path = obsidian_vault / "Voice Memos" / "2025-01-30.md"
        assert file_path == str(expected_path)
        assert expected_path.exists()

    def test_prepare_for_memo_weekly(self, obsidian_vault, config_dir):
        """Test preparing for a memo in weekly mode."""
        config = {
            "vault_path": str(obsidian_vault),
            "folder": "Voice Memos",
            "organize_by": "weekly",
        }
        dest = ObsidianDestination(config, str(config_dir))
        dest.initialize()

        memo_date = datetime(2025, 1, 30, 14, 30, 0)  # Thursday
        file_path = dest.prepare_for_memo(memo_date)

        # Should create file for Monday (2025-01-27)
        expected_path = obsidian_vault / "Voice Memos" / "2025-01-27 Week.md"
        assert file_path == str(expected_path)
        assert expected_path.exists()

    def test_prepare_for_memo_custom_date_format(self, obsidian_vault, config_dir):
        """Test preparing with custom date format."""
        config = {
            "vault_path": str(obsidian_vault),
            "folder": "Memos",
            "date_format": "%Y%m%d",
        }
        dest = ObsidianDestination(config, str(config_dir))
        dest.initialize()

        memo_date = datetime(2025, 1, 30, 14, 30, 0)
        file_path = dest.prepare_for_memo(memo_date)

        expected_path = obsidian_vault / "Memos" / "20250130.md"
        assert file_path == str(expected_path)


@pytest.mark.unit
class TestFrontmatter:
    """Test frontmatter generation."""

    def test_file_has_frontmatter(self, obsidian_dest, obsidian_vault):
        """Test that created file has frontmatter."""
        obsidian_dest.initialize()
        memo_date = datetime(2025, 1, 30)

        file_path = obsidian_dest.prepare_for_memo(memo_date)

        with open(file_path, "r") as f:
            content = f.read()

        assert content.startswith("---\n")
        assert "date: 2025-01-30" in content
        assert "type: voice-memo-transcript" in content
        assert "tags: [voice-memo]" in content
        assert "memo_count: 0" in content

    def test_weekly_file_has_week_number(self, obsidian_vault, config_dir):
        """Test that weekly file includes week number."""
        config = {
            "vault_path": str(obsidian_vault),
            "organize_by": "weekly",
        }
        dest = ObsidianDestination(config, str(config_dir))
        dest.initialize()

        memo_date = datetime(2025, 1, 30)
        file_path = dest.prepare_for_memo(memo_date)

        with open(file_path, "r") as f:
            content = f.read()

        assert "week: 2025-W05" in content

    def test_no_frontmatter_when_disabled(self, obsidian_vault, config_dir):
        """Test file has no frontmatter when disabled."""
        config = {
            "vault_path": str(obsidian_vault),
            "include_frontmatter": False,
        }
        dest = ObsidianDestination(config, str(config_dir))
        dest.initialize()

        memo_date = datetime(2025, 1, 30)
        file_path = dest.prepare_for_memo(memo_date)

        with open(file_path, "r") as f:
            content = f.read()

        assert not content.startswith("---\n")
        assert content.startswith("# Voice Memos")


@pytest.mark.unit
class TestTranscriptAppend:
    """Test appending transcripts."""

    def test_append_transcript_basic(self, obsidian_dest, obsidian_vault):
        """Test appending a basic transcript."""
        obsidian_dest.initialize()
        memo_date = datetime(2025, 1, 30, 14, 30, 0)

        file_path = obsidian_dest.prepare_for_memo(memo_date)

        obsidian_dest.append_transcript(
            file_path,
            "Test Memo.m4a",
            "2025-01-30 14:30:00",
            "This is the transcript text.",
            memo_date,
            "/path/to/test.m4a",
        )

        with open(file_path, "r") as f:
            content = f.read()

        assert "## Test Memo.m4a" in content
        assert "**Recorded:** 2025-01-30 14:30:00" in content
        assert "This is the transcript text." in content

    @patch("destinations.obsidian.extract_audio_metadata")
    def test_append_transcript_with_metadata(
        self, mock_extract, obsidian_dest, obsidian_vault
    ):
        """Test appending transcript with metadata."""
        mock_extract.return_value = {
            "title": "Meeting Notes",
            "duration": 204.5,
            "device": "iPhone Version 18.1.1",
        }

        obsidian_dest.initialize()
        memo_date = datetime(2025, 1, 30, 14, 30, 0)

        file_path = obsidian_dest.prepare_for_memo(memo_date)

        obsidian_dest.append_transcript(
            file_path,
            "Test.m4a",
            "2025-01-30 14:30:00",
            "Transcript here.",
            memo_date,
            "/path/to/test.m4a",
        )

        with open(file_path, "r") as f:
            content = f.read()

        assert "## Meeting Notes" in content
        assert "**Duration:** 3m 24s" in content
        assert "**Device:** iPhone Version 18.1.1" in content

    def test_append_multiple_transcripts(self, obsidian_dest, obsidian_vault):
        """Test appending multiple transcripts to same file."""
        obsidian_dest.initialize()
        memo_date = datetime(2025, 1, 30, 14, 30, 0)

        file_path = obsidian_dest.prepare_for_memo(memo_date)

        # Append first
        obsidian_dest.append_transcript(
            file_path,
            "First.m4a",
            "2025-01-30 14:30:00",
            "First transcript.",
            memo_date,
            "/path/to/first.m4a",
        )

        # Append second
        obsidian_dest.append_transcript(
            file_path,
            "Second.m4a",
            "2025-01-30 15:00:00",
            "Second transcript.",
            memo_date,
            "/path/to/second.m4a",
        )

        with open(file_path, "r") as f:
            content = f.read()

        assert "First transcript." in content
        assert "Second transcript." in content


@pytest.mark.unit
class TestMemoCount:
    """Test memo counting."""

    def test_memo_count_updates(self, obsidian_dest, obsidian_vault):
        """Test that memo_count is updated in frontmatter."""
        obsidian_dest.initialize()
        memo_date = datetime(2025, 1, 30, 14, 30, 0)

        file_path = obsidian_dest.prepare_for_memo(memo_date)

        # Append first memo
        obsidian_dest.append_transcript(
            file_path,
            "First.m4a",
            "2025-01-30 14:30:00",
            "First.",
            memo_date,
            "/path/to/first.m4a",
        )

        with open(file_path, "r") as f:
            content = f.read()

        assert "memo_count: 1" in content

        # Append second memo
        obsidian_dest.append_transcript(
            file_path,
            "Second.m4a",
            "2025-01-30 15:00:00",
            "Second.",
            memo_date,
            "/path/to/second.m4a",
        )

        with open(file_path, "r") as f:
            content = f.read()

        assert "memo_count: 2" in content


@pytest.mark.unit
class TestCleanup:
    """Test cleanup."""

    def test_cleanup_prints_vault_path(self, obsidian_dest, capsys):
        """Test cleanup prints vault location."""
        obsidian_dest.initialize()

        obsidian_dest.cleanup()

        captured = capsys.readouterr()
        assert "Transcripts saved to Obsidian vault" in captured.out
        assert "Voice Memos" in captured.out
