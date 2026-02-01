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
            # Document grouping strategy
            "doc_grouping": "monthly",  # Options: weekly, monthly, quarterly, yearly, tag, single

            # Tab grouping strategy
            "tab_grouping": "daily",  # Options: daily, weekly, time-of-day, duration, tag, none

            # Optional: Custom date format for daily/weekly tabs
            "tab_date_format": "%B %d, %Y",  # e.g., "February 01, 2026"

            # Optional: Time ranges for time-of-day grouping
            "tab_time_ranges": {
                "Morning": (6, 12),
                "Afternoon": (12, 18),
                "Evening": (18, 24),
                "Night": (0, 6)
            },

            # Optional: Duration ranges for duration-based grouping (in seconds)
            "tab_duration_ranges": {
                "Quick Notes": (0, 120),
                "Standard": (120, 600),
                "Extended": (600, float('inf'))
            },

            # Optional: Tag pattern for tag-based grouping
            "doc_tag_pattern": r"#(\w+)",  # Matches hashtags like #project-alpha

            # Legacy options (still supported)
            # "doc_id": "",  # Specify a single doc ID (overrides grouping)
            # "use_weekly_docs": True,  # Auto-migrates to doc_grouping
        },
    },
}
```

### Features

- **Flexible Document Grouping**: 6 grouping strategies for documents
  - Weekly (Monday-based), Monthly, Quarterly, Yearly, Tag-based, or Single document
- **Flexible Tab Grouping**: 6 grouping strategies for tabs within documents
  - Daily, Weekly, Time-of-day, Duration-based, Tag-based, or No tabs
- **36 Total Combinations**: Mix and match doc and tab strategies
- **Metadata-Based Grouping**: Uses audio file title and duration for smart organization
- **Tag Support**: Organize by hashtags in memo titles (e.g., `#project-alpha`)
- **Automatic Headers**: Adds formatted headers with date and emoji
- **URL Output**: Prints direct link to each document
- **Backward Compatible**: Automatically migrates old configurations

### Grouping Examples

**Example 1: Monthly docs with daily tabs** (recommended for most users)
```python
"doc_grouping": "monthly",
"tab_grouping": "daily"
```
Output:
```
📄 2026-02 Voice Memo Transcripts
  ├─ 📑 February 01, 2026
  ├─ 📑 February 02, 2026
  └─ 📑 February 03, 2026
```

**Example 2: Quarterly docs with time-of-day tabs** (context-based organization)
```python
"doc_grouping": "quarterly",
"tab_grouping": "time-of-day",
"tab_time_ranges": {
    "Morning": (6, 12),
    "Afternoon": (12, 18),
    "Evening": (18, 24),
    "Night": (0, 6)
}
```
Output:
```
📄 2026-Q1 Voice Memo Transcripts
  ├─ 📑 Morning (6:00-12:00)
  ├─ 📑 Afternoon (12:00-18:00)
  ├─ 📑 Evening (18:00-24:00)
  └─ 📑 Night (0:00-6:00)
```

**Example 3: Tag-based docs with daily tabs** (project organization)
```python
"doc_grouping": "tag",
"doc_tag_pattern": r"#(\w+)",
"tab_grouping": "daily"
```
With memos titled:
- "Meeting notes #project-alpha"
- "Ideas for blog #content"

Output:
```
📄 #project-alpha Voice Memo Transcripts
  ├─ 📑 February 01
  └─ 📑 February 03

📄 #content Voice Memo Transcripts
  └─ 📑 February 02

📄 Untagged Voice Memo Transcripts
  └─ 📑 February 01
```

**Example 4: Yearly docs with duration tabs** (archive by length)
```python
"doc_grouping": "yearly",
"tab_grouping": "duration",
"tab_duration_ranges": {
    "Quick Notes": (0, 120),
    "Standard": (120, 600),
    "Extended": (600, float('inf'))
}
```
Output:
```
📄 2026 Voice Memo Transcripts
  ├─ 📑 Quick Notes
  ├─ 📑 Standard
  └─ 📑 Extended
```

**Example 5: Single doc with no tabs** (continuous document)
```python
"doc_grouping": "single",
"tab_grouping": "none"
```
Output:
```
📄 Voice Memo Transcripts
  (All memos in one continuous document)
```

See [docs/google-docs-grouping.md](docs/google-docs-grouping.md) for complete reference with all 36 combinations.

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
