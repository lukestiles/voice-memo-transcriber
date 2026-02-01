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

# Destination abstraction
from destinations import create_destination

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

    # Voice Memos location (default macOS location)
    "voice_memos_path": os.path.expanduser(
        "~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/"
    ),

    # Where to store app data (processed files list, config)
    "data_dir": os.path.expanduser("~/.voice-memo-transcriber"),

    # Destination configuration
    "destination": {
        "type": "google_docs",  # or "obsidian"

        # Google Docs settings (used when type is "google_docs")
        "google_docs": {
            "doc_id": "",  # Specific doc ID, or empty for weekly docs
            "doc_title": "Voice Memo Transcripts",
            "tab_date_format": "%B %d, %Y",
            "use_weekly_docs": True,  # Create one doc per week
        },

        # Obsidian settings (used when type is "obsidian")
        "obsidian": {
            "vault_path": "~/Documents/Obsidian/MyVault",
            "folder": "Voice Memos",
            "organize_by": "daily",  # or "weekly"
            "date_format": "%Y-%m-%d",
            "include_frontmatter": True,
            "include_tags": True,
            "include_metadata": True,
        },
    },
}


def migrate_legacy_config(config: dict) -> dict:
    """Migrate legacy flat config to nested destination structure.

    Args:
        config: Configuration dict (may be legacy or new format)

    Returns:
        Migrated config dict with destination structure
    """
    # Check if already using new format
    if "destination" in config:
        return config

    # Legacy format detected - migrate to Google Docs destination
    print("⚠️  Legacy config detected - migrating to new format...")

    migrated = config.copy()

    # Create destination config
    migrated["destination"] = {
        "type": "google_docs",
        "google_docs": {},
        "obsidian": {
            "vault_path": "~/Documents/Obsidian/MyVault",
            "folder": "Voice Memos",
            "organize_by": "daily",
            "date_format": "%Y-%m-%d",
            "include_frontmatter": True,
            "include_tags": True,
            "include_metadata": True,
        },
    }

    # Migrate Google Docs settings (only if non-empty)
    if config.get("google_doc_id"):
        migrated["destination"]["google_docs"]["doc_id"] = config["google_doc_id"]

    if config.get("google_doc_title"):
        migrated["destination"]["google_docs"]["doc_title"] = config[
            "google_doc_title"
        ]

    if config.get("tab_date_format"):
        migrated["destination"]["google_docs"]["tab_date_format"] = config[
            "tab_date_format"
        ]

    # Default to weekly docs for backward compatibility
    migrated["destination"]["google_docs"]["use_weekly_docs"] = True

    print("✓ Config migrated to Google Docs destination")

    return migrated


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
# NOTE: Google Docs integration moved to destinations/google_docs.py
# =============================================================================

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_monday_of_week(date: datetime) -> str:
    """Get the Monday of the week for a given date in YYYY-MM-DD format.

    Kept for backward compatibility with tests.
    """
    from datetime import timedelta

    weekday = date.weekday()
    days_to_monday = weekday
    monday = date - timedelta(days=days_to_monday)
    return monday.strftime("%Y-%m-%d")


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

    # Migrate legacy config if needed
    global CONFIG
    CONFIG = migrate_legacy_config(CONFIG)

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

    # Set up destination
    dest_config = CONFIG["destination"]
    dest_type = dest_config["type"]
    dest_settings = dest_config.get(dest_type, {})

    print(f"\n🔐 Initializing {dest_type} destination...")
    try:
        destination = create_destination(dest_type, dest_settings, str(data_dir))
    except ValueError as e:
        print(f"❌ Invalid destination type: {e}")
        print("   Check CONFIG['destination']['type'] in transcribe_memos.py")
        return
    except Exception as e:
        print(f"❌ Failed to create destination: {e}")
        return

    try:
        destination.initialize()
    except FileNotFoundError as e:
        print(f"❌ Missing required file: {e}")
        print("   Please follow the setup instructions in README.md")
        return
    except Exception as e:
        print(f"❌ Failed to initialize destination: {e}")
        import traceback

        traceback.print_exc()
        return

    # Process each memo
    processed = get_processed_memos()
    success_count = 0
    failed_count = 0
    failed_memos = []
    session_cache = {}  # Cache session IDs by date to avoid repeated prep

    for filepath, filename, memo_datetime in new_memos:
        timestamp_str = memo_datetime.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🎙️  Processing: {filename}")
        print(f"   Recorded: {timestamp_str}")

        transcript = None
        try:
            # Check file size - skip empty or very small files
            file_size = os.path.getsize(filepath)
            if file_size < 1000:  # Less than 1KB
                print(
                    f"   ⚠️  Skipping: File is too small ({file_size} bytes) - likely empty or corrupted"
                )
                # Mark as processed so we don't keep trying
                file_hash = get_file_hash(filepath)
                processed.add(file_hash)
                save_processed_memos(processed)
                continue

            # Prepare destination for this memo
            # Use destination-specific cache key (handles daily vs weekly organization)
            cache_key = destination.get_cache_key(memo_datetime, filepath)
            if cache_key not in session_cache:
                session_id = destination.prepare_for_memo(memo_datetime, filepath)
                session_cache[cache_key] = session_id
            else:
                session_id = session_cache[cache_key]

            # Transcribe
            print(f"   Transcribing with {CONFIG['backend']} backend...")
            transcript = transcribe(filepath)
            print(f"   ✓ Transcription complete")

            # Append to destination
            print(f"   Appending to destination...")
            destination.append_transcript(
                session_id, filename, timestamp_str, transcript, memo_datetime, filepath
            )
            print(f"   ✓ Added to destination")

            # Mark as processed ONLY if both transcription and destination append succeeded
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

    # Cleanup and summary
    destination.cleanup()

    print("\n" + "=" * 60)
    print("✨ Processing complete!")
    print(f"   Success: {success_count}/{len(new_memos)} memos")
    if failed_count > 0:
        print(f"   Failed: {failed_count}/{len(new_memos)} memos")
        print(f"   Failed memos will be retried on next run:")
        for memo in failed_memos:
            print(f"     - {memo}")
    print("=" * 60)


if __name__ == "__main__":
    main()
