# Voice Memo Destinations Guide

This guide explains how to configure different destinations for your voice memo transcripts.

## Overview

The voice memo transcriber supports multiple destinations where your transcripts can be saved:

- **Google Docs**: Save to Google Docs with automatic organization by week and day
- **Obsidian**: Save to an Obsidian vault as markdown files with frontmatter

## Choosing a Destination

Edit the `CONFIG` dictionary in `transcribe_memos.py` and set the `destination` section.

## Google Docs Destination

### Configuration

```python
CONFIG = {
    # ... other settings ...

    "destination": {
        "type": "google_docs",

        "google_docs": {
            # Leave empty to create weekly docs automatically, or specify a doc ID
            "doc_id": "",

            # Title for new documents (used when doc_id is empty)
            "doc_title": "Voice Memo Transcripts",

            # Date format for tab titles (%B = month name, %d = day, %Y = year)
            "tab_date_format": "%B %d, %Y",

            # Create one doc per week (True) or use single doc (False)
            "use_weekly_docs": True,
        },
    },
}
```

### Features

- **Weekly Organization**: Creates one document per week (Monday-Sunday)
- **Daily Tabs**: One tab per day within each document
- **Automatic Headers**: Adds formatted headers with date and emoji
- **URL Output**: Prints direct link to each document

### Example Output

```
Week of 2025-01-27 Voice Memo Transcripts
├── Tab: January 27, 2025
│   ├── 📝 Meeting Notes
│   ├── 🕐 2025-01-27 09:15:32
│   └── Transcript...
└── Tab: January 28, 2025
    └── ...
```

## Obsidian Destination

### Configuration

```python
CONFIG = {
    # ... other settings ...

    "destination": {
        "type": "obsidian",

        "obsidian": {
            # Path to your Obsidian vault (required)
            "vault_path": "~/Documents/Obsidian/MyVault",

            # Folder within vault for transcripts
            "folder": "Voice Memos",

            # Organization: "daily" or "weekly"
            "organize_by": "daily",

            # Date format for filenames
            "date_format": "%Y-%m-%d",

            # Include YAML frontmatter
            "include_frontmatter": True,

            # Add #voice-memo tag
            "include_tags": True,

            # Extract and include audio metadata
            "include_metadata": True,
        },
    },
}
```

### Features

- **Daily or Weekly Files**: Choose how to organize your transcripts
- **YAML Frontmatter**: Includes date, type, tags, and memo count
- **Audio Metadata**: Extracts title, duration, and device from audio files
- **Markdown Formatting**: Clean, readable markdown with headers and separators
- **Automatic Linking**: Works seamlessly with Obsidian's linking features

### Example Output (Daily)

**File:** `2025-01-30.md`

```markdown
---
date: 2025-01-30
type: voice-memo-transcript
tags: [voice-memo]
memo_count: 2
---

# Voice Memos - January 30, 2025

---

## Meeting Notes

**Recorded:** 2025-01-30 09:15:32
**Duration:** 3m 24s
**Device:** iPhone Version 18.1.1

Discussion about the new project timeline and deliverables for Q1...

---

## Grocery List

**Recorded:** 2025-01-30 14:22:10
**Duration:** 45s

Milk, eggs, bread, coffee, bananas...

```

### Example Output (Weekly)

**File:** `2025-01-27 Week.md`

```markdown
---
date: 2025-01-27
type: voice-memo-transcript
tags: [voice-memo]
week: 2025-W05
memo_count: 5
---

# Voice Memos - Week of January 27, 2025

---

## Monday Meeting

**Recorded:** 2025-01-27 09:00:00
**Duration:** 15m 30s

Weekly standup notes...

---

## Ideas for Blog Post

**Recorded:** 2025-01-28 11:30:00
**Duration:** 2m 10s

Three ideas for next month's content...

```

### Setup Steps for Obsidian

1. **Find your vault path**:
   - Open Obsidian
   - Go to Settings → Files and Links
   - Note the "Vault folder" path

