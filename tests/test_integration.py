"""End-to-end integration tests."""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transcribe_memos import find_new_memos


@pytest.mark.integration
class TestFindNewMemos:
    """Test finding new voice memos."""

    def test_find_new_memos_empty_directory(self, temp_dir, monkeypatch, mock_config):
        """Test finding memos in empty directory."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        result = find_new_memos()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_find_new_memos_with_files(self, voice_memos_list, temp_dir, monkeypatch, mock_config):
        """Test finding memos with existing files."""
        mock_config["voice_memos_path"] = str(temp_dir / "voice_memos")
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        result = find_new_memos()

        assert isinstance(result, list)
        assert len(result) == 3

        # Verify structure of result
        for filepath, filename, memo_datetime in result:
            assert os.path.exists(filepath)
            assert isinstance(filename, str)
            assert isinstance(memo_datetime, datetime)

    def test_find_new_memos_skips_processed(self, voice_memos_list, temp_dir, processed_memos_file, monkeypatch, mock_config):
        """Test that processed memos are skipped."""
        mock_config["voice_memos_path"] = str(temp_dir / "voice_memos")
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        # Get first memo and mark it as processed
        from transcribe_memos import get_file_hash, save_processed_memos

        first_memo = str(voice_memos_list[0])
        hash1 = get_file_hash(first_memo)

        processed = {hash1}
        save_processed_memos(processed)

        result = find_new_memos()

        # Should find 2 memos (3 total - 1 processed)
        assert len(result) == 2

    def test_find_new_memos_sorted_by_time(self, temp_dir, monkeypatch, mock_config):
        """Test that memos are sorted by modification time."""
        memos_dir = temp_dir / "voice_memos"
        memos_dir.mkdir(parents=True, exist_ok=True)
        mock_config["voice_memos_path"] = str(memos_dir)
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        # Create files with different timestamps
        import time
        files = []
        for i in range(3):
            file_path = memos_dir / f"memo_{i}.m4a"
            with open(file_path, "wb") as f:
                f.write(b"test" * 1000)
            files.append(file_path)
            time.sleep(0.01)  # Ensure different mtimes

        result = find_new_memos()

        # Should be sorted oldest to newest
        assert len(result) == 3
        timestamps = [memo[2] for memo in result]
        assert timestamps == sorted(timestamps)


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.skip(reason="Deprecated - replaced by tests/test_destination_integration.py")
    @patch('transcribe_memos.OpenAI')
    @patch('transcribe_memos.build')
    @patch('transcribe_memos.get_google_credentials')
    @patch('transcribe_memos.validate_audio_file')
    def test_complete_transcription_workflow(
        self,
        mock_validate,
        mock_get_creds,
        mock_build,
        mock_openai_class,
        voice_memos_list,
        temp_dir,
        config_dir,
        monkeypatch,
        mock_config
    ):
        """Test complete workflow from finding memos to transcribing and saving."""
        # Setup
        mock_config["voice_memos_path"] = str(temp_dir / "voice_memos")
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        # Mock validation
        mock_validate.return_value = (True, "")

        # Mock credentials
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_get_creds.return_value = mock_creds

        # Mock Google Docs service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_create = MagicMock()
        mock_create.execute.return_value = {"documentId": "test-doc-id"}
        mock_service.documents().create.return_value = mock_create

        mock_get = MagicMock()
        mock_get.execute.return_value = {
            "body": {"content": [{"endIndex": 1}, {"endIndex": 100}]}
        }
        mock_service.documents().get.return_value = mock_get

        mock_update = MagicMock()
        mock_update.execute.return_value = {}
        mock_service.documents().batchUpdate.return_value = mock_update

        # Mock OpenAI
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test transcription"
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Execute workflow
        from transcribe_memos import (
            find_new_memos,
            get_or_create_doc,
            transcribe_openai,
            append_to_doc,
            get_file_hash,
            save_processed_memos,
        )

        new_memos = find_new_memos()
        assert len(new_memos) == 3

        processed = set()
        for filepath, filename, memo_datetime in new_memos[:1]:  # Process just first one
            # Get/create doc
            doc_id = get_or_create_doc(mock_service, memo_datetime)
            assert doc_id == "test-doc-id"

            # Transcribe
            transcript = transcribe_openai(filepath)
            assert transcript == "Test transcription"

            # Append to doc
            timestamp_str = memo_datetime.strftime("%Y-%m-%d %H:%M:%S")
            append_to_doc(mock_service, doc_id, filename, timestamp_str, transcript)

            # Mark as processed
            file_hash = get_file_hash(filepath)
            processed.add(file_hash)

        save_processed_memos(processed)

        # Verify processed file was created
        processed_path = config_dir / "processed.json"
        assert processed_path.exists()

        with open(processed_path) as f:
            data = json.load(f)
        assert len(data) == 1


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery scenarios."""

    @pytest.mark.skip(reason="Deprecated - replaced by tests/test_destination_integration.py")
    @patch('transcribe_memos.OpenAI')
    @patch('transcribe_memos.validate_audio_file')
    def test_corrupted_file_handling(self, mock_validate, mock_openai, corrupted_audio_file, monkeypatch, mock_config):
        """Test that corrupted files are handled gracefully."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)
        mock_validate.return_value = (False, "moov atom not found")

        from transcribe_memos import transcribe_openai

        with pytest.raises(ValueError, match="Corrupted audio file"):
            transcribe_openai(str(corrupted_audio_file))

        # OpenAI should not be called for corrupted files
        mock_openai.assert_not_called()

    def test_empty_file_detection(self, empty_audio_file):
        """Test that empty files are detected."""
        size = os.path.getsize(empty_audio_file)
        assert size == 0

        # Verify this would be caught by size check
        assert size < 1000

    @patch('transcribe_memos.validate_audio_file')
    def test_processed_tracking_persists(self, mock_validate, voice_memos_list, config_dir, monkeypatch, mock_config):
        """Test that processed tracking persists across runs."""
        mock_config["voice_memos_path"] = str(voice_memos_list[0].parent)
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        from transcribe_memos import (
            get_file_hash,
            save_processed_memos,
            get_processed_memos,
            find_new_memos
        )

        # Process first memo
        first_memo = str(voice_memos_list[0])
        hash1 = get_file_hash(first_memo)
        save_processed_memos({hash1})

        # "Restart" - load processed memos
        processed = get_processed_memos()
        assert hash1 in processed

        # Find new memos should skip the processed one
        new_memos = find_new_memos()
        new_memo_paths = [path for path, _, _ in new_memos]
        assert first_memo not in new_memo_paths
