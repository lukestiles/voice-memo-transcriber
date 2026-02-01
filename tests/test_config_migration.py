"""Tests for config migration."""

import pytest
from transcribe_memos import migrate_legacy_config


@pytest.mark.unit
class TestConfigMigration:
    """Test configuration migration from legacy to new format."""

    def test_migrate_legacy_google_docs_config(self):
        """Test migrating legacy Google Docs config."""
        legacy_config = {
            "backend": "openai",
            "google_doc_id": "my-doc-id-123",
            "google_doc_title": "My Transcripts",
            "tab_date_format": "%Y-%m-%d",
            "voice_memos_path": "/path/to/memos",
            "data_dir": "/path/to/data",
        }

        migrated = migrate_legacy_config(legacy_config)

        # Check that destination structure was created
        assert "destination" in migrated
        assert migrated["destination"]["type"] == "google_docs"

        # Check that Google Docs settings were migrated
        google_docs_config = migrated["destination"]["google_docs"]
        assert google_docs_config["doc_id"] == "my-doc-id-123"
        assert google_docs_config["doc_title"] == "My Transcripts"
        assert google_docs_config["tab_date_format"] == "%Y-%m-%d"
        assert google_docs_config["use_weekly_docs"] is True

        # Check that other settings were preserved
        assert migrated["backend"] == "openai"
        assert migrated["voice_memos_path"] == "/path/to/memos"
        assert migrated["data_dir"] == "/path/to/data"

    def test_migrate_already_new_format(self):
        """Test that new format config is not modified."""
        new_config = {
            "backend": "local",
            "destination": {
                "type": "obsidian",
                "obsidian": {
                    "vault_path": "~/vault",
                },
            },
        }

        migrated = migrate_legacy_config(new_config)

        # Should return unchanged
        assert migrated == new_config

    def test_migrate_minimal_legacy_config(self):
        """Test migrating minimal legacy config."""
        legacy_config = {
            "backend": "local",
            "voice_memos_path": "/path",
            "data_dir": "/data",
        }

        migrated = migrate_legacy_config(legacy_config)

        # Should create destination structure with defaults
        assert "destination" in migrated
        assert migrated["destination"]["type"] == "google_docs"
        assert "google_docs" in migrated["destination"]
        assert "obsidian" in migrated["destination"]

    def test_migrate_partial_google_docs_settings(self):
        """Test migration with partial Google Docs settings."""
        legacy_config = {
            "backend": "openai",
            "google_doc_id": "",  # Empty doc_id - should not be migrated
            "google_doc_title": "Voice Memos",
            # tab_date_format not present
        }

        migrated = migrate_legacy_config(legacy_config)

        google_docs_config = migrated["destination"]["google_docs"]
        # Empty strings should not be migrated (bug fix #5)
        assert "doc_id" not in google_docs_config
        assert google_docs_config["doc_title"] == "Voice Memos"
        # tab_date_format should not be set if not present in legacy
        assert "tab_date_format" not in google_docs_config
