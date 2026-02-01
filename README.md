# Voice Memo Transcriber

Automatically transcribe Apple Voice Memos and organize them in Google Docs or Obsidian with flexible grouping options.

## Features

- 🎙️ **Automatic transcription** - Transcribes all new voice memos using OpenAI's Whisper API or local Whisper
- 📊 **Flexible organization** - Multiple destination options with customizable grouping:
  - **Google Docs**: Weekly/monthly/quarterly/yearly documents with daily/weekly/time-of-day tabs
  - **Obsidian**: Daily/weekly markdown files with YAML frontmatter and metadata
- 🏷️ **Tag-based grouping** - Organize by hashtags in memo titles (e.g., `#project-alpha`)
- ⏱️ **Time & duration grouping** - Group by time of day or memo length
- 📝 **Smart file handling** - Automatically splits large files (>25MB), skips corrupted/empty files
- 🔄 **Resume support** - Tracks processed memos, only transcribes new ones
- 🎨 **Rich metadata** - Extracts title, duration, and device from audio files
- 🤖 **Scheduled execution** - Can run daily via launchd (macOS)
- ⚡ **Error recovery** - Failed transcriptions won't be marked as processed, allowing retries
- 🔀 **Backward compatible** - Automatically migrates from older configurations

## Requirements

- macOS (for Apple Voice Memos access)
- Python 3.8+
- FFmpeg (for audio file handling)
- OpenAI API account (for transcription)
- Google Cloud project (for Google Docs access)

## Installation

### 1. Install System Dependencies

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install FFmpeg
brew install ffmpeg
```

### 2. Clone or Download This Repository

```bash
cd ~/
git clone <repository-url> voice-memo-transcriber
cd voice-memo-transcriber
```

### 3. Set Up Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Setup

### 1. Google Cloud Setup

Create a Google Cloud project and enable the Google Docs API:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Voice Memo Transcriber")
3. Enable the Google Docs API:
   - Go to [API Library](https://console.cloud.google.com/apis/library)
   - Search for "Google Docs API"
   - Click "Enable"
4. Create OAuth credentials:
   - Go to [Credentials](https://console.cloud.google.com/apis/credentials)
   - Click "Create Credentials" → "OAuth client ID"
   - Configure OAuth consent screen if prompted:
     - Choose "External"
     - Fill in app name: "Voice Memo Transcriber"
     - Add your email as support email and developer contact
     - Click "Save and Continue" (no scopes needed)
   - Back at Create OAuth client ID:
     - Application type: "Desktop app"
     - Name: "Voice Memo Transcriber"
     - Click "Create"
   - Download the JSON file
5. Save the credentials file:
   ```bash
   cp ~/Downloads/client_secret_*.json ~/.voice-memo-transcriber/credentials.json
   ```

### 2. OpenAI API Setup

1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-`)
4. Save it for the next step

### 3. Configure the Script

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

Or update the plist file for scheduled runs (see Scheduled Execution below).

## Usage

### Manual Run

```bash
cd ~/voice-memo-transcriber
source venv/bin/activate
export OPENAI_API_KEY="sk-your-api-key-here"
python transcribe_memos.py
```

### First Run

On the first run, the script will:
1. Open your browser for Google OAuth authorization
2. Scan your Voice Memos folder
3. Create Google Docs organized by week
4. Transcribe all new memos

### Subsequent Runs

The script only transcribes **new** memos that haven't been processed yet. It tracks processed files in `~/.voice-memo-transcriber/processed.json`.

## Scheduled Execution

To run the transcriber automatically every day at 9:00 AM:

1. Update the plist file with your API key:
   ```bash
   nano com.user.voice-memo-transcriber.plist
   ```
   Find the `OPENAI_API_KEY` entry and replace with your actual key.

2. Install the launch agent:
   ```bash
   cp com.user.voice-memo-transcriber.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.user.voice-memo-transcriber.plist
   ```

3. Check logs:
   ```bash
   tail -f ~/voice-memo-transcriber/logs/stdout.log
   tail -f ~/voice-memo-transcriber/logs/stderr.log
   ```

## Configuration

Edit `transcribe_memos.py` to customize:

