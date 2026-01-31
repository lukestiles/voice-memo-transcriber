# Tests

Comprehensive test suite for the Voice Memo Transcriber.

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Types

**Unit tests only:**
```bash
pytest -m unit
```

**Integration tests only:**
```bash
pytest -m integration
```

**Exclude slow tests:**
```bash
pytest -m "not slow"
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

### Run Specific Test File

```bash
pytest tests/test_file_operations.py
```

### Run Specific Test

```bash
pytest tests/test_file_operations.py::TestFileHash::test_get_file_hash
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_file_operations.py  # File handling tests
├── test_transcription.py    # Transcription tests
├── test_google_docs.py      # Google Docs integration tests
├── test_integration.py      # End-to-end tests
└── fixtures/                # Test data files
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Test individual functions in isolation
- Use mocks for external dependencies
- Fast execution
- Examples:
  - File hash generation
  - Date calculations
  - File validation

### Integration Tests (`@pytest.mark.integration`)
- Test multiple components together
- May use real file system operations
- Mock external APIs (OpenAI, Google)
- Examples:
  - Full transcription workflow
  - Document creation and append
  - Finding and processing memos

### Slow Tests (`@pytest.mark.slow`)
- Tests that take longer to run
- May involve file I/O or complex operations
- Skipped by default in CI for faster feedback

## Fixtures

Key fixtures available in `conftest.py`:

- `temp_dir` - Temporary directory for test files
- `config_dir` - Mock config directory
- `mock_config` - Mock CONFIG dictionary
- `sample_audio_file` - Sample M4A file
- `large_audio_file` - Large file for testing splitting
- `empty_audio_file` - Empty file for error testing
- `corrupted_audio_file` - Corrupted file for error testing
- `mock_openai_client` - Mocked OpenAI client
- `mock_google_service` - Mocked Google Docs service
- `voice_memos_list` - List of test memo files

## Writing New Tests

### Example Unit Test

```python
import pytest

@pytest.mark.unit
def test_my_function(mock_config, monkeypatch):
    """Test description."""
    monkeypatch.setattr("transcribe_memos.CONFIG", mock_config)

    result = my_function()

    assert result == expected_value
```

### Example Integration Test

```python
import pytest
from unittest.mock import patch

@pytest.mark.integration
@patch('transcribe_memos.OpenAI')
def test_workflow(mock_openai, temp_dir):
    """Test complete workflow."""
    # Setup mocks
    mock_openai.return_value.transcribe.return_value = "text"

    # Execute
    result = full_workflow()

    # Verify
    assert result is not None
    mock_openai.assert_called_once()
```

## Continuous Integration

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main`

Runs on multiple Python versions (3.9, 3.10, 3.11, 3.12) on macOS.

## Coverage Goals

- **Overall**: >80%
- **Unit tests**: >90%
- **Integration tests**: >70%

View current coverage:
```bash
pytest --cov=. --cov-report=term-missing
```

## Troubleshooting

### Tests fail with "ModuleNotFoundError"

Make sure you've installed test dependencies:
```bash
pip install -r requirements-dev.txt
```

### Tests fail with "ffprobe not found"

Install FFmpeg:
```bash
brew install ffmpeg
```

### Mock issues

If mocks aren't working:
1. Check that you're patching the right import path
2. Ensure patches are applied before the function is imported
3. Use `monkeypatch` fixture for safer patching

### Fixture issues

List available fixtures:
```bash
pytest --fixtures
```

## Best Practices

1. **One concept per test** - Each test should verify one thing
2. **Descriptive names** - Test names should describe what they test
3. **Arrange-Act-Assert** - Structure tests clearly
4. **Use fixtures** - Don't repeat setup code
5. **Mock external APIs** - Never call real APIs in tests
6. **Test edge cases** - Empty files, large files, errors, etc.
7. **Fast tests** - Keep tests fast for quick feedback
8. **Independent tests** - Tests shouldn't depend on each other
