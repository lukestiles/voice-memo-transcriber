# Quick Start Guide

Get the Voice Memo Transcriber running in 10 minutes.

## Prerequisites

- Mac with macOS 10.15+
- Voice Memos app with at least one recording
- Terminal access

## 1. Install Dependencies (2 minutes)

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install FFmpeg
brew install ffmpeg
```

## 2. Download and Setup (2 minutes)

```bash
# Clone repository
cd ~/
git clone <repository-url> voice-memo-transcriber
cd voice-memo-transcriber

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Get API Keys (4 minutes)

### OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)
4. Save it - you'll need it in step 5

### Google Cloud Setup

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable "Google Docs API" in API Library
4. Create OAuth credentials:
   - Credentials → Create Credentials → OAuth client ID
   - Application type: "Desktop app"
   - Download the JSON file
5. Save credentials:
   ```bash
   mkdir -p ~/.voice-memo-transcriber
   cp ~/Downloads/client_secret_*.json ~/.voice-memo-transcriber/credentials.json
   ```

## 4. Configure (1 minute)

```bash
# Set OpenAI API key
export OPENAI_API_KEY="sk-your-actual-key-here"
```

## 5. Run! (1 minute)

```bash
cd ~/voice-memo-transcriber
source venv/bin/activate
python transcribe_memos.py
```

On first run:
1. Your browser will open for Google authorization
2. Sign in and allow access
3. Return to terminal - transcription starts automatically!

## What You'll Get

**Default behavior (Google Docs):**
- One document per week
- One tab per day
- All your voice memos transcribed automatically

**Example output:**
```
📄 2026-02-03 Voice Memo Transcripts
  ├─ 📑 February 03, 2026
  │   ├─ 📝 Morning Meeting Notes
  │   └─ 📝 Ideas for Blog
  └─ 📑 February 04, 2026
      └─ 📝 Grocery List
```

## Customization

Want different organization? Edit `transcribe_memos.py`:

### Monthly documents instead of weekly:
```python
"google_docs": {
    "doc_grouping": "monthly",  # One doc per month
    "tab_grouping": "daily",     # One tab per day
}
```

### Group by time of day:
```python
"google_docs": {
    "doc_grouping": "monthly",
    "tab_grouping": "time-of-day",  # Morning/Afternoon/Evening/Night tabs
}
```

### Use Obsidian instead:
```python
"destination": {
    "type": "obsidian",
    "obsidian": {
        "vault_path": "~/Documents/Obsidian/MyVault",
        "folder": "Voice Memos",
    },
}
```

## Next Steps

### Run Automatically Daily

```bash
# Edit plist file with your info
cp com.user.voice-memo-transcriber.plist ~/Library/LaunchAgents/
nano ~/Library/LaunchAgents/com.user.voice-memo-transcriber.plist
# Update: USERNAME, OPENAI_API_KEY

# Load it
launchctl load ~/Library/LaunchAgents/com.user.voice-memo-transcriber.plist
```

### Explore All Options

- **36 Google Docs grouping combinations**: See [docs/google-docs-grouping.md](docs/google-docs-grouping.md)
- **Complete configuration guide**: See [DESTINATIONS.md](DESTINATIONS.md)
- **Detailed setup**: See [SETUP.md](SETUP.md)
- **Rebuild the app**: See [DEVELOPER.md](DEVELOPER.md)

## Common Issues

### "Voice Memos folder not found"
- Open Voice Memos app and record at least one test memo

### "Invalid API key"
- Verify your OPENAI_API_KEY starts with `sk-`
- Get a new one at https://platform.openai.com/api-keys

### "Google credentials not found"
- Make sure you saved the credentials to: `~/.voice-memo-transcriber/credentials.json`

### "Access blocked" error
- You need to create your own Google Cloud project (step 3)
- Don't use credentials from tutorials

## Cost

OpenAI Whisper API: **$0.006 per minute** of audio

Examples:
- 10 minutes = $0.06
- 1 hour = $0.36
- 10 hours = $3.60

## Getting Help

- **Installation issues**: See [SETUP.md](SETUP.md)
- **Configuration help**: See [DESTINATIONS.md](DESTINATIONS.md)
- **Grouping examples**: See [docs/google-docs-grouping.md](docs/google-docs-grouping.md)
- **Developer guide**: See [DEVELOPER.md](DEVELOPER.md)
- **All documentation**: See [INDEX.md](INDEX.md)

## That's It!

You should now have:
- ✅ Voice memos being transcribed automatically
- ✅ Organized Google Docs (or Obsidian files)
- ✅ Only new memos transcribed (no duplicates)
- ✅ Failed transcriptions can be retried

Enjoy your automated voice memo transcription! 🎉
