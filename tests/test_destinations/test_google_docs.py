"""Tests for Google Docs destination."""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from destinations.google_docs import GoogleDocsDestination


@pytest.fixture
def google_config():
    """Configuration for Google Docs destination."""
    return {
        "doc_id": "",
        "doc_title": "Test Voice Memo Transcripts",
        "tab_date_format": "%B %d, %Y",
        "use_weekly_docs": True,
    }


@pytest.fixture
def google_dest(google_config, config_dir):
    """Create a GoogleDocsDestination instance."""
    return GoogleDocsDestination(google_config, str(config_dir))


@pytest.fixture
def mock_service():
    """Mock Google Docs service."""
    mock = MagicMock()

    # Mock document creation
    mock_create = MagicMock()
    mock_create.execute.return_value = {"documentId": "test-doc-id-123"}
    mock.documents().create.return_value = mock_create

    # Mock document get for tab operations
    mock_get = MagicMock()
    mock_get.execute.return_value = {
        "tabs": [
            {
                "tabProperties": {
                    "tabId": "tab-1",
                    "title": "January 30, 2025"
                },
                "documentTab": {
                    "body": {
                        "content": [
                            {"endIndex": 1},
                            {"endIndex": 100}
                        ]
                    }
                }
            }
        ]
    }
    mock.documents().get.return_value = mock_get

    # Mock batch update
    mock_update = MagicMock()
    mock_update.execute.return_value = {
        "replies": [
            {
                "addDocumentTab": {
                    "tabId": "new-tab-id"
                }
            }
        ]
    }
    mock.documents().batchUpdate.return_value = mock_update

    return mock


@pytest.mark.unit
class TestGoogleDocsValidation:
    """Test configuration validation."""

    def test_validate_config_missing_credentials(self, google_dest):
        """Test validation fails when credentials.json is missing."""
        with pytest.raises(FileNotFoundError, match="Google credentials not found"):
            google_dest.validate_config()

    def test_validate_config_success(self, google_dest, config_dir):
        """Test validation succeeds with credentials present."""
        # Create dummy credentials file
        creds_path = config_dir / "credentials.json"
        creds_path.write_text('{"installed": {}}')

        google_dest.validate_config()


@pytest.mark.unit
class TestGoogleDocsInitialization:
    """Test initialization."""

    @patch('destinations.google_docs.build')
    @patch('destinations.google_docs.Credentials')
    def test_initialize(self, mock_creds_class, mock_build, google_dest, config_dir):
        """Test that initialize sets up the service."""
        # Create dummy credentials
        creds_path = config_dir / "credentials.json"
        creds_path.write_text('{"installed": {"client_id": "test"}}')

        token_path = config_dir / "token.json"
        token_data = {
            "token": "test-token",
            "refresh_token": "test-refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "scopes": ["https://www.googleapis.com/auth/documents"]
        }
        token_path.write_text(json.dumps(token_data))

        # Mock credentials to be valid
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        google_dest.initialize()

        assert google_dest.service is not None
        mock_build.assert_called_once_with("docs", "v1", credentials=mock_creds)


@pytest.mark.unit
class TestDocumentCreation:
    """Test document creation."""

    def test_get_or_create_doc_new(self, google_dest, config_dir, mock_service):
        """Test creating a new document."""
        google_dest.service = mock_service
        memo_date = datetime(2025, 1, 30)

        doc_id = google_dest._get_or_create_doc(memo_date)

        assert doc_id == "test-doc-id-123"
        mock_service.documents().create.assert_called_once()

    def test_get_or_create_doc_existing(self, google_dest, config_dir, mock_service):
        """Test using existing document for the week."""
        google_dest.service = mock_service

        # Create existing mapping
        docs_path = config_dir / "docs_by_week.json"
        docs_path.write_text(json.dumps({"2025-01-27": "existing-doc-id"}))

        # Date in the same week
        memo_date = datetime(2025, 1, 30)

        doc_id = google_dest._get_or_create_doc(memo_date)

        assert doc_id == "existing-doc-id"
        mock_service.documents().create.assert_not_called()

    def test_get_or_create_doc_config_override(self, config_dir, mock_service):
        """Test that doc_id config takes precedence."""
        config = {
            "doc_id": "override-doc-id",
            "use_weekly_docs": True,
        }
        dest = GoogleDocsDestination(config, str(config_dir))
        dest.service = mock_service

        memo_date = datetime(2025, 1, 30)
        doc_id = dest._get_or_create_doc(memo_date)

        assert doc_id == "override-doc-id"
        mock_service.documents().create.assert_not_called()

    def test_get_or_create_doc_single_mode(self, config_dir, mock_service):
        """Test single document mode."""
        config = {
            "doc_title": "My Transcripts",
            "use_weekly_docs": False,
        }
        dest = GoogleDocsDestination(config, str(config_dir))
        dest.service = mock_service

        memo_date = datetime(2025, 1, 30)
        doc_id = dest._get_or_create_doc(memo_date)

        assert doc_id == "test-doc-id-123"

        # Check saved mapping uses structured format
        docs_path = config_dir / "docs_by_week.json"
        with open(docs_path) as f:
            data = json.load(f)
        assert data["mode"] == "single"
        assert data["single"] == "test-doc-id-123"


