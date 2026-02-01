# Developer Guide

This guide explains how to rebuild, extend, and contribute to the Voice Memo Transcriber.

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Creating Custom Destinations](#creating-custom-destinations)
- [Testing](#testing)
- [Code Style](#code-style)
- [Contributing](#contributing)

## Getting Started

### Prerequisites

- macOS 10.15+
- Python 3.8+
- Git
- FFmpeg
- Basic Python knowledge

### Clone and Setup

```bash
# Clone repository
git clone <repository-url> voice-memo-transcriber
cd voice-memo-transcriber

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov pylint mypy black

# Run tests to verify setup
pytest tests/ -v
```

## Architecture

### Destination Abstraction Layer

The transcriber uses a destination abstraction pattern that separates transcription from storage:

```
┌─────────────────────┐
│  transcribe_memos.py│  Main script
│  - File discovery   │
│  - Transcription    │
└──────────┬──────────┘
           │
           │ create_destination(config)
           ▼
┌─────────────────────────────┐
│ destinations/__init__.py    │  Factory & Registry
│ - Factory pattern          │
│ - Destination registration │
└──────────┬──────────────────┘
           │
           │ Returns TranscriptDestination
           ▼
┌─────────────────────────────┐
│ destinations/base.py        │  Abstract Base Class
│ - Interface definition     │
│ - 5 required methods       │
└──────────┬──────────────────┘
           │
           │ Implemented by...
           ▼
┌──────────────────────────────┬──────────────────────────┐
│ destinations/google_docs.py  │ destinations/obsidian.py │
│ - Document grouping         │ - Markdown files         │
│ - Tab grouping              │ - YAML frontmatter       │
│ - 12 strategy classes       │ - Metadata extraction    │
└─────────────────────────────┴──────────────────────────┘
```

### Key Design Patterns

1. **Factory Pattern**: `create_destination()` creates destinations by type
2. **Strategy Pattern**: Google Docs uses strategies for flexible grouping
3. **Abstract Base Class**: `TranscriptDestination` defines the interface
4. **Registry Pattern**: Destinations auto-register on import

## Project Structure

```
voice-memo-transcriber/
├── destinations/                 # Destination implementations
│   ├── __init__.py              # Factory and registry (71 lines)
│   ├── base.py                  # Abstract base class (112 lines)
│   ├── google_docs.py           # Google Docs impl (560 lines)
│   ├── obsidian.py              # Obsidian impl (309 lines)
│   └── utils.py                 # Shared utilities (98 lines)
│
├── tests/                        # Test suite (72 tests, 68% coverage)
│   ├── test_destinations/       # Destination tests
│   │   ├── test_base.py        # Base class tests (5 tests)
│   │   ├── test_google_docs.py # Google Docs tests (15 tests)
│   │   ├── test_obsidian.py    # Obsidian tests (18 tests)
│   │   └── test_utils.py       # Utilities tests (9 tests)
│   ├── test_config_migration.py # Migration tests (4 tests)
│   ├── test_destination_integration.py  # Integration (6 tests)
│   ├── test_file_operations.py  # File ops tests (15 tests)
│   └── conftest.py              # Shared fixtures
│
├── docs/                         # Documentation
│   └── google-docs-grouping.md  # Grouping reference
│
├── transcribe_memos.py          # Main script (532 lines)
├── requirements.txt             # Python dependencies
├── README.md                    # User guide
├── SETUP.md                     # Installation guide
├── DESTINATIONS.md              # Destination guide
├── DEVELOPER.md                 # This file
├── MIGRATION_GUIDE.md           # Upgrade guide
├── CHANGELOG.md                 # Version history
└── INDEX.md                     # Complete file index
```

## Development Setup

### Environment Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install development tools
pip install pytest pytest-cov pytest-mock
pip install pylint mypy black isort

# Setup pre-commit (optional)
pip install pre-commit
pre-commit install
```

### Configuration for Development

Create a test configuration in `transcribe_memos.py`:

```python
# Development config - uses smaller Whisper model
DEV_CONFIG = {
    "backend": "local",  # Don't use API credits during development
    "whisper_model": "tiny",  # Faster for testing
    "voice_memos_path": "/tmp/test_memos",  # Test directory
    "data_dir": "/tmp/.voice-memo-transcriber-dev",
    "destination": {
        "type": "obsidian",  # Easier to verify during development
        "obsidian": {
            "vault_path": "/tmp/test_vault",
            "folder": "Test Memos",
            "organize_by": "daily",
        },
    },
}
```

### Running the App Locally

```bash
# Set up test environment
mkdir -p /tmp/test_memos /tmp/test_vault/.obsidian

# Copy a test audio file
cp ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings/*.m4a /tmp/test_memos/

# Run with development config
python3 transcribe_memos.py
```

## Creating Custom Destinations

### Step 1: Implement the Interface

Create `destinations/my_destination.py`:

```python
from datetime import datetime
from typing import Any, Dict
from .base import TranscriptDestination


class MyDestination(TranscriptDestination):
    """My custom destination implementation."""

    def validate_config(self) -> None:
        """Validate required configuration."""
        required = ["my_setting"]
        for key in required:
            if key not in self.config:
                raise ValueError(f"Missing required config: {key}")

    def initialize(self) -> None:
        """Initialize connections, authenticate, etc."""
        # Setup API clients, verify access, etc.
        self.api_client = SomeAPI(self.config["api_key"])
        print("Connected to My Destination")

    def prepare_for_memo(self, memo_datetime: datetime, filepath: str = None) -> str:
        """Get or create destination for this memo.

        Returns:
            session_id - Unique identifier for this session
                        (e.g., page_id, file_path, doc_id)
        """
        # Determine where this memo should go
        # Create destination if needed
        page_id = self._get_or_create_page(memo_datetime)
        return page_id

    def append_transcript(
        self,
        session_id: str,
        memo_name: str,
        timestamp: str,
        transcript: str,
        memo_datetime: datetime,
        filepath: str,
    ) -> None:
        """Append transcript to the destination."""
        # Use session_id to append content
        self.api_client.append_to_page(
            page_id=session_id,
            content=f"## {memo_name}\n\n{timestamp}\n\n{transcript}"
        )

    def cleanup(self) -> None:
        """Clean up resources and print summary."""
        print(f"✓ Transcripts saved to My Destination")
        if hasattr(self, 'api_client'):
            self.api_client.close()

    def get_cache_key(self, memo_datetime: datetime, filepath: str = None) -> str:
        """Get cache key for session reuse.

        Override this if your destination groups memos differently.
        For example, if you group by week, return the week identifier.
        """
        # Default: one session per day
        return memo_datetime.strftime("%Y-%m-%d")

    # Helper methods (private)
    def _get_or_create_page(self, date: datetime) -> str:
        """Get existing page or create new one."""
        # Your implementation
        return "page-id-123"
```

### Step 2: Register the Destination

Add to `destinations/__init__.py`:

```python
from .my_destination import MyDestination

# Register the destination
register_destination("my_destination", MyDestination)
```

### Step 3: Add Configuration

Update `transcribe_memos.py`:

```python
CONFIG = {
    # ... other settings ...

    "destination": {
        "type": "my_destination",  # Use your new destination

        "my_destination": {
            "api_key": "your-api-key",
            "my_setting": "value",
        },
    },
}
```

### Step 4: Write Tests

Create `tests/test_destinations/test_my_destination.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from destinations.my_destination import MyDestination


@pytest.fixture
def my_config():
    """Configuration for MyDestination."""
    return {
        "api_key": "test-key",
        "my_setting": "test-value",
    }


@pytest.fixture
def my_dest(my_config, config_dir):
    """Create a MyDestination instance."""
    return MyDestination(my_config, str(config_dir))


@pytest.mark.unit
class TestMyDestination:
    """Test MyDestination implementation."""

    def test_validate_config_success(self, my_dest):
        """Test validation with correct config."""
        my_dest.validate_config()  # Should not raise

    def test_validate_config_missing_key(self, config_dir):
        """Test validation fails with missing config."""
        config = {"api_key": "test"}  # Missing my_setting
        dest = MyDestination(config, str(config_dir))

        with pytest.raises(ValueError, match="Missing required config"):
            dest.validate_config()

    @patch('destinations.my_destination.SomeAPI')
    def test_initialize(self, mock_api, my_dest):
        """Test initialization."""
        my_dest.initialize()

        mock_api.assert_called_once_with("test-key")
        assert my_dest.api_client is not None

    def test_prepare_for_memo(self, my_dest):
        """Test preparing for a memo."""
        # Mock the API
        my_dest.api_client = MagicMock()
        my_dest.api_client.get_or_create_page.return_value = "page-123"

        memo_date = datetime(2026, 2, 1)
        session_id = my_dest.prepare_for_memo(memo_date)

        assert session_id == "page-123"

    def test_append_transcript(self, my_dest):
        """Test appending a transcript."""
        my_dest.api_client = MagicMock()

        my_dest.append_transcript(
            session_id="page-123",
            memo_name="Test Memo",
            timestamp="2026-02-01 10:00:00",
            transcript="This is a test.",
            memo_datetime=datetime(2026, 2, 1),
            filepath="/path/to/memo.m4a"
        )

        my_dest.api_client.append_to_page.assert_called_once()
        call_args = my_dest.api_client.append_to_page.call_args
        assert call_args[1]['page_id'] == "page-123"
        assert "Test Memo" in call_args[1]['content']

    def test_cleanup(self, my_dest, capsys):
        """Test cleanup."""
        my_dest.api_client = MagicMock()
        my_dest.cleanup()

        captured = capsys.readouterr()
        assert "My Destination" in captured.out
        my_dest.api_client.close.assert_called_once()
```

Run tests:

```bash
pytest tests/test_destinations/test_my_destination.py -v
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_destinations/test_google_docs.py -v

# Run specific test
pytest tests/test_destinations/test_google_docs.py::TestDocumentCreation::test_get_or_create_doc_new -v

# Run with coverage
pytest tests/ --cov=destinations --cov=transcribe_memos --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Structure

```python
# tests/test_destinations/test_example.py

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from destinations.example import ExampleDestination


@pytest.fixture
def example_config():
    """Test configuration."""
    return {"setting": "value"}


@pytest.fixture
def example_dest(example_config, config_dir):
    """Create destination instance."""
    return ExampleDestination(example_config, str(config_dir))


@pytest.mark.unit
class TestExampleValidation:
    """Test configuration validation."""

    def test_valid_config(self, example_dest):
        """Test with valid configuration."""
        example_dest.validate_config()

    def test_invalid_config(self):
        """Test with invalid configuration."""
        dest = ExampleDestination({}, "/tmp")
        with pytest.raises(ValueError):
            dest.validate_config()


@pytest.mark.unit
class TestExampleOperations:
    """Test destination operations."""

    def test_prepare_for_memo(self, example_dest):
        """Test preparing for a memo."""
        session_id = example_dest.prepare_for_memo(datetime.now())
        assert session_id is not None
```

### Writing Good Tests

1. **Use fixtures** for common setup
2. **Mock external services** (API calls, file I/O)
3. **Test error cases** not just happy path
4. **Use descriptive names** that explain what's being tested
5. **Keep tests independent** - no shared state
6. **Use markers** (`@pytest.mark.unit`, `@pytest.mark.integration`)

## Code Style

### Python Style

We follow PEP 8 with some modifications:

```python
# Line length: 100 characters (not 80)
# Use double quotes for strings
# Use f-strings for formatting

# Good
def format_duration(seconds: int) -> str:
    """Format duration in human-readable format."""
    minutes = seconds // 60
    return f"{minutes}m {seconds % 60}s"

# Bad
def format_duration(seconds):
    minutes = seconds // 60
    return str(minutes) + 'm ' + str(seconds % 60) + 's'
```

### Type Hints

Use type hints for function signatures:

```python
from typing import Dict, List, Optional
from datetime import datetime

def process_memos(
    memos: List[str],
    config: Dict[str, Any],
    start_date: Optional[datetime] = None
) -> int:
    """Process memos and return count."""
    return len(memos)
```

### Docstrings

Use Google-style docstrings:

```python
def extract_audio_metadata(filepath: str) -> Dict[str, Any]:
    """Extract metadata from audio file using ffprobe.

    Args:
        filepath: Path to the audio file

    Returns:
        Dictionary with keys: title, duration, device

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If ffprobe fails
    """
    pass
```

### Code Formatting

```bash
# Format with black
black destinations/ transcribe_memos.py

# Sort imports
isort destinations/ transcribe_memos.py

# Check with pylint
pylint destinations/ transcribe_memos.py

# Type check with mypy
mypy destinations/ transcribe_memos.py
```

## Contributing

### Workflow

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/my-feature`
3. **Make changes** and add tests
4. **Run tests**: `pytest tests/ -v`
5. **Format code**: `black . && isort .`
6. **Commit**: `git commit -m "Add my feature"`
7. **Push**: `git push origin feature/my-feature`
8. **Create pull request**

### Commit Messages

Follow conventional commits:

```bash
# Good
git commit -m "feat: add Notion destination support"
git commit -m "fix: handle missing audio metadata gracefully"
git commit -m "docs: update Google Docs grouping examples"
git commit -m "test: add integration tests for Obsidian"

# Types: feat, fix, docs, test, refactor, chore
```

### Pull Request Checklist

- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Code formatted with black
- [ ] Type hints added
- [ ] Docstrings added/updated
- [ ] CHANGELOG.md updated
- [ ] No breaking changes (or documented if unavoidable)

## Building & Releasing

### Version Numbering

We use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Process

1. Update version in `transcribe_memos.py`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Create git tag: `git tag v2.1.0`
5. Push tag: `git push origin v2.1.0`
6. Create GitHub release

## Troubleshooting

### Tests Failing

```bash
# Clear cache
rm -rf .pytest_cache __pycache__ **/__pycache__

# Reinstall dependencies
pip install -r requirements.txt

# Run with verbose output
pytest tests/ -vv
```

### Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Verify Python path
python3 -c "import sys; print(sys.path)"

# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Mock Issues

```python
# When mocking, patch at the import location
# Not where the function is defined

# Good
@patch('destinations.google_docs.build')  # Where it's imported
def test_something(self, mock_build):
    pass

# Bad
@patch('googleapiclient.discovery.build')  # Where it's defined
def test_something(self, mock_build):
    pass
```

## Resources

- **Python Docs**: https://docs.python.org/3/
- **Pytest Docs**: https://docs.pytest.org/
- **Google Docs API**: https://developers.google.com/docs/api
- **OpenAI API**: https://platform.openai.com/docs
- **FFmpeg**: https://ffmpeg.org/documentation.html

## Getting Help

- Review existing documentation in the repo
- Check GitHub issues for similar problems
- Create a new issue with:
  - Clear description of the problem
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (Python version, OS, etc.)

## License

MIT License - See LICENSE file for details
