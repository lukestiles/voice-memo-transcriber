# Google Docs Custom Grouping

This document describes the flexible custom grouping options available for the Google Docs destination.

## Overview

The Google Docs destination now supports flexible organization of transcripts at two levels:

1. **Document-Level Grouping**: How to organize separate documents
2. **Tab-Level Grouping**: How to organize tabs within each document

## Configuration

Add grouping configuration to your Google Docs destination config in `transcribe_memos.py`:

```python
"google_docs": {
    # Document grouping (how to organize documents)
    "doc_grouping": "monthly",  # Options: weekly, monthly, quarterly, yearly, single, tag

    # Tab grouping (how to organize tabs within documents)
    "tab_grouping": "daily",  # Options: daily, weekly, time-of-day, duration, none, tag

    # Optional: Custom patterns and formats
    "tab_date_format": "%B %d, %Y",  # For daily/weekly tabs
    "doc_tag_pattern": r"#(\w+)",  # Regex for tag extraction

    # Optional: Custom ranges
    "tab_time_ranges": {
        "Morning": (6, 12),
        "Afternoon": (12, 18),
        "Evening": (18, 24),
        "Night": (0, 6)
    },
    "tab_duration_ranges": {  # In seconds
        "Quick Notes": (0, 120),
        "Standard": (120, 600),
        "Extended": (600, float('inf'))
    }
}
```

## Document Grouping Options

### `weekly` (default)
One document per week, Monday-based.

**Example:**
```
📄 2026-02-09 Voice Memo Transcripts
📄 2026-02-16 Voice Memo Transcripts
📄 2026-02-23 Voice Memo Transcripts
```

### `monthly`
One document per month.

**Example:**
```
📄 2026-01 Voice Memo Transcripts
📄 2026-02 Voice Memo Transcripts
📄 2026-03 Voice Memo Transcripts
```

### `quarterly`
One document per quarter (Q1, Q2, Q3, Q4).

**Example:**
```
📄 2026-Q1 Voice Memo Transcripts
📄 2026-Q2 Voice Memo Transcripts
📄 2026-Q3 Voice Memo Transcripts
```

### `yearly`
One document per year.

**Example:**
```
📄 2025 Voice Memo Transcripts
📄 2026 Voice Memo Transcripts
```

### `tag`
Separate documents based on tags in memo titles. Requires `doc_tag_pattern` configuration.

**Example:**
With memos titled "Meeting notes #project-alpha" and "Ideas #content":
```
📄 #project-alpha Voice Memo Transcripts
📄 #content Voice Memo Transcripts
📄 Untagged Voice Memo Transcripts
```

**Configuration:**
```python
"doc_grouping": "tag",
"doc_tag_pattern": r"#(\w+)"  # Matches hashtags like #project-alpha
```

### `single`
One document for all transcripts (same as `use_weekly_docs: False`).

**Example:**
```
📄 Voice Memo Transcripts
```

## Tab Grouping Options

### `daily` (default)
One tab per day.

**Example:**
```
📄 2026-02 Voice Memo Transcripts
  ├─ 📑 February 01, 2026
  ├─ 📑 February 02, 2026
  └─ 📑 February 03, 2026
```

**Configuration:**
```python
"tab_grouping": "daily",
"tab_date_format": "%B %d, %Y"  # Customize date format
```

### `weekly`
One tab per week within the document.

**Example:**
```
📄 2026 Voice Memo Transcripts
  ├─ 📑 Week of February 01, 2026
  ├─ 📑 Week of February 08, 2026
  └─ 📑 Week of February 15, 2026
```

### `time-of-day`
Group by time of day (morning, afternoon, evening, night).

**Example:**
```
📄 2026-02 Voice Memo Transcripts
  ├─ 📑 Morning (6:00-12:00)
  ├─ 📑 Afternoon (12:00-18:00)
  ├─ 📑 Evening (18:00-24:00)
  └─ 📑 Night (0:00-6:00)
```

**Configuration:**
```python
"tab_grouping": "time-of-day",
"tab_time_ranges": {
    "Morning": (6, 12),    # 6am to 12pm
    "Afternoon": (12, 18), # 12pm to 6pm
    "Evening": (18, 24),   # 6pm to midnight
    "Night": (0, 6)        # midnight to 6am
}
```

### `duration`
Group by memo duration (requires audio metadata).

**Example:**
```
📄 2026-02 Voice Memo Transcripts
  ├─ 📑 Quick Notes
  ├─ 📑 Standard
  └─ 📑 Extended
```

**Configuration:**
```python
"tab_grouping": "duration",
"tab_duration_ranges": {  # Duration in seconds
    "Quick Notes": (0, 120),           # Under 2 minutes
    "Standard": (120, 600),             # 2-10 minutes
    "Extended": (600, float('inf'))     # Over 10 minutes
}
```

### `tag`
Separate tabs based on tags in memo titles.

**Example:**
```
📄 2026-02 Voice Memo Transcripts
  ├─ 📑 #work
  ├─ 📑 #personal
  └─ 📑 Untagged
```

**Configuration:**
```python
"tab_grouping": "tag",
"doc_tag_pattern": r"#(\w+)"  # Or use tab_tag_pattern for different pattern
```

### `none`
No tabs - all memos in one continuous document.

