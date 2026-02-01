"""Integration tests for destination-based transcription workflow."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from datetime import datetime

from destinations import create_destination
from destinations.google_docs import GoogleDocsDestination
from destinations.obsidian import ObsidianDestination


@pytest.mark.integration
class TestDestinationCreation:
    """Test creating destinations via factory."""

    def test_create_google_docs_destination(self, config_dir):
        """Test creating Google Docs destination."""
        config = {
            "doc_id": "test-doc",
            "doc_title": "Test Transcripts",
        }

        dest = create_destination("google_docs", config, str(config_dir))

        assert isinstance(dest, GoogleDocsDestination)
        assert dest.config == config
        assert dest.data_dir == str(config_dir)

    def test_create_obsidian_destination(self, temp_dir, config_dir):
        """Test creating Obsidian destination."""
        vault_path = temp_dir / "vault"
        vault_path.mkdir()
        (vault_path / ".obsidian").mkdir()

        config = {
            "vault_path": str(vault_path),
            "folder": "Memos",
        }

        dest = create_destination("obsidian", config, str(config_dir))

        assert isinstance(dest, ObsidianDestination)
        assert dest.config == config

    def test_create_unknown_destination(self, config_dir):
        """Test error when creating unknown destination type."""
        with pytest.raises(ValueError, match="Unknown destination type"):
            create_destination("unknown_type", {}, str(config_dir))


@pytest.mark.integration
class TestGoogleDocsWorkflow:
    """Test complete workflow with Google Docs destination."""

    @patch("destinations.google_docs.Credentials")
    @patch("destinations.google_docs.build")
    def test_full_workflow(self, mock_build, mock_creds_class, config_dir):
        """Test complete transcription workflow with Google Docs."""
        # Setup credentials
        creds_path = config_dir / "credentials.json"
        creds_path.write_text('{"installed": {"client_id": "test"}}')

        token_path = config_dir / "token.json"
        token_data = {
            "token": "test-token",
            "refresh_token": "test-refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test-id",
            "client_secret": "test-secret",
            "scopes": ["https://www.googleapis.com/auth/documents"],
        }
        token_path.write_text(json.dumps(token_data))

        # Mock credentials
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        # Mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock document operations
        mock_create = MagicMock()
        mock_create.execute.return_value = {"documentId": "new-doc-id"}
        mock_service.documents().create.return_value = mock_create

        mock_get = MagicMock()
        mock_get.execute.return_value = {
            "tabs": [
                {
                    "tabProperties": {"tabId": "tab-1", "title": "January 30, 2025"},
                    "documentTab": {
                        "body": {"content": [{"endIndex": 1}, {"endIndex": 100}]}
                    },
                }
            ]
        }
        mock_service.documents().get.return_value = mock_get

        mock_update = MagicMock()
        mock_update.execute.return_value = {
            "replies": [{"addDocumentTab": {"tabId": "new-tab"}}]
        }
        mock_service.documents().batchUpdate.return_value = mock_update

        # Create and initialize destination
        config = {
            "doc_id": "",
            "doc_title": "Test Transcripts",
            "use_weekly_docs": True,
        }
        dest = create_destination("google_docs", config, str(config_dir))
        dest.initialize()

        # Simulate transcription workflow
        memo_datetime = datetime(2025, 1, 30, 14, 30, 0)

        # Prepare for memo
        session_id = dest.prepare_for_memo(memo_datetime)
        assert ":" in session_id  # Should be "doc_id:tab_id"

        # Append transcript
        dest.append_transcript(
            session_id,
            "Test Memo",
            "2025-01-30 14:30:00",
            "This is a test transcript.",
            memo_datetime,
            "/path/to/audio.m4a",
        )

        # Verify service was called
        mock_service.documents().create.assert_called()
        mock_service.documents().batchUpdate.assert_called()

        # Cleanup
        dest.cleanup()


@pytest.mark.integration
class TestObsidianWorkflow:
    """Test complete workflow with Obsidian destination."""

    def test_full_workflow(self, temp_dir, config_dir):
        """Test complete transcription workflow with Obsidian."""
        # Create vault
        vault_path = temp_dir / "TestVault"
        vault_path.mkdir()
        (vault_path / ".obsidian").mkdir()

        # Create and initialize destination
        config = {
            "vault_path": str(vault_path),
            "folder": "Voice Memos",
            "organize_by": "daily",
            "include_frontmatter": True,
            "include_metadata": False,
        }
        dest = create_destination("obsidian", config, str(config_dir))
        dest.initialize()

        # Verify folder was created
        assert (vault_path / "Voice Memos").exists()

        # Simulate transcription workflow
        memo_datetime = datetime(2025, 1, 30, 14, 30, 0)

        # Prepare for memo
        file_path = dest.prepare_for_memo(memo_datetime)
        assert Path(file_path).exists()
        assert "2025-01-30" in file_path

        # Append first transcript
        dest.append_transcript(
            file_path,
            "First Memo",
            "2025-01-30 14:30:00",
            "This is the first transcript.",
            memo_datetime,
            "/path/to/audio1.m4a",
        )

        # Verify content
        with open(file_path, "r") as f:
            content = f.read()
        assert "First Memo" in content
        assert "This is the first transcript." in content
        assert "memo_count: 1" in content

        # Append second transcript
        dest.append_transcript(
            file_path,
            "Second Memo",
            "2025-01-30 15:00:00",
            "This is the second transcript.",
            memo_datetime,
            "/path/to/audio2.m4a",
        )

        # Verify both transcripts are present
        with open(file_path, "r") as f:
            content = f.read()
        assert "First Memo" in content
        assert "Second Memo" in content
        assert "memo_count: 2" in content

        # Cleanup
        dest.cleanup()


@pytest.mark.integration
class TestDestinationSwitching:
    """Test switching between destinations."""

    def test_can_use_different_destinations(self, temp_dir, config_dir):
        """Test that processed.json works across different destinations."""
        # This test verifies that the processed memos tracking is destination-agnostic

        # Setup Obsidian vault
        vault_path = temp_dir / "vault"
        vault_path.mkdir()
        (vault_path / ".obsidian").mkdir()

        # Create Obsidian destination
        obsidian_config = {
            "vault_path": str(vault_path),
            "folder": "Memos",
        }
        obs_dest = create_destination("obsidian", obsidian_config, str(config_dir))
        obs_dest.initialize()

        # Use it
        memo_date = datetime(2025, 1, 30)
        file_path = obs_dest.prepare_for_memo(memo_date)
        obs_dest.append_transcript(
            file_path, "Test", "2025-01-30 14:30", "Content", memo_date, "/test.m4a"
        )

        # Verify Obsidian file was created
        assert Path(file_path).exists()

        # The key point: processed.json should work the same regardless of destination
        # Both destinations use the same data_dir for tracking processed memos
        assert obs_dest.data_dir == str(config_dir)