```python
CONFIG = {
    # Transcription backend: "local" (Whisper) or "openai" (API)
    "backend": "openai",

    # Whisper model for local transcription (if using "local" backend)
    "whisper_model": "small",

    # Voice Memos location (default is correct for most users)
    "voice_memos_path": os.path.expanduser(
        "~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/"
    ),

    # Data directory for config files
    "data_dir": os.path.expanduser("~/.voice-memo-transcriber"),

    # Destination configuration
    "destination": {
        "type": "google_docs",  # or "obsidian"

        # Google Docs options
        "google_docs": {
            "doc_grouping": "monthly",  # weekly, monthly, quarterly, yearly, tag, single
            "tab_grouping": "daily",    # daily, weekly, time-of-day, duration, tag, none
            "tab_date_format": "%B %d, %Y",
        },

        # Obsidian options
        "obsidian": {
            "vault_path": "~/Documents/Obsidian/MyVault",
            "folder": "Voice Memos",
            "organize_by": "daily",  # or "weekly"
            "include_metadata": True,
        },
    },
}
```

See [DESTINATIONS.md](DESTINATIONS.md) and [docs/google-docs-grouping.md](docs/google-docs-grouping.md) for complete configuration options.

## Destinations

### Google Docs

Organize transcripts in Google Docs with flexible grouping:

**Document Grouping Options:**
- `weekly` - One doc per week (default)
- `monthly` - One doc per month
- `quarterly` - One doc per quarter (Q1-Q4)
- `yearly` - One doc per year
- `tag` - Separate docs by hashtags in memo titles
- `single` - One doc for everything

**Tab Grouping Options:**
- `daily` - One tab per day (default)
- `weekly` - One tab per week
- `time-of-day` - Tabs for morning/afternoon/evening/night
- `duration` - Tabs for quick/standard/extended memos
- `tag` - Tabs by hashtags in memo titles
- `none` - No tabs (continuous document)

**Example:** Monthly docs with time-of-day tabs:
```python
"google_docs": {
    "doc_grouping": "monthly",
    "tab_grouping": "time-of-day",
    "tab_time_ranges": {
        "Morning": (6, 12),
        "Afternoon": (12, 18),
        "Evening": (18, 24),
        "Night": (0, 6)
    }
}
```

### Obsidian

Save transcripts as markdown files in your Obsidian vault:

- Daily or weekly file organization
- YAML frontmatter with metadata
- Audio metadata extraction (title, duration, device)
- Automatic memo counting
- Tag support for Obsidian linking

**Example:** Daily organization with metadata:
```python
"obsidian": {
    "vault_path": "~/Documents/Obsidian/MyVault",
    "folder": "Voice Memos",
    "organize_by": "daily",
    "include_metadata": True,
    "include_frontmatter": True
}
```

For complete configuration options and examples, see:
- [DESTINATIONS.md](DESTINATIONS.md) - Destination guide
- [docs/google-docs-grouping.md](docs/google-docs-grouping.md) - Google Docs grouping reference

## How It Works

### Document Organization

The transcriber uses a flexible destination system:

**Google Docs:**
- Creates documents based on your grouping strategy (weekly/monthly/quarterly/yearly/tag/single)
- Organizes tabs within documents (daily/weekly/time-of-day/duration/tag/none)
- Automatically creates and reuses documents and tabs
- Documents named based on grouping (e.g., `2026-02 Voice Memo Transcripts` for monthly)

**Obsidian:**
- Creates markdown files based on organization (daily/weekly)
- Adds YAML frontmatter with metadata
- Extracts audio metadata (title, duration, device)
- Updates memo count automatically
- Files named based on date (e.g., `2026-02-01.md` for daily)

### File Handling

1. **Empty files** (<1KB) - Skipped and marked as processed
2. **Corrupted files** - Validated with ffprobe, skipped if corrupted
3. **Large files** (>25MB) - Automatically split into chunks, transcribed separately, then combined
4. **Normal files** - Sent directly to OpenAI Whisper API

### Tracking

- Processed files are tracked by hash (path + modification time) in `~/.voice-memo-transcriber/processed.json`
- Weekly document mappings stored in `~/.voice-memo-transcriber/docs_by_week.json`
- Google OAuth token cached in `~/.voice-memo-transcriber/token.json`

## Troubleshooting

### "Access blocked: Voice Memo Transcriber has not completed the Google verification process"

You need to create your own Google Cloud project and credentials (see Setup section above). Don't use credentials from tutorials or other projects.

### "Invalid file format" or "The audio file could not be decoded"

The voice memo file may be corrupted. The script will automatically detect and skip these files.

