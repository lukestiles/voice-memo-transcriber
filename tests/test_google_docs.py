"""Unit tests for Google Docs integration."""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transcribe_memos import (
    get_or_create_doc,
    append_to_doc,
)


@pytest.mark.unit
class TestDocumentCreation:
    """Test Google Doc creation."""

    def test_get_or_create_doc_new(self, mock_google_service, config_dir, monkeypatch, mock_config, sample_memo_datetime):
        """Test creating a new document."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        # Mock the documents().create() chain
        mock_create = MagicMock()
        mock_create.execute.return_value = {"documentId": "new-doc-id"}
        mock_google_service.documents().create.return_value = mock_create

        result = get_or_create_doc(mock_google_service, sample_memo_datetime)

        assert result == "new-doc-id"
        mock_google_service.documents().create.assert_called_once()

    def test_get_or_create_doc_existing(self, mock_google_service, docs_by_week_file, monkeypatch, mock_config):
        """Test using existing document for the week."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        # Date that matches existing doc
        date = datetime(2025, 1, 30)  # Monday is 2025-01-27

        result = get_or_create_doc(mock_google_service, date)

        assert result == "doc-id-1"
        # Should not create a new document
        mock_google_service.documents().create.assert_not_called()

    def test_get_or_create_doc_config_override(self, mock_google_service, monkeypatch, mock_config, sample_memo_datetime):
        """Test that CONFIG google_doc_id takes precedence."""
        mock_config["google_doc_id"] = "override-doc-id"
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        result = get_or_create_doc(mock_google_service, sample_memo_datetime)

        assert result == "override-doc-id"
        mock_google_service.documents().create.assert_not_called()

    def test_get_or_create_doc_saves_mapping(self, mock_google_service, config_dir, monkeypatch, mock_config, sample_memo_datetime):
        """Test that doc mapping is saved."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        mock_create = MagicMock()
        mock_create.execute.return_value = {"documentId": "saved-doc-id"}
        mock_google_service.documents().create.return_value = mock_create

        get_or_create_doc(mock_google_service, sample_memo_datetime)

        # Check that mapping file was created
        docs_path = config_dir / "docs_by_week.json"
        assert docs_path.exists()

        with open(docs_path) as f:
            data = json.load(f)

        assert "2025-01-27" in data
        assert data["2025-01-27"] == "saved-doc-id"


@pytest.mark.unit
class TestDocumentAppend:
    """Test appending to Google Docs."""

    def test_append_to_doc_success(self, mock_google_service):
        """Test successful append to document."""
        doc_id = "test-doc-123"
        memo_name = "Test Memo"
        timestamp = "2025-01-30 14:30:00"
        transcript = "This is the test transcript text."

        # Mock the get() chain for getting document length
        mock_get = MagicMock()
        mock_get.execute.return_value = {
            "body": {
                "content": [
                    {"endIndex": 1},
                    {"endIndex": 500}
                ]
            }
        }
        mock_google_service.documents().get.return_value = mock_get

        # Mock the batchUpdate() chain
        mock_update = MagicMock()
        mock_update.execute.return_value = {}
        mock_google_service.documents().batchUpdate.return_value = mock_update

        # Execute
        append_to_doc(mock_google_service, doc_id, memo_name, timestamp, transcript)

        # Verify
        mock_google_service.documents().get.assert_called_once()
        mock_google_service.documents().batchUpdate.assert_called_once()

        # Verify the batch update was called with correct doc_id
        call_args = mock_google_service.documents().batchUpdate.call_args
        assert call_args[1]["documentId"] == doc_id

    def test_append_to_doc_includes_content(self, mock_google_service):
        """Test that append includes memo name, timestamp, and transcript."""
        doc_id = "test-doc"
        memo_name = "Important Memo"
        timestamp = "2025-01-30 14:30:00"
        transcript = "Meeting notes here."

        mock_get = MagicMock()
        mock_get.execute.return_value = {
            "body": {"content": [{"endIndex": 1}, {"endIndex": 100}]}
        }
        mock_google_service.documents().get.return_value = mock_get

        mock_update = MagicMock()
        mock_update.execute.return_value = {}
        mock_google_service.documents().batchUpdate.return_value = mock_update

        append_to_doc(mock_google_service, doc_id, memo_name, timestamp, transcript)

        # Get the call arguments
        call_args = mock_google_service.documents().batchUpdate.call_args
        requests = call_args[1]["body"]["requests"]

        # Verify insertText request exists
        assert len(requests) > 0
        insert_request = requests[0]
        assert "insertText" in insert_request

        # Verify content includes key information
        text = insert_request["insertText"]["text"]
        assert memo_name in text
        assert timestamp in text
        assert transcript in text

    def test_append_to_doc_error_handling(self, mock_google_service):
        """Test error handling when append fails."""
        doc_id = "test-doc"

        # Mock get to fail
        mock_google_service.documents().get.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            append_to_doc(mock_google_service, doc_id, "Memo", "2025-01-30", "Text")


@pytest.mark.integration
class TestGoogleDocsIntegration:
    """Integration tests for Google Docs operations."""

    @patch('transcribe_memos.get_google_credentials')
    @patch('transcribe_memos.build')
    def test_full_doc_workflow(self, mock_build, mock_get_creds, config_dir, monkeypatch, mock_config, sample_memo_datetime):
        """Test complete document creation and append workflow."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        # Mock credentials
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_get_creds.return_value = mock_creds

        # Mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock document creation
        mock_create = MagicMock()
        mock_create.execute.return_value = {"documentId": "integration-test-doc"}
        mock_service.documents().create.return_value = mock_create

        # Mock document get
        mock_get = MagicMock()
        mock_get.execute.return_value = {
            "body": {"content": [{"endIndex": 1}, {"endIndex": 100}]}
        }
        mock_service.documents().get.return_value = mock_get

        # Mock batch update
        mock_update = MagicMock()
        mock_update.execute.return_value = {}
        mock_service.documents().batchUpdate.return_value = mock_update

        # Execute full workflow
        doc_id = get_or_create_doc(mock_service, sample_memo_datetime)
        append_to_doc(mock_service, doc_id, "Test Memo", "2025-01-30 14:30", "Test transcript")

        # Verify
        assert doc_id == "integration-test-doc"
        mock_service.documents().create.assert_called_once()
        mock_service.documents().get.assert_called_once()
        mock_service.documents().batchUpdate.assert_called_once()
