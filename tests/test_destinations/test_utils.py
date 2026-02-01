"""Tests for destination utilities."""

import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from destinations.utils import extract_audio_metadata, format_duration


def test_extract_audio_metadata_success():
    """Test successful metadata extraction."""
    mock_output = {
        "format": {
            "duration": "204.5",
            "tags": {
                "title": "Meeting Notes",
                "creation_time": "2025-01-30T09:15:32Z",
                "encoder": "iPhone Version 18.1.1"
            }
        }
    }

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_output)
        )

        metadata = extract_audio_metadata("/path/to/audio.m4a")

        assert metadata["title"] == "Meeting Notes"
        assert metadata["duration"] == 204.5
        assert metadata["creation_time"] == "2025-01-30T09:15:32Z"
        assert metadata["device"] == "iPhone Version 18.1.1"


def test_extract_audio_metadata_missing_fields():
    """Test extraction with missing metadata fields."""
    mock_output = {
        "format": {
            "tags": {}
        }
    }

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_output)
        )

        metadata = extract_audio_metadata("/path/to/audio.m4a")

        assert "title" not in metadata
        assert "duration" not in metadata
        assert "device" not in metadata


def test_extract_audio_metadata_ffprobe_error():
    """Test extraction when ffprobe returns error."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)

        metadata = extract_audio_metadata("/path/to/audio.m4a")

        assert metadata == {}


def test_extract_audio_metadata_missing_ffprobe():
    """Test extraction when ffprobe is not installed."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        metadata = extract_audio_metadata("/path/to/audio.m4a")

        assert metadata == {}


def test_extract_audio_metadata_timeout():
    """Test extraction when ffprobe times out."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 10)):
        metadata = extract_audio_metadata("/path/to/audio.m4a")

        assert metadata == {}


def test_extract_audio_metadata_invalid_json():
    """Test extraction when ffprobe returns invalid JSON."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json"
        )

        metadata = extract_audio_metadata("/path/to/audio.m4a")

        assert metadata == {}


def test_format_duration_seconds_only():
    """Test formatting duration with only seconds."""
    assert format_duration(45) == "45s"
    assert format_duration(5.7) == "5s"


def test_format_duration_minutes_and_seconds():
    """Test formatting duration with minutes and seconds."""
    assert format_duration(204) == "3m 24s"
    assert format_duration(90) == "1m 30s"
    assert format_duration(120) == "2m 0s"


def test_format_duration_hours():
    """Test formatting duration with hours."""
    assert format_duration(3665) == "1h 1m 5s"
    assert format_duration(3600) == "1h 0m 0s"
    assert format_duration(7325) == "2h 2m 5s"