### "Voice Memos folder not found"

Check that:
1. Voice Memos app is installed on your Mac
2. You have recorded at least one voice memo
3. The path in CONFIG matches your system

### No new memos found (but you have new recordings)

Check if the processed list needs to be reset:
```bash
cat ~/.voice-memo-transcriber/processed.json
```

To force reprocessing of all memos:
```bash
rm ~/.voice-memo-transcriber/processed.json
```

## Cost Estimation

OpenAI Whisper API pricing: **$0.006 per minute** of audio

Examples:
- 10 minutes of audio = $0.06
- 1 hour of audio = $0.36
- 10 hours of audio = $3.60

## File Structure

```
voice-memo-transcriber/
├── README.md                              # This file
├── SETUP.md                               # Detailed setup guide
├── DESTINATIONS.md                        # Destination configuration guide
├── docs/
│   └── google-docs-grouping.md           # Google Docs grouping reference
├── transcribe_memos.py                    # Main script
├── requirements.txt                       # Python dependencies
├── destinations/                          # Destination implementations
│   ├── __init__.py                       # Factory and registry
│   ├── base.py                           # Abstract base class
│   ├── google_docs.py                    # Google Docs destination
│   ├── obsidian.py                       # Obsidian destination
│   └── utils.py                          # Shared utilities
├── tests/                                 # Comprehensive test suite
│   ├── test_destinations/                # Destination tests
│   ├── test_config_migration.py          # Migration tests
│   └── test_destination_integration.py   # Integration tests
├── com.user.voice-memo-transcriber.plist  # launchd configuration
├── venv/                                  # Python virtual environment
└── logs/                                  # Log files (when run via launchd)
    ├── stdout.log
    └── stderr.log

~/.voice-memo-transcriber/
├── credentials.json                       # Google OAuth credentials
├── token.json                            # Google OAuth token (auto-generated)
├── processed.json                        # List of processed memo hashes
└── docs_by_week.json                     # Mapping of groups to Google Doc IDs
```

## Testing & Development

### Running Tests

```bash
cd ~/voice-memo-transcriber
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_destinations/ -v
pytest tests/test_config_migration.py -v
pytest tests/test_destination_integration.py -v

# Run with coverage
pytest tests/ --cov=destinations --cov=transcribe_memos --cov-report=html
```

### Creating Custom Destinations

You can create your own destination (Notion, Evernote, plain text, etc.):

1. Create a new file in `destinations/` (e.g., `notion.py`)
2. Implement the `TranscriptDestination` interface from `destinations/base.py`
3. Register it in `destinations/__init__.py`
4. Add configuration in `transcribe_memos.py`
5. Write tests in `tests/test_destinations/`

See [DESTINATIONS.md](DESTINATIONS.md#creating-custom-destinations) for a detailed developer guide.

### Project Structure

- `destinations/base.py` - Abstract base class defining the destination interface
- `destinations/google_docs.py` - Google Docs implementation with grouping strategies
- `destinations/obsidian.py` - Obsidian markdown implementation
- `destinations/utils.py` - Shared utilities (metadata extraction, formatting)
- `transcribe_memos.py` - Main script with destination factory

## Privacy & Security

- **API Keys**: Keep your OpenAI API key and Google credentials secure. Never commit them to version control.
- **Voice Memos**: Your audio files are sent to OpenAI's servers for transcription (or processed locally with Whisper).
- **Google Docs**: Transcripts are stored in your personal Google Drive.
- **Obsidian**: Transcripts are stored locally in your vault.
- **Local Storage**: Only file hashes (not content) are stored locally for tracking.

## Documentation

- **README.md** (this file) - Overview and quick start
- **SETUP.md** - Detailed step-by-step setup instructions
- **DESTINATIONS.md** - Complete destination configuration guide
- **docs/google-docs-grouping.md** - Google Docs grouping reference
- **MIGRATION_GUIDE.md** - Upgrading from older versions
- **CHANGELOG.md** - Version history and changes
- **INDEX.md** - Complete file index

## License

MIT License - feel free to modify and distribute.

## Support

For issues or questions:
- Check [DESTINATIONS.md](DESTINATIONS.md) for configuration help
- Review [SETUP.md](SETUP.md) for installation issues
- See [docs/google-docs-grouping.md](docs/google-docs-grouping.md) for grouping examples
- Open an issue on the GitHub repository
