"""Shared utilities for destinations."""

import json
import subprocess
from typing import Dict, Any


def extract_audio_metadata(filepath: str) -> Dict[str, Any]:
    """Extract metadata from audio file using ffprobe.

    Args:
        filepath: Path to the audio file

    Returns:
        Dictionary with metadata fields:
        - title: Custom title from Voice Memos app
        - duration: Duration in seconds
        - creation_time: When the file was created
        - device: Device information from encoder field
        Returns empty dict if extraction fails.
    """
    try:
        # Run ffprobe to get metadata as JSON
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                filepath
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return {}

        data = json.loads(result.stdout)
        metadata = {}

        # Extract format tags
        format_tags = data.get("format", {}).get("tags", {})

        # Get title (may be in different fields)
        if "title" in format_tags:
            metadata["title"] = format_tags["title"]
        elif "TIT2" in format_tags:
            metadata["title"] = format_tags["TIT2"]

        # Get duration
        if "duration" in data.get("format", {}):
            try:
                metadata["duration"] = float(data["format"]["duration"])
            except (ValueError, TypeError):
                pass

        # Get creation time
        if "creation_time" in format_tags:
            metadata["creation_time"] = format_tags["creation_time"]

        # Get device info from encoder
        if "encoder" in format_tags:
            encoder = format_tags["encoder"]
            # Extract device info (e.g., "iPhone Version 18.1.1")
            if "iPhone" in encoder or "iPad" in encoder:
                metadata["device"] = encoder

        return metadata

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        # ffprobe not available, file not found, or JSON parsing failed
        return {}


def format_duration(seconds: float) -> str:
    """Format duration in seconds as human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "3m 24s" or "1h 5m 30s"
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
