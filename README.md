# Voice Memo Transcriber

Automatically transcribe Apple Voice Memos and organize them in Google Docs, with one document per week.

## Features

- 🎙️ **Automatic transcription** - Transcribes all new voice memos using OpenAI's Whisper API
- 📅 **Weekly organization** - Creates one Google Doc per week (named `YYYY-MM-DD Voice Memo Transcripts`)
- 📝 **Smart file handling** - Automatically splits large files (>25MB), skips corrupted/empty files
- 🔄 **Resume support** - Tracks processed memos, only transcribes new ones
- 🤖 **Scheduled execution** - Can run daily via launchd (macOS)
- ⚡ **Error recovery** - Failed transcriptions won't be marked as processed, allowing retries

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
}
```

## How It Works

### Document Organization

- One Google Doc is created per week
- Documents are named: `YYYY-MM-DD Voice Memo Transcripts` (where the date is the Monday of that week)
- All memos recorded during a week are added to that week's document

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
├── transcribe_memos.py                    # Main script
├── requirements.txt                       # Python dependencies
├── com.user.voice-memo-transcriber.plist  # launchd configuration
├── venv/                                  # Python virtual environment
└── logs/                                  # Log files (when run via launchd)
    ├── stdout.log
    └── stderr.log

~/.voice-memo-transcriber/
├── credentials.json                       # Google OAuth credentials
├── token.json                            # Google OAuth token (auto-generated)
├── processed.json                        # List of processed memo hashes
└── docs_by_week.json                     # Mapping of weeks to Google Doc IDs
```

## Privacy & Security

- **API Keys**: Keep your OpenAI API key and Google credentials secure. Never commit them to version control.
- **Voice Memos**: Your audio files are sent to OpenAI's servers for transcription.
- **Google Docs**: Transcripts are stored in your personal Google Drive.
- **Local Storage**: Only file hashes (not content) are stored locally for tracking.

## License

MIT License - feel free to modify and distribute.

## Support

For issues or questions, please open an issue on the GitHub repository.