**Example:**
```
📄 Voice Memo Transcripts
  (All memos in one continuous document body)
```

## Configuration Examples

### Example 1: Monthly Documents, Daily Tabs

Organize by month with one tab per day.

```python
"google_docs": {
    "doc_grouping": "monthly",
    "tab_grouping": "daily",
    "tab_date_format": "%B %d, %Y"
}
```

**Result:**
```
📄 2026-02 Voice Memo Transcripts
  ├─ 📑 February 01, 2026
  ├─ 📑 February 02, 2026
  └─ 📑 February 03, 2026
```

### Example 2: Yearly Documents, Weekly Tabs

One document per year with weekly tabs.

```python
"google_docs": {
    "doc_grouping": "yearly",
    "tab_grouping": "weekly"
}
```

**Result:**
```
📄 2026 Voice Memo Transcripts
  ├─ 📑 Week of February 01, 2026
  ├─ 📑 Week of February 08, 2026
  └─ 📑 Week of February 15, 2026
```

### Example 3: Quarterly Documents, Time-of-Day Tabs

Organize by quarter with time-based tabs.

```python
"google_docs": {
    "doc_grouping": "quarterly",
    "tab_grouping": "time-of-day",
    "tab_time_ranges": {
        "Morning": (6, 12),
        "Afternoon": (12, 18),
        "Evening": (18, 24),
        "Night": (0, 6)
    }
}
```

**Result:**
```
📄 2026-Q1 Voice Memo Transcripts
  ├─ 📑 Morning (6:00-12:00)
  ├─ 📑 Afternoon (12:00-18:00)
  ├─ 📑 Evening (18:00-24:00)
  └─ 📑 Night (0:00-6:00)
```

### Example 4: Tag-Based Documents and Daily Tabs

Separate documents by project tag.

```python
"google_docs": {
    "doc_grouping": "tag",
    "doc_tag_pattern": r"#(\w+)",
    "tab_grouping": "daily",
    "tab_date_format": "%B %d"
}
```

**With memos titled:**
- "Meeting notes #project-alpha"
- "Ideas for blog #content"
- "Grocery list"

**Result:**
```
📄 #project-alpha Voice Memo Transcripts
  ├─ 📑 February 01
  └─ 📑 February 03

📄 #content Voice Memo Transcripts
  └─ 📑 February 02

📄 Untagged Voice Memo Transcripts
  └─ 📑 February 01
```

### Example 5: Monthly Documents, Duration-Based Tabs

Organize by month with duration-based tabs.

```python
"google_docs": {
    "doc_grouping": "monthly",
    "tab_grouping": "duration",
    "tab_duration_ranges": {
        "Quick Notes": (0, 120),
        "Standard Memos": (120, 600),
        "Long Recordings": (600, float('inf'))
    }
}
```

**Result:**
```
📄 2026-02 Voice Memo Transcripts
  ├─ 📑 Quick Notes
  ├─ 📑 Standard Memos
  └─ 📑 Long Recordings
```

### Example 6: Single Document, No Tabs

One continuous document for all transcripts.

```python
"google_docs": {
    "doc_grouping": "single",
    "tab_grouping": "none"
}
```

**Result:**
```
📄 Voice Memo Transcripts
  (All memos in one continuous document, no tabs)
```

## Backward Compatibility

The new grouping system is fully backward compatible:

- **Old `use_weekly_docs: true`** → Maps to `doc_grouping: "weekly"`
- **Old `use_weekly_docs: false`** → Maps to `doc_grouping: "single"`
- **Old `tab_date_format`** → Still works with daily tab grouping
- **No configuration** → Defaults to weekly docs with daily tabs (original behavior)

## Migration

You can migrate gradually:

1. **Keep existing behavior**: No changes needed - continues working as before
2. **Change document grouping**: Add `doc_grouping` to try monthly/quarterly/yearly
3. **Change tab grouping**: Add `tab_grouping` to try time-of-day/duration
4. **Advanced features**: Add custom patterns for tag-based grouping

## Metadata Requirements

Some grouping strategies require audio metadata:

- **Duration-based grouping** (`tab_grouping: "duration"`): Requires audio file duration
- **Tag-based grouping** (`doc_grouping: "tag"` or `tab_grouping: "tag"`): Requires audio file title metadata

The system automatically extracts metadata from audio files when available.

## Tips

1. **Choose combinations wisely**: Consider how you'll search for memos later
2. **Time-of-day works well with daily docs**: `doc_grouping: "daily"` + `tab_grouping: "time-of-day"`
3. **Tags are powerful for projects**: Use `doc_grouping: "tag"` to separate work projects
4. **Duration helps with workflow**: Quick notes vs. detailed recordings
5. **Start simple**: Try monthly docs with daily tabs before advanced features

## Troubleshooting

### Memos not appearing in expected tabs

- Check that your system clock is accurate
- For duration-based grouping, verify audio metadata is being extracted
- For tag-based grouping, check that your memo titles contain the expected tags

### Multiple documents being created

- Verify your `doc_grouping` configuration
- Check that dates are being parsed correctly
- Ensure consistent tag patterns in memo titles

### Tabs not being created

- Verify `tab_grouping` is not set to `"none"`
- Check that the grouping criteria (time, duration, tags) matches your memos
- Ensure metadata extraction is working for duration/tag-based grouping
