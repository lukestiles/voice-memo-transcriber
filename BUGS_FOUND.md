# Bug Report - Voice Memo Transcriber Destination Abstraction

## Critical Bugs 🔴

### 1. **Obsidian: Unsafe String Replacement in `_update_memo_count()`**
**File:** `destinations/obsidian.py:232-275`
**Severity:** HIGH
**Impact:** Could corrupt file content if memo_count value appears elsewhere in the document

**Issue:**
```python
# Line 272
content = content.replace(old_line, new_line)
```

If the string `"memo_count: 1"` appears anywhere in the transcript text (not just frontmatter), it will be replaced. This could corrupt user content.

**Example:**
```markdown
---
memo_count: 1
---

Transcript: "I need to increase memo_count: 1 to memo_count: 2"
```
After update, the transcript text would be changed to:
```
Transcript: "I need to increase memo_count: 2 to memo_count: 2"
```

**Fix:** Use regex to replace only in the frontmatter section, or better yet, parse YAML properly.

---

### 2. **Obsidian: Double File Read in `_update_memo_count()`**
**File:** `destinations/obsidian.py:232-275`
**Severity:** MEDIUM
**Impact:** Performance issue and potential race condition

**Issue:**
The function reads the file twice:
- Lines 246-247: Read to extract current count
- Lines 263-264: Read again to update

This is inefficient and could cause issues if the file changes between reads (e.g., user editing in Obsidian).

**Fix:** Read once, parse, update, write.

---

### 3. **Main Script: Session Cache Uses Wrong Key for Weekly Docs**
**File:** `transcribe_memos.py:423-450`
**Severity:** MEDIUM
**Impact:** Creates unnecessary documents/tabs, defeats caching purpose

**Issue:**
```python
# Line 445
date_key = memo_datetime.strftime("%Y-%m-%d")
```

For Google Docs with `use_weekly_docs=True`, multiple memos on different days of the same week should use the same document. But the cache uses daily keys, so:
- Monday memo: Creates doc for week of 2025-01-27
- Tuesday memo: Calls `prepare_for_memo()` again (cache miss), retrieves same doc
- Wednesday memo: Calls `prepare_for_memo()` again (cache miss), retrieves same doc

This works but is inefficient - it makes redundant API calls.

**Example:**
```
Monday (2025-01-27):    cache["2025-01-27"] = "doc123:tab1"
Tuesday (2025-01-28):   cache["2025-01-28"] = "doc123:tab2"  # Same doc, new tab
Wednesday (2025-01-29): cache["2025-01-29"] = "doc123:tab3"  # Same doc, new tab
```

Each date triggers a new `prepare_for_memo()` call and doc/tab lookup.

**Fix:** Cache key should incorporate the destination's organization strategy (weekly vs daily).

---

## Major Bugs 🟡

### 4. **Google Docs: File Structure Conflict Between Weekly and Single Mode**
**File:** `destinations/google_docs.py:140-204`
**Severity:** MEDIUM
**Impact:** Confusing state when switching between modes

**Issue:**
The `docs_by_week.json` file can have two different structures:

**Weekly mode:**
```json
{
  "2025-01-27": "doc-id-1",
  "2025-02-03": "doc-id-2"
}
```

**Single mode:**
```json
{
  "single_doc": "doc-id-3"
}
```

When switching from weekly to single mode:
1. File contains `{"2025-01-27": "doc-id-1", ...}`
2. Single mode checks for `"single_doc"` key (line 157)
3. Key not found, creates new doc
4. Saves `{"single_doc": "doc-id-new"}` (line 168)
5. Old weekly docs are lost from tracking file

**Fix:** Use separate files (`docs_by_week.json` and `single_doc.json`) or use a structured format:
```json
{
  "mode": "weekly",
  "weekly": { "2025-01-27": "doc-id-1" },
  "single": null
}
```

---

### 5. **Config Migration: Migrates Empty String Values**
**File:** `transcribe_memos.py:72-124`
**Severity:** LOW
**Impact:** Unnecessary config entries

**Issue:**
```python
# Line 106-107
if "google_doc_id" in config:
    migrated["destination"]["google_docs"]["doc_id"] = config["google_doc_id"]
```

If `google_doc_id` is an empty string `""`, it's still migrated. This is technically harmless but adds unnecessary keys to the config.

**Fix:**
```python
if "google_doc_id" in config and config["google_doc_id"]:
    migrated["destination"]["google_docs"]["doc_id"] = config["google_doc_id"]
```

---

### 6. **Obsidian: Week Number Calculation Inconsistency**
**File:** `destinations/obsidian.py:178`
**Severity:** LOW
**Impact:** Week numbers in frontmatter might not match file organization

**Issue:**
```python
week_num = date.isocalendar()[1]  # ISO week number
```

But file organization uses:
```python
monday = self._get_monday_of_week(date)  # Custom Monday calculation
```

ISO week numbering has different rules:
- Week 1 is the week with the first Thursday of the year
- Custom `_get_monday_of_week()` just finds the Monday of any given week

