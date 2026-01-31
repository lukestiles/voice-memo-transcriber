#!/usr/bin/env python3
"""
Voice Memos Transcriber
Automatically transcribes new Apple Voice Memos and appends them to a Google Doc.

Supports:
- Local transcription via Whisper (default, free)
- OpenAI API transcription (faster on older machines)
- Organizes transcripts by day (one tab per day)
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

# Google Docs
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# =============================================================================
# CONFIGURATION - Edit these settings
# =============================================================================

CONFIG = {
    # Transcription backend: "local" (Whisper) or "openai" (API)
    "backend": "openai",
    
    # Whisper model for local transcription: "tiny", "base", "small", "medium", "large"
    # Larger = more accurate but slower
    "whisper_model": "small",
    
    # OpenAI API key (only needed if backend is "openai")
    # Set via environment variable OPENAI_API_KEY or paste here
    "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
    
    # Google Doc ID - will be set automatically on first run or paste existing doc ID
    "google_doc_id": "",
    
    # Title for new Google Doc (if creating new)
    "google_doc_title": "Voice Memo Transcripts",
    
    # Tab naming format (Python strftime format)
    # Examples:
    #   "%B %d, %Y"  -> "January 15, 2025"
    #   "%Y-%m-%d"   -> "2025-01-15"
    #   "%m/%d/%Y"   -> "01/15/2025"
    "tab_date_format": "%B %d, %Y",
    
    # Voice Memos location (default macOS location)
    "voice_memos_path": os.path.expanduser(
        "~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/"
    ),
    
    # Where to store app data (processed files list, config)
    "data_dir": os.path.expanduser("~/.voice-memo-transcriber"),
}

# Google Docs API scope
SCOPES = ["https://www.googleapis.com/auth/documents"]

# =============================================================================
# TRANSCRIPTION BACKENDS
# =============================================================================

def transcribe_local(audio_path: str) -> str:
    """Transcribe using local Whisper model."""
    import whisper
    
    model_name = CONFIG["whisper_model"]
    print(f"  Loading Whisper model '{model_name}'...")
    model = whisper.load_model(model_name)
    
    print(f"  Transcribing...")
    result = model.transcribe(audio_path)
    return result["text"].strip()


def split_audio_file(audio_path: str, max_size_mb: int = 24) -> list[str]:
    """Split audio file into chunks smaller than max_size_mb.

    Returns list of chunk file paths.
    """
    import subprocess
    import tempfile

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

    if file_size_mb <= max_size_mb:
        # File is small enough, no splitting needed
        return [audio_path]

    print(f"  File size: {file_size_mb:.1f}MB - splitting into chunks...")

    # Get audio duration using ffprobe
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
        capture_output=True,
        text=True
    )
    duration_seconds = float(result.stdout.strip())

    # Calculate chunk duration to keep each chunk under max_size_mb
    # Estimate: size is roughly proportional to duration
    chunk_duration = int((duration_seconds * max_size_mb) / file_size_mb)

    # Create temporary directory for chunks
    temp_dir = tempfile.mkdtemp(prefix="voice-memo-chunks-")
    chunks = []

    # Split the file into chunks
    chunk_num = 0
    start_time = 0

    while start_time < duration_seconds:
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_num:03d}.m4a")

        # Use ffmpeg to extract chunk
        subprocess.run(
            ['ffmpeg', '-i', audio_path, '-ss', str(start_time),
             '-t', str(chunk_duration), '-c', 'copy', '-y', chunk_path],
            capture_output=True,
            check=True
        )

        chunks.append(chunk_path)
        start_time += chunk_duration
        chunk_num += 1

    print(f"  Created {len(chunks)} chunks")
    return chunks


def validate_audio_file(audio_path: str) -> tuple[bool, str]:
    """Validate that audio file can be decoded.

    Returns: (is_valid, error_message)
    """
    import subprocess

    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return False, result.stderr.strip()

    # Check if we got a valid duration
    try:
        duration = float(result.stdout.strip())
        if duration <= 0:
            return False, "File has zero duration"
    except ValueError:
        return False, "Could not determine file duration"

    return True, ""


def transcribe_openai(audio_path: str) -> str:
    """Transcribe using OpenAI API.

    Automatically splits files larger than 25MB into chunks.
    """
    from openai import OpenAI
    import shutil

    api_key = CONFIG["openai_api_key"]
    if not api_key:
        raise ValueError(
            "OpenAI API key not set. Set OPENAI_API_KEY environment variable "
            "or add it to CONFIG in this script."
        )

    client = OpenAI(api_key=api_key)

    # Validate audio file first
    is_valid, error_msg = validate_audio_file(audio_path)
    if not is_valid:
        raise ValueError(f"Corrupted audio file: {error_msg}")

    # Split file if needed
    chunks = split_audio_file(audio_path, max_size_mb=24)
    temp_dir = None

    try:
        if len(chunks) > 1:
            temp_dir = os.path.dirname(chunks[0])
            print(f"  Transcribing {len(chunks)} chunks...")
        else:
            print(f"  Sending to OpenAI API...")

        transcripts = []

        for i, chunk_path in enumerate(chunks):
            if len(chunks) > 1:
                print(f"    Chunk {i+1}/{len(chunks)}...")

            with open(chunk_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            transcripts.append(transcript.text.strip())

        # Combine all transcripts
        full_transcript = " ".join(transcripts)
        return full_transcript

    finally:
        # Clean up temporary chunks
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"  Cleaned up temporary chunks")


def transcribe(audio_path: str) -> str:
    """Transcribe audio file using configured backend."""
    backend = CONFIG["backend"]
    
    if backend == "local":
        return transcribe_local(audio_path)
    elif backend == "openai":
        return transcribe_openai(audio_path)
    else:
        raise ValueError(f"Unknown backend: {backend}")

# =============================================================================
# GOOGLE DOCS INTEGRATION
# =============================================================================

def get_google_credentials() -> Credentials:
    """Get or refresh Google API credentials."""
    data_dir = Path(CONFIG["data_dir"])
    token_path = data_dir / "token.json"
    creds_path = data_dir / "credentials.json"
    
    creds = None
    
    # Load existing token
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"Google credentials not found at {creds_path}\n"
                    "Please follow the setup instructions in README.md"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token for next run
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())
    
    return creds


def get_monday_of_week(date: datetime) -> str:
    """Get the Monday of the week for a given date in YYYY-MM-DD format."""
    from datetime import timedelta
    # Get the weekday (0 = Monday, 6 = Sunday)
    weekday = date.weekday()
    # Calculate days to subtract to get to Monday
    days_to_monday = weekday
    # Get the Monday date
    monday = date - timedelta(days=days_to_monday)
    return monday.strftime("%Y-%m-%d")


def get_or_create_doc(service, memo_date: datetime) -> str:
    """Get existing doc ID for the week or create a new document.

    Creates one document per week, named with the Monday date.
    """
    data_dir = Path(CONFIG["data_dir"])
    docs_map_path = data_dir / "docs_by_week.json"

    # First check if user configured a specific doc ID
    if CONFIG["google_doc_id"]:
        return CONFIG["google_doc_id"]

    # Get the Monday of this memo's week
    monday_str = get_monday_of_week(memo_date)

    # Load existing document mappings
    docs_map = {}
    if docs_map_path.exists():
        with open(docs_map_path) as f:
            docs_map = json.load(f)

    # Check if we already have a doc for this week
    if monday_str in docs_map:
        return docs_map[monday_str]

    # Create new document for this week
    doc_title = f"{monday_str} Voice Memo Transcripts"
    print(f"  Creating new Google Doc: '{doc_title}'")
    doc = service.documents().create(body={"title": doc_title}).execute()
    doc_id = doc["documentId"]

    # Save the mapping
    docs_map[monday_str] = doc_id
    with open(docs_map_path, "w") as f:
        json.dump(docs_map, f, indent=2)

    print(f"  Created doc with ID: {doc_id}")
    print(f"  URL: https://docs.google.com/document/d/{doc_id}/edit")

    return doc_id


def get_existing_tabs(service, doc_id: str) -> dict[str, str]:
    """Get a mapping of tab titles to tab IDs for the document.
    
    Returns: dict mapping tab_title -> tab_id
    """
    # Fetch document with tabs included
    doc = service.documents().get(
        documentId=doc_id,
        includeTabsContent=True
    ).execute()
    
    tabs = {}
    
    # Process all tabs in the document
    if "tabs" in doc:
        for tab in doc["tabs"]:
            tab_props = tab.get("tabProperties", {})
            tab_id = tab_props.get("tabId", "")
            tab_title = tab_props.get("title", "")
            if tab_id and tab_title:
                tabs[tab_title] = tab_id
    
    return tabs


def get_or_create_tab_for_date(service, doc_id: str, date: datetime) -> str:
    """Get existing tab for the date, or create a new one.
    
    Returns: tab_id for the date's tab
    """
    tab_title = date.strftime(CONFIG["tab_date_format"])
    
    # Check if tab already exists
    existing_tabs = get_existing_tabs(service, doc_id)
    
    if tab_title in existing_tabs:
        print(f"  Using existing tab: '{tab_title}'")
        return existing_tabs[tab_title]
    
    # Create new tab
    print(f"  Creating new tab: '{tab_title}'")
    
    requests = [
        {
            "createTab": {
                "tabProperties": {
                    "title": tab_title
                }
            }
        }
    ]
    
    response = service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()
    
    # Extract the new tab ID from the response
    new_tab_id = response["replies"][0]["createTab"]["tabProperties"]["tabId"]
    
    # Add a header to the new tab
    header_text = f"📅 {tab_title}\n\nVoice Memo Transcripts\n\n"
    
    service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {
                            "index": 1,
                            "tabId": new_tab_id
                        },
                        "text": header_text
                    }
                }
            ]
        }
    ).execute()
    
    return new_tab_id


def get_tab_end_index(service, doc_id: str, tab_id: str) -> int:
    """Get the end index of content in a specific tab."""
    doc = service.documents().get(
        documentId=doc_id,
        includeTabsContent=True
    ).execute()
    
    # Find the tab and get its content end index
    if "tabs" in doc:
        for tab in doc["tabs"]:
            if tab.get("tabProperties", {}).get("tabId") == tab_id:
                doc_tab = tab.get("documentTab", {})
                body = doc_tab.get("body", {})
                content = body.get("content", [])
                if content:
                    return content[-1].get("endIndex", 1) - 1
    
    return 1  # Default to beginning if not found


def append_to_tab(service, doc_id: str, tab_id: str, memo_name: str, timestamp: str, transcript: str):
    """Append a transcription to a specific tab in the Google Doc."""
    # Format the content to append
    content = f"\n{'─'*50}\n"
    content += f"📝 {memo_name}\n"
    content += f"🕐 {timestamp}\n"
    content += f"{'─'*50}\n\n"
    content += transcript
    content += "\n\n"
    
    # Get current tab content length
    end_index = get_tab_end_index(service, doc_id, tab_id)
    
    # Insert at end of tab
    requests = [
        {
            "insertText": {
                "location": {
                    "index": end_index,
                    "tabId": tab_id
                },
                "text": content
            }
        }
    ]
    
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()


# Legacy function for backwards compatibility
def append_to_doc(service, doc_id: str, memo_name: str, timestamp: str, transcript: str):
    """Append a transcription to the main tab of the Google Doc (legacy)."""
    # Format the content to append
    content = f"\n\n{'='*60}\n"
    content += f"📝 {memo_name}\n"
    content += f"🕐 {timestamp}\n"
    content += f"{'='*60}\n\n"
    content += transcript
    content += "\n"
    
    # Get current document length
    doc = service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1
    
    # Insert at end
    requests = [
        {
            "insertText": {
                "location": {"index": end_index},
                "text": content
            }
        }
    ]
    
    service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

# =============================================================================
# MEMO TRACKING
# =============================================================================

def get_processed_memos() -> set:
    """Get set of already-processed memo file hashes."""
    data_dir = Path(CONFIG["data_dir"])
    processed_path = data_dir / "processed.json"
    
    if processed_path.exists():
        with open(processed_path) as f:
            return set(json.load(f))
    return set()


def save_processed_memos(processed: set):
    """Save the set of processed memo hashes."""
    data_dir = Path(CONFIG["data_dir"])
    processed_path = data_dir / "processed.json"
    
    with open(processed_path, "w") as f:
        json.dump(list(processed), f)


def get_file_hash(filepath: str) -> str:
    """Get a hash of file path + modification time for tracking."""
    stat = os.stat(filepath)
    content = f"{filepath}:{stat.st_mtime}"
    return hashlib.md5(content.encode()).hexdigest()

# =============================================================================
# MAIN
# =============================================================================

def find_new_memos() -> list[tuple[str, str, datetime]]:
    """Find voice memos that haven't been processed yet.
    
    Returns list of (filepath, filename, datetime) tuples.
    """
    memos_path = Path(CONFIG["voice_memos_path"])
    
    if not memos_path.exists():
        print(f"Voice Memos folder not found: {memos_path}")
        print("Make sure you have Voice Memos installed and have recorded at least one memo.")
        return []
    
    processed = get_processed_memos()
    new_memos = []
    
    # Find all audio files
    for audio_file in memos_path.glob("**/*.m4a"):
        file_hash = get_file_hash(str(audio_file))
        
        if file_hash not in processed:
            # Get modification time as datetime
            mtime = datetime.fromtimestamp(audio_file.stat().st_mtime)
            new_memos.append((str(audio_file), audio_file.stem, mtime))
    
    # Sort by timestamp
    new_memos.sort(key=lambda x: x[2])
    return new_memos


def main():
    """Main entry point."""
    print("=" * 60)
    print("Voice Memo Transcriber")
    print("=" * 60)
    
    # Ensure data directory exists
    data_dir = Path(CONFIG["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Find new memos
    print("\n📂 Scanning for new voice memos...")
    new_memos = find_new_memos()
    
    if not new_memos:
        print("No new memos to transcribe.")
        return
    
    print(f"Found {len(new_memos)} new memo(s)")

    # Set up Google Docs
    print("\n🔐 Connecting to Google Docs...")
    creds = get_google_credentials()
    service = build("docs", "v1", credentials=creds)

    # Process each memo
    processed = get_processed_memos()
    success_count = 0
    failed_count = 0
    failed_memos = []
    doc_cache = {}  # Cache doc IDs by week to avoid repeated lookups

    for filepath, filename, memo_datetime in new_memos:
        timestamp_str = memo_datetime.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🎙️  Processing: {filename}")
        print(f"   Recorded: {timestamp_str}")

        transcript = None
        try:
            # Check file size - skip empty or very small files
            file_size = os.path.getsize(filepath)
            if file_size < 1000:  # Less than 1KB
                print(f"   ⚠️  Skipping: File is too small ({file_size} bytes) - likely empty or corrupted")
                # Mark as processed so we don't keep trying
                file_hash = get_file_hash(filepath)
                processed.add(file_hash)
                save_processed_memos(processed)
                continue

            # Get or create document for this memo's week
            monday_str = get_monday_of_week(memo_datetime)
            if monday_str not in doc_cache:
                doc_id = get_or_create_doc(service, memo_datetime)
                doc_cache[monday_str] = doc_id
                print(f"  Using doc: https://docs.google.com/document/d/{doc_id}/edit")
            else:
                doc_id = doc_cache[monday_str]

            # Transcribe
            print(f"   Transcribing with {CONFIG['backend']} backend...")
            transcript = transcribe(filepath)
            print(f"   ✓ Transcription complete")

            # Append to document
            print(f"   Appending to document...")
            append_to_doc(service, doc_id, filename, timestamp_str, transcript)
            print(f"   ✓ Added to document")

            # Mark as processed ONLY if both transcription and document append succeeded
            file_hash = get_file_hash(filepath)
            processed.add(file_hash)
            save_processed_memos(processed)

            print(f"   ✅ Done!")
            success_count += 1

        except ValueError as e:
            # Corrupted file - skip and mark as processed
            error_msg = str(e)
            if "Corrupted audio file" in error_msg:
                print(f"   ⚠️  Skipping: {error_msg}")
                print(f"   Marking as processed to avoid retrying corrupted file")
                file_hash = get_file_hash(filepath)
                processed.add(file_hash)
                save_processed_memos(processed)
                failed_count += 1
                failed_memos.append(f"{filename} (corrupted)")
            else:
                # Other ValueError - don't mark as processed
                failed_count += 1
                failed_memos.append(filename)
                print(f"   ❌ Error: {e}")
                print(f"   ⚠️  Memo NOT marked as processed - will retry on next run")
                import traceback
                traceback.print_exc()
            continue

        except Exception as e:
            failed_count += 1
            failed_memos.append(filename)
            print(f"   ❌ Error: {e}")
            print(f"   ⚠️  Memo NOT marked as processed - will retry on next run")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "=" * 60)
    print("✨ Processing complete!")
    print(f"   Success: {success_count}/{len(new_memos)} memos")
    if failed_count > 0:
        print(f"   Failed: {failed_count}/{len(new_memos)} memos")
        print(f"   Failed memos will be retried on next run:")
        for memo in failed_memos:
            print(f"     - {memo}")

    if doc_cache:
        print(f"\n📄 Documents created/updated ({len(doc_cache)} total):")
        for monday_str in sorted(doc_cache.keys()):
            doc_id = doc_cache[monday_str]
            print(f"   Week of {monday_str}:")
            print(f"     https://docs.google.com/document/d/{doc_id}/edit")
    print("=" * 60)


if __name__ == "__main__":
    main()