@pytest.mark.unit
class TestTabOperations:
    """Test tab creation and operations."""

    def test_get_existing_tabs(self, google_dest, mock_service):
        """Test retrieving existing tabs."""
        google_dest.service = mock_service

        tabs = google_dest._get_existing_tabs("test-doc-id")

        assert "January 30, 2025" in tabs
        assert tabs["January 30, 2025"] == "tab-1"

    def test_get_or_create_tab_existing(self, google_dest, mock_service):
        """Test using existing tab."""
        google_dest.service = mock_service
        memo_date = datetime(2025, 1, 30)

        tab_id = google_dest._get_or_create_tab_for_date("test-doc-id", memo_date)

        assert tab_id == "tab-1"

    def test_get_or_create_tab_new(self, google_dest, mock_service):
        """Test creating new tab."""
        google_dest.service = mock_service

        # Mock empty tabs
        mock_get = MagicMock()
        mock_get.execute.return_value = {"tabs": []}
        mock_service.documents().get.return_value = mock_get

        memo_date = datetime(2025, 2, 1)
        tab_id = google_dest._get_or_create_tab_for_date("test-doc-id", memo_date)

        assert tab_id == "new-tab-id"
        # Should have called batchUpdate twice (create tab + add header)
        assert mock_service.documents().batchUpdate.call_count == 2


@pytest.mark.unit
class TestTranscriptAppend:
    """Test appending transcripts."""

    def test_append_to_tab(self, google_dest, mock_service):
        """Test appending transcript to tab."""
        google_dest.service = mock_service

        google_dest._append_to_tab(
            "test-doc-id",
            "tab-1",
            "Test Memo",
            "2025-01-30 14:30:00",
            "This is the transcript."
        )

        # Verify batchUpdate was called
        mock_service.documents().batchUpdate.assert_called_once()

        # Verify the content includes memo info
        call_args = mock_service.documents().batchUpdate.call_args
        requests = call_args[1]["body"]["requests"]
        assert len(requests) > 0

        text = requests[0]["insertText"]["text"]
        assert "Test Memo" in text
        assert "2025-01-30 14:30:00" in text
        assert "This is the transcript." in text


@pytest.mark.unit
class TestDestinationInterface:
    """Test the full destination interface."""

    def test_prepare_for_memo(self, google_dest, mock_service):
        """Test preparing for a memo."""
        google_dest.service = mock_service
        memo_date = datetime(2025, 1, 30)

        session_id = google_dest.prepare_for_memo(memo_date)

        assert ":" in session_id
        doc_id, tab_id = session_id.split(":", 1)
        assert doc_id
        assert tab_id

    def test_append_transcript(self, google_dest, mock_service):
        """Test appending transcript via interface."""
        google_dest.service = mock_service

        session_id = "test-doc:test-tab"
        google_dest.append_transcript(
            session_id,
            "My Memo",
            "2025-01-30 14:30",
            "Transcript text here",
            datetime(2025, 1, 30),
            "/path/to/audio.m4a"
        )

        mock_service.documents().batchUpdate.assert_called()

    def test_cleanup_no_docs(self, google_dest, capsys):
        """Test cleanup with no docs created."""
        google_dest.cleanup()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_cleanup_with_docs(self, google_dest, capsys):
        """Test cleanup with docs created."""
        google_dest.docs_created = [
            ("doc-1", "Week 1 Transcripts"),
            ("doc-2", "Week 2 Transcripts"),
        ]

        google_dest.cleanup()

        captured = capsys.readouterr()
        assert "Google Docs created:" in captured.out
        assert "Week 1 Transcripts" in captured.out
        assert "doc-1" in captured.out
