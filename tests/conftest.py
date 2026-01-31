"""Shared pytest fixtures for voice memo transcriber tests."""

import os
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_dir(temp_dir):
    """Create a temporary config directory."""
    config_path = temp_dir / ".voice-memo-transcriber"
    config_path.mkdir(parents=True, exist_ok=True)
    return config_path


@pytest.fixture
def mock_config(temp_dir, config_dir, monkeypatch):
    """Mock the CONFIG dictionary."""
    mock_config = {
        "backend": "openai",
        "whisper_model": "small",
        "openai_api_key": "sk-test-key-12345",
        "google_doc_id": "",
        "google_doc_title": "Test Voice Memo Transcripts",
        "tab_date_format": "%B %d, %Y",
        "voice_memos_path": str(temp_dir / "voice_memos"),
        "data_dir": str(config_dir),
    }

    # Create voice memos directory
    Path(mock_config["voice_memos_path"]).mkdir(parents=True, exist_ok=True)

    return mock_config


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a sample audio file for testing."""
    audio_path = temp_dir / "test_memo.m4a"

    # Create a minimal valid M4A file (just header, not playable but valid structure)
    # This is a simplified M4A header
    m4a_header = b'\x00\x00\x00\x20ftyp' + b'M4A \x00\x00\x00\x00' + b'M4A mp42isom\x00\x00\x00\x00'
    m4a_header += b'\x00\x00\x00\x08wide'
    m4a_header += b'\x00\x00\x00\x00' * 100  # Padding to make it larger

    with open(audio_path, "wb") as f:
        f.write(m4a_header)

    return audio_path


@pytest.fixture
def large_audio_file(temp_dir):
    """Create a large audio file (>25MB) for testing file splitting."""
    audio_path = temp_dir / "large_memo.m4a"

    # Create a file larger than 25MB
    size_mb = 26
    with open(audio_path, "wb") as f:
        # Write M4A header
        m4a_header = b'\x00\x00\x00\x20ftyp' + b'M4A \x00\x00\x00\x00' + b'M4A mp42isom\x00\x00\x00\x00'
        f.write(m4a_header)
        # Fill with zeros to reach desired size
        remaining = (size_mb * 1024 * 1024) - len(m4a_header)
        f.write(b'\x00' * remaining)

    return audio_path


@pytest.fixture
def empty_audio_file(temp_dir):
    """Create an empty audio file for testing."""
    audio_path = temp_dir / "empty_memo.m4a"
    audio_path.touch()
    return audio_path


@pytest.fixture
def corrupted_audio_file(temp_dir):
    """Create a corrupted audio file for testing."""
    audio_path = temp_dir / "corrupted_memo.m4a"
    with open(audio_path, "wb") as f:
        f.write(b"This is not a valid audio file")
    return audio_path


@pytest.fixture
def processed_memos_file(config_dir):
    """Create a processed memos tracking file."""
    processed_path = config_dir / "processed.json"
    processed_data = [
        "hash1",
        "hash2",
        "hash3",
    ]
    with open(processed_path, "w") as f:
        json.dump(processed_data, f)
    return processed_path


@pytest.fixture
def docs_by_week_file(config_dir):
    """Create a docs by week mapping file."""
    docs_path = config_dir / "docs_by_week.json"
    docs_data = {
        "2025-01-27": "doc-id-1",
        "2025-02-03": "doc-id-2",
    }
    with open(docs_path, "w") as f:
        json.dump(docs_data, f)
    return docs_path


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a test transcription."
    mock_client.audio.transcriptions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_google_service():
    """Mock Google Docs service."""
    mock_service = MagicMock()

    # Mock document creation
    mock_doc = {"documentId": "test-doc-id-123"}
    mock_service.documents().create().execute.return_value = mock_doc

    # Mock document retrieval
    mock_get_doc = {
        "body": {
            "content": [
                {"endIndex": 1},
                {"endIndex": 100}
            ]
        }
    }
    mock_service.documents().get().execute.return_value = mock_get_doc

    # Mock batch update
    mock_service.documents().batchUpdate().execute.return_value = {}

    return mock_service


@pytest.fixture
def mock_credentials():
    """Mock Google credentials."""
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False
    mock_creds.refresh_token = "test-refresh-token"
    return mock_creds


@pytest.fixture
def sample_memo_datetime():
    """Sample datetime for a memo."""
    return datetime(2025, 1, 30, 14, 30, 0)


@pytest.fixture
def voice_memos_list(temp_dir):
    """Create a list of sample voice memo files."""
    memos_dir = temp_dir / "voice_memos"
    memos_dir.mkdir(parents=True, exist_ok=True)

    memos = []
    for i in range(3):
        memo_file = memos_dir / f"20250130_memo_{i}.m4a"
        with open(memo_file, "wb") as f:
            # Write minimal M4A header
            m4a_header = b'\x00\x00\x00\x20ftyp' + b'M4A \x00\x00\x00\x00' + b'M4A mp42isom\x00\x00\x00\x00'
            f.write(m4a_header + b'\x00' * 1000)
        memos.append(memo_file)

    return memos
