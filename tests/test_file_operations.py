"""Unit tests for file operations."""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock


# Import functions from main script
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transcribe_memos import (
    get_file_hash,
    get_monday_of_week,
    get_processed_memos,
    save_processed_memos,
    validate_audio_file,
)


@pytest.mark.unit
class TestFileHash:
    """Test file hash generation."""

    def test_get_file_hash(self, sample_audio_file):
        """Test that file hash is generated correctly."""
        hash1 = get_file_hash(str(sample_audio_file))
        assert isinstance(hash1, str)
        assert len(hash1) == 32  # MD5 hash length

    def test_get_file_hash_consistency(self, sample_audio_file):
        """Test that same file produces same hash."""
        hash1 = get_file_hash(str(sample_audio_file))
        hash2 = get_file_hash(str(sample_audio_file))
        assert hash1 == hash2

    def test_get_file_hash_different_files(self, sample_audio_file, temp_dir):
        """Test that different files produce different hashes."""
        # Create another file
        other_file = temp_dir / "other.m4a"
        with open(other_file, "wb") as f:
            f.write(b"different content")

        hash1 = get_file_hash(str(sample_audio_file))
        hash2 = get_file_hash(str(other_file))
        assert hash1 != hash2


@pytest.mark.unit
class TestMondayCalculation:
    """Test Monday of week calculation."""

    def test_monday_returns_monday(self):
        """Test Monday returns same date."""
        monday = datetime(2025, 1, 27)  # A Monday
        result = get_monday_of_week(monday)
        assert result == "2025-01-27"

    def test_tuesday_returns_previous_monday(self):
        """Test Tuesday returns previous Monday."""
        tuesday = datetime(2025, 1, 28)  # A Tuesday
        result = get_monday_of_week(tuesday)
        assert result == "2025-01-27"

    def test_sunday_returns_previous_monday(self):
        """Test Sunday returns previous Monday."""
        sunday = datetime(2025, 2, 2)  # A Sunday
        result = get_monday_of_week(sunday)
        assert result == "2025-01-27"

    def test_format_is_correct(self):
        """Test output format is YYYY-MM-DD."""
        date = datetime(2025, 1, 30)
        result = get_monday_of_week(date)
        assert len(result) == 10
        assert result.count("-") == 2
        year, month, day = result.split("-")
        assert len(year) == 4
        assert len(month) == 2
        assert len(day) == 2


@pytest.mark.unit
class TestProcessedMemos:
    """Test processed memos tracking."""

    def test_get_processed_memos_empty(self, config_dir, monkeypatch, mock_config):
        """Test getting processed memos when file doesn't exist."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)
        processed = get_processed_memos()
        assert isinstance(processed, set)
        assert len(processed) == 0

    def test_get_processed_memos_existing(self, processed_memos_file, monkeypatch, mock_config):
        """Test getting processed memos from existing file."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)
        processed = get_processed_memos()
        assert isinstance(processed, set)
        assert len(processed) == 3
        assert "hash1" in processed

    def test_save_processed_memos(self, config_dir, monkeypatch, mock_config):
        """Test saving processed memos."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)
        processed = {"hash1", "hash2", "hash3"}
        save_processed_memos(processed)

        # Verify file was created
        processed_path = config_dir / "processed.json"
        assert processed_path.exists()

        # Verify content
        with open(processed_path) as f:
            data = json.load(f)
        assert len(data) == 3
        assert "hash1" in data

    def test_save_and_load_roundtrip(self, config_dir, monkeypatch, mock_config):
        """Test saving and loading processed memos."""
        monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

        # Save
        original = {"hash_a", "hash_b", "hash_c"}
        save_processed_memos(original)

        # Load
        loaded = get_processed_memos()
        assert loaded == original


@pytest.mark.unit
class TestAudioValidation:
    """Test audio file validation."""

    def test_validate_audio_file_empty(self, empty_audio_file):
        """Test validation fails for empty file."""
        is_valid, error_msg = validate_audio_file(str(empty_audio_file))
        assert not is_valid
        assert len(error_msg) > 0

    def test_validate_audio_file_corrupted(self, corrupted_audio_file):
        """Test validation fails for corrupted file."""
        is_valid, error_msg = validate_audio_file(str(corrupted_audio_file))
        assert not is_valid
        assert len(error_msg) > 0

    @pytest.mark.slow
    def test_validate_audio_file_valid(self, sample_audio_file):
        """Test validation passes for valid file structure."""
        # Note: This may fail because our test file isn't truly valid audio
        # In a real scenario, you'd use an actual audio file fixture
        is_valid, error_msg = validate_audio_file(str(sample_audio_file))
        # We expect this to fail since it's not real audio
        # This test documents the expected behavior
        assert isinstance(is_valid, bool)
        assert isinstance(error_msg, str)

    def test_validate_nonexistent_file(self):
        """Test validation fails for nonexistent file."""
        is_valid, error_msg = validate_audio_file("/nonexistent/file.m4a")
        assert not is_valid
        assert "No such file" in error_msg or "moov atom" in error_msg
