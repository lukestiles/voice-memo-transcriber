"""Unit tests for transcription functionality."""

import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transcribe_memos import (
    transcribe_openai,
    split_audio_file,
    validate_audio_file,
)


@pytest.mark.unit
class TestTranscriptionOpenAI:
    """Test OpenAI transcription."""

    @patch('transcribe_memos.OpenAI')
    @patch('transcribe_memos.validate_audio_file')
    def test_transcribe_openai_success(self, mock_validate, mock_openai_class, sample_audio_file, monkeypatch, mock_config):
        """Test successful OpenAI transcription."""
        # Setup
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)
        mock_validate.return_value = (True, "")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test transcription text"
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Execute
        result = transcribe_openai(str(sample_audio_file))

        # Verify
        assert result == "Test transcription text"
        mock_client.audio.transcriptions.create.assert_called_once()

    @patch('transcribe_memos.validate_audio_file')
    def test_transcribe_openai_no_api_key(self, mock_validate, sample_audio_file, monkeypatch, mock_config):
        """Test transcription fails without API key."""
        mock_validate.return_value = (True, "")
        mock_config["openai_api_key"] = ""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        with pytest.raises(ValueError, match="OpenAI API key not set"):
            transcribe_openai(str(sample_audio_file))

    @patch('transcribe_memos.validate_audio_file')
    def test_transcribe_openai_invalid_file(self, mock_validate, corrupted_audio_file, monkeypatch, mock_config):
        """Test transcription fails for invalid file."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)
        mock_validate.return_value = (False, "File is corrupted")

        with pytest.raises(ValueError, match="Corrupted audio file"):
            transcribe_openai(str(corrupted_audio_file))

    @patch('transcribe_memos.OpenAI')
    @patch('transcribe_memos.validate_audio_file')
    @patch('transcribe_memos.split_audio_file')
    def test_transcribe_openai_strips_whitespace(self, mock_split, mock_validate, mock_openai_class, sample_audio_file, monkeypatch, mock_config):
        """Test that transcription result is stripped of whitespace."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)
        mock_validate.return_value = (True, "")
        mock_split.return_value = [str(sample_audio_file)]

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "  Test transcription with spaces  \n"
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = transcribe_openai(str(sample_audio_file))

        assert result == "Test transcription with spaces"
        assert not result.startswith(" ")
        assert not result.endswith(" ")


@pytest.mark.unit
class TestFileSplitting:
    """Test audio file splitting."""

    @patch('subprocess.run')
    def test_split_audio_file_small_file(self, mock_run, sample_audio_file):
        """Test that small files are not split."""
        # Small file should return as-is
        result = split_audio_file(str(sample_audio_file), max_size_mb=1)

        assert len(result) == 1
        assert result[0] == str(sample_audio_file)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_split_audio_file_large_file(self, mock_mkdtemp, mock_run, large_audio_file, temp_dir):
        """Test that large files are split."""
        # Mock temp directory
        chunk_dir = temp_dir / "chunks"
        chunk_dir.mkdir()
        mock_mkdtemp.return_value = str(chunk_dir)

        # Mock ffprobe to return duration
        ffprobe_result = MagicMock()
        ffprobe_result.stdout = "120.5"  # 120.5 seconds
        ffprobe_result.returncode = 0

        # Mock ffmpeg (file splitting)
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0

        def run_side_effect(*args, **kwargs):
            if 'ffprobe' in args[0]:
                # Create dummy chunk files when ffmpeg is called
                chunk_path = args[0][-1] if len(args[0]) > 0 else None
                if chunk_path and 'chunk' in str(chunk_path):
                    Path(chunk_path).touch()
                return ffprobe_result
            else:
                return ffmpeg_result

        mock_run.side_effect = run_side_effect

        # Note: This test is simplified - a real implementation would need
        # more sophisticated mocking
        result = split_audio_file(str(large_audio_file), max_size_mb=24)

        # Verify ffprobe was called
        assert mock_run.call_count >= 1

    def test_split_audio_file_returns_list(self, sample_audio_file):
        """Test that split_audio_file always returns a list."""
        result = split_audio_file(str(sample_audio_file))
        assert isinstance(result, list)
        assert len(result) >= 1


@pytest.mark.integration
class TestTranscriptionIntegration:
    """Integration tests for transcription workflow."""

    @patch('transcribe_memos.OpenAI')
    @patch('transcribe_memos.validate_audio_file')
    @patch('transcribe_memos.split_audio_file')
    def test_full_transcription_workflow(self, mock_split, mock_validate, mock_openai_class, sample_audio_file, monkeypatch, mock_config):
        """Test complete transcription workflow."""
        # Setup all mocks
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)
        mock_validate.return_value = (True, "")
        mock_split.return_value = [str(sample_audio_file)]

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Complete test transcription"
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Execute
        result = transcribe_openai(str(sample_audio_file))

        # Verify complete workflow
        assert result == "Complete test transcription"
        mock_validate.assert_called_once_with(str(sample_audio_file))
        mock_split.assert_called_once()
        mock_client.audio.transcriptions.create.assert_called_once()