**Example Edge Case:**
- January 1, 2025 is a Wednesday
- ISO week: Week 1 (because Jan 2 is Thursday)
- Custom Monday: Would be Dec 30, 2024

This creates a mismatch between the file name and frontmatter week number.

**Fix:** Use consistent method for both, either ISO or custom throughout.

---

## Minor Bugs 🟢

### 7. **Obsidian: Special Characters in Metadata Titles**
**File:** `destinations/obsidian.py:215`
**Severity:** LOW
**Impact:** Markdown formatting could break

**Issue:**
```python
content += f"## {metadata.get('title', memo_name)}\n\n"
```

If the title contains characters that have special meaning in markdown (like `#`, `[`, `]`, `*`, etc.), it could break formatting.

**Example:**
Title: `"Meeting #1 [Important]"`
Output: `## Meeting #1 [Important]`

This works, but if title is: `"## Already a header ##"`
Output: `## ## Already a header ##` (malformed)

**Fix:** Sanitize title or escape special characters.

---

### 8. **Missing Validation After `destination.initialize()`**
**File:** `transcribe_memos.py:411-416`
**Severity:** LOW
**Impact:** Unclear error states

**Issue:**
```python
try:
    destination = create_destination(dest_type, dest_settings, str(data_dir))
    destination.initialize()
except Exception as e:
    print(f"❌ Failed to initialize destination: {e}")
    return
```

The code catches exceptions but doesn't distinguish between:
- Failed to create destination (wrong type, bad config)
- Failed to initialize (auth failure, network issue)

Both get the same generic message.

**Fix:** Separate try-catch blocks or more specific error messages.

---

### 9. **Obsidian: Missing Directory Creation for Custom Folder**
**File:** `destinations/obsidian.py:67-71`
**Severity:** LOW (already handled)
**Impact:** None (works correctly)

**Note:** This is actually NOT a bug - line 71 has `mkdir(parents=True, exist_ok=True)` which handles it correctly. Just documenting for completeness.

---

### 10. **Google Docs: No Cleanup for Partial Document Creation**
**File:** `destinations/google_docs.py:163-174, 192-204`
**Severity:** LOW
**Impact:** Orphaned docs if crash occurs between creation and saving

**Issue:**
If the program crashes between:
1. Creating the doc (line 163 or 192)
2. Saving to mapping file (line 167-168 or 197-198)

The document will exist in Google Docs but won't be tracked in `docs_by_week.json`.

**Fix:** Save to file first with a "pending" marker, then update after doc creation succeeds.

---

## Potential Issues ⚠️

### 11. **Concurrent Access to Obsidian Files**
**File:** `destinations/obsidian.py` (multiple methods)
**Severity:** INFO
**Impact:** File corruption if Obsidian is open

If user has the markdown file open in Obsidian while the script runs, there could be conflicts:
- Script appends to file
- User is editing the same file
- Changes might conflict or be lost

**Recommendation:** Add warning in documentation about closing files before running script.

---

### 12. **No Validation of Destination Type at Config Level**
**File:** `transcribe_memos.py:406-408`
**Severity:** INFO
**Impact:** Runtime error if typo in destination type

```python
dest_type = dest_config["type"]
dest_settings = dest_config.get(dest_type, {})
```

If `type: "googledocs"` (typo), it will fail when trying to create destination, but error message won't be clear about the typo.

**Fix:** Validate destination type early and suggest corrections for typos.

---

## Summary

| Severity | Count | Examples |
|----------|-------|----------|
| 🔴 Critical | 3 | String replacement bug, double file read, cache key issue |
| 🟡 Major | 3 | File structure conflict, empty string migration, week number |
| 🟢 Minor | 4 | Special chars, validation, orphaned docs, etc. |
| ⚠️  Info | 2 | Concurrent access, type validation |
| **Total** | **12** | |

---

## Recommendations

### Priority 1 (Fix Immediately)
1. Fix Obsidian `_update_memo_count()` string replacement (Bug #1)
2. Optimize file reading in `_update_memo_count()` (Bug #2)
3. Fix session cache key strategy (Bug #3)

### Priority 2 (Fix Soon)
4. Restructure Google Docs file storage (Bug #4)
5. Improve config migration logic (Bug #5)
6. Align week number calculations (Bug #6)

### Priority 3 (Nice to Have)
7-12. Address minor issues and add validation

---

## Testing Recommendations

1. **Test Mode Switching:** Test switching between weekly/single mode in Google Docs
2. **Test Special Characters:** Test Obsidian with titles containing markdown characters
3. **Test Same Week:** Test multiple memos in the same week to verify caching
4. **Test Edge Dates:** Test year-end dates (Dec 31, Jan 1) for week number consistency
5. **Test Concurrent Access:** Test running script while Obsidian is open
6. **Test Failure Scenarios:** Test network failures during doc creation

---

**Date:** January 31, 2026
**Reviewer:** Claude
**Status:** 12 bugs identified, 3 critical, 3 major, 4 minor, 2 informational
