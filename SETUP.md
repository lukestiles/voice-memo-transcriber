# Setup Guide

This guide walks you through setting up the Voice Memo Transcriber step by step.

## Prerequisites

Before starting, make sure you have:
- A Mac with macOS 10.15 or later
- Apple Voice Memos app installed and at least one recording
- An OpenAI account with API access
- A Google account

## Step 1: Install System Dependencies

### Install Homebrew (if not already installed)

Open Terminal and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Install FFmpeg

```bash
brew install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

## Step 2: Download and Install the Script

```bash
cd ~/
git clone <repository-url> voice-memo-transcriber
cd voice-memo-transcriber
```

## Step 3: Set Up Python Environment

### Create virtual environment

```bash
python3 -m venv venv
```

### Activate virtual environment

```bash
source venv/bin/activate
```

You should see `(venv)` at the beginning of your terminal prompt.

### Install Python dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Google Docs API libraries
- OpenAI Python client
- Audio processing libraries

## Step 4: Get OpenAI API Key

1. Go to https://platform.openai.com/signup (create account if needed)
2. Navigate to https://platform.openai.com/api-keys
3. Click "Create new secret key"
4. Name it "Voice Memo Transcriber"
5. **IMPORTANT**: Copy the key immediately (it starts with `sk-`)
6. Save it somewhere secure - you'll need it in Step 6

**Cost**: OpenAI charges $0.006 per minute of audio transcribed.

## Step 5: Set Up Google Cloud Project

### Create Project

1. Go to https://console.cloud.google.com/
2. Click "Select a project" dropdown at the top
3. Click "New Project"
4. Name: "Voice Memo Transcriber"
5. Click "Create"
6. Wait for project creation, then select it

### Enable Google Docs API

1. Go to https://console.cloud.google.com/apis/library
2. Search for "Google Docs API"
3. Click on "Google Docs API"
4. Click "Enable"
5. Wait for it to enable

### Configure OAuth Consent Screen

1. Go to https://console.cloud.google.com/apis/credentials/consent
2. Select "External" user type
3. Click "Create"
4. Fill in required fields:
   - App name: `Voice Memo Transcriber`
   - User support email: (your email)
   - Developer contact: (your email)
5. Click "Save and Continue"
6. On Scopes page, click "Save and Continue" (no scopes needed)
7. On Test users page, click "Save and Continue"
8. Review and click "Back to Dashboard"

### Create OAuth Credentials

1. Go to https://console.cloud.google.com/apis/credentials
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: Select "Desktop app"
4. Name: `Voice Memo Transcriber`
5. Click "Create"
6. A popup shows your credentials - click "OK"
7. Click the download icon (⬇️) next to your newly created OAuth 2.0 Client ID
8. Save the JSON file

### Install Credentials

```bash
# Create config directory
mkdir -p ~/.voice-memo-transcriber

# Copy the downloaded credentials
cp ~/Downloads/client_secret_*.json ~/.voice-memo-transcriber/credentials.json
```

Verify:
```bash
ls -la ~/.voice-memo-transcriber/credentials.json
```

## Step 6: Configure Environment

### Option A: For Manual Runs

Add to your `~/.zshrc` or `~/.bash_profile`:

```bash
export OPENAI_API_KEY="sk-your-actual-api-key-here"
```

Then reload:
```bash
source ~/.zshrc  # or source ~/.bash_profile
```

### Option B: For Scheduled Runs (launchd)

Copy the template and edit it:

```bash
cp com.user.voice-memo-transcriber.plist.template com.user.voice-memo-transcriber.plist
nano com.user.voice-memo-transcriber.plist
```

Update these fields:
1. Replace `YOUR_USERNAME` with your actual username (run `whoami` to find it)
2. Replace `YOUR_OPENAI_API_KEY_HERE` with your actual OpenAI API key

Save and exit (Ctrl+X, then Y, then Enter).

## Step 7: First Run and Authorization

### Run the script

```bash
cd ~/voice-memo-transcriber
source venv/bin/activate
export OPENAI_API_KEY="sk-your-actual-api-key-here"
python transcribe_memos.py
```

### Authorize Google Access

1. The script will print a URL starting with `https://accounts.google.com/o/oauth2/auth...`
2. Copy and paste it into your browser
3. Sign in with your Google account
4. You'll see a warning "Google hasn't verified this app" - this is normal
5. Click "Advanced" → "Go to Voice Memo Transcriber (unsafe)"
6. Click "Continue"
7. The browser will show "The authentication flow has completed"
8. Return to Terminal - the script will continue automatically

### Watch the Progress

You'll see output like:
```
============================================================
Voice Memo Transcriber
============================================================

📂 Scanning for new voice memos...
Found 73 new memo(s)

🔐 Connecting to Google Docs...
  Creating new Google Doc: '2025-01-27 Voice Memo Transcripts'
  ...

🎙️  Processing: 20250120 091917-07B7EB25
   Recorded: 2025-01-20 09:19:17
   Transcribing with openai backend...
  Sending to OpenAI API...
   ✓ Transcription complete
   Appending to document...
   ✓ Added to document
   ✅ Done!
```

## Step 8: Verify Results

1. Check the summary at the end for any errors
2. Open the Google Docs links shown
3. Verify transcriptions are accurate

## Step 9 (Optional): Set Up Automatic Daily Runs

### Install the launch agent

```bash
cp com.user.voice-memo-transcriber.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.voice-memo-transcriber.plist
```

### Verify it's loaded

```bash
launchctl list | grep voice-memo
```

You should see: `com.user.voice-memo-transcriber`

### Test it

```bash
launchctl start com.user.voice-memo-transcriber
```

Check logs:
```bash
tail -f ~/voice-memo-transcriber/logs/stdout.log
```

### Uninstall (if needed)

```bash
launchctl unload ~/Library/LaunchAgents/com.user.voice-memo-transcriber.plist
rm ~/Library/LaunchAgents/com.user.voice-memo-transcriber.plist
```

## Troubleshooting

### "command not found: python3"

Install Python:
```bash
brew install python@3
```

### "ModuleNotFoundError"

Make sure virtual environment is activated:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Voice Memos folder not found"

1. Open Voice Memos app
2. Record a test memo
3. Check path exists:
   ```bash
   ls -la ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings/
   ```

### "Invalid API key"

1. Verify your key starts with `sk-`
2. Create a new key at https://platform.openai.com/api-keys
3. Update your environment variable or plist file

### "Access blocked: Voice Memo Transcriber has not completed the Google verification process"

You're using someone else's Google credentials. Follow Step 5 to create your own.

## Next Steps

- Run manually whenever you have new voice memos
- Or let it run automatically daily at 9 AM
- Check `~/voice-memo-transcriber/logs/` for any issues

## Getting Help

If you encounter issues not covered here, check:
1. The main README.md
2. Error messages in `logs/stderr.log`
3. OpenAI API status: https://status.openai.com/
4. Google Cloud Console for API quota/errors