2. **Update config**:
   ```python
   "vault_path": "/Users/yourname/Documents/Obsidian/YourVault",
   ```

3. **Choose organization**:
   - `"organize_by": "daily"` - One file per day
   - `"organize_by": "weekly"` - One file per week

4. **Customize metadata** (optional):
   - Set `"include_metadata": False` to skip audio metadata extraction
   - Set `"include_frontmatter": False` for plain markdown files
   - Set `"include_tags": False` to remove tags

## Switching Destinations

You can switch between destinations at any time:

1. Change `"type"` in the config
2. Run the script
3. New transcripts will go to the new destination
4. Previously processed memos won't be re-transcribed

The `processed.json` file tracks which memos have been transcribed, regardless of destination.

## Legacy Configuration

If you're upgrading from an older version, your existing config will automatically migrate:

**Old format:**
```python
CONFIG = {
    "google_doc_id": "abc123",
    "google_doc_title": "My Transcripts",
    "tab_date_format": "%B %d, %Y",
}
```

**Automatically migrates to:**
```python
CONFIG = {
    "destination": {
        "type": "google_docs",
        "google_docs": {
            "doc_id": "abc123",
            "doc_title": "My Transcripts",
            "tab_date_format": "%B %d, %Y",
            "use_weekly_docs": True,
        },
    },
}
```

No action needed! The script will print a message and continue working.

## Creating Custom Destinations

Want to add support for Notion, Evernote, or plain text files? See the Developer Guide below.

### Developer Guide

To create a new destination:

1. Create a new file in `destinations/` (e.g., `notion.py`)

2. Implement the `TranscriptDestination` interface:

```python
from .base import TranscriptDestination

class NotionDestination(TranscriptDestination):
    def validate_config(self):
        # Check required config keys
        pass

    def initialize(self):
        # Setup API connection, authenticate
        pass

    def prepare_for_memo(self, memo_datetime):
        # Get/create page for this memo
        # Return session_id (e.g., page_id)
        return "page-id-123"

    def append_transcript(self, session_id, memo_name, timestamp,
                         transcript, memo_datetime, filepath):
        # Add transcript to the page
        pass

    def cleanup(self):
        # Print summary, close connections
        pass
```

3. Register in `destinations/__init__.py`:

```python
from .notion import NotionDestination
register_destination("notion", NotionDestination)
```

4. Add config section in `transcribe_memos.py`:

```python
"destination": {
    "type": "notion",
    "notion": {
        "api_key": "...",
        "database_id": "...",
    },
}
```

5. Write tests in `tests/test_destinations/test_notion.py`

See `destinations/obsidian.py` for a complete example.

## Troubleshooting

### Google Docs

**Issue**: "Google credentials not found"
- **Solution**: Follow the Google Docs setup in README.md

**Issue**: "Permission denied" errors
- **Solution**: Re-authenticate by deleting `~/.voice-memo-transcriber/token.json`

### Obsidian

**Issue**: "Not a valid Obsidian vault"
- **Solution**: Make sure the path points to the vault root (contains `.obsidian` folder)

**Issue**: "No metadata extracted"
- **Solution**: Install ffmpeg/ffprobe: `brew install ffmpeg` (macOS)

**Issue**: Frontmatter not updating
- **Solution**: Close the file in Obsidian before running the script

## Best Practices

### Google Docs
- Use weekly docs for ongoing organization
- Use single doc mode if you want everything in one place
- Customize tab_date_format to match your preference

### Obsidian
- Use daily organization for detailed tracking
- Use weekly organization for summarized views
- Keep metadata enabled for searchability
- Use frontmatter for Dataview queries

### General
- Run the script regularly (daily or after recording memos)
- Back up your destination (vault or Google Docs)
- Test configuration changes with a single memo first

## Support

For issues or questions:
- Check existing GitHub issues
- Review logs in `~/.voice-memo-transcriber/`
- Test with a single memo file first
