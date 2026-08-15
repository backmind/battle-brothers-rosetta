"""Tests for rosetta_db.database module."""

import tempfile
from pathlib import Path

import pytest

from rosetta_db.database import Database, compute_string_id


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    database = Database(db_path)
    yield database
    database.close()
    db_path.unlink()


class TestComputeStringId:
    def test_basic(self):
        id1 = compute_string_id("file.nut", "context", "Hello")
        assert len(id1) == 16
        assert id1.isalnum()

    def test_deterministic(self):
        id1 = compute_string_id("file.nut", "ctx", "text")
        id2 = compute_string_id("file.nut", "ctx", "text")
        assert id1 == id2

    def test_different_file(self):
        id1 = compute_string_id("file1.nut", "ctx", "text")
        id2 = compute_string_id("file2.nut", "ctx", "text")
        assert id1 != id2

    def test_different_context(self):
        id1 = compute_string_id("file.nut", "ctx1", "text")
        id2 = compute_string_id("file.nut", "ctx2", "text")
        assert id1 != id2

    def test_different_text(self):
        id1 = compute_string_id("file.nut", "ctx", "text1")
        id2 = compute_string_id("file.nut", "ctx", "text2")
        assert id1 != id2


class TestStringCRUD:
    def test_insert_and_get(self, db):
        string_id = compute_string_id("test.nut", "m.Name", "Hello")
        db.insert_string(string_id, "test.nut", "m.Name", "Hello", "1.0.0")

        result = db.get_string(string_id)
        assert result is not None
        assert result['file_path'] == "test.nut"
        assert result['context'] == "m.Name"
        assert result['en_text'] == "Hello"
        assert result['first_seen_version'] == "1.0.0"
        assert result['last_seen_version'] == "1.0.0"
        assert result['status'] == "active"

    def test_get_nonexistent(self, db):
        result = db.get_string("nonexistent")
        assert result is None

    def test_update_version(self, db):
        string_id = compute_string_id("test.nut", "ctx", "text")
        db.insert_string(string_id, "test.nut", "ctx", "text", "1.0.0")
        db.update_string_version(string_id, "1.0.1")

        result = db.get_string(string_id)
        assert result['first_seen_version'] == "1.0.0"
        assert result['last_seen_version'] == "1.0.1"

    def test_update_text(self, db):
        string_id = compute_string_id("test.nut", "ctx", "old text")
        db.insert_string(string_id, "test.nut", "ctx", "old text", "1.0.0")
        db.update_string_text(string_id, "new text", "1.0.1")

        result = db.get_string(string_id)
        assert result['en_text'] == "new text"
        assert result['status'] == "modified"

    def test_count_strings(self, db):
        assert db.count_strings() == 0

        db.insert_string("id1", "f1.nut", "c1", "t1", "1.0")
        db.insert_string("id2", "f2.nut", "c2", "t2", "1.0")
        assert db.count_strings() == 2
        assert db.count_strings(version="1.0") == 2
        assert db.count_strings(version="2.0") == 0

    def test_get_strings_by_version(self, db):
        db.insert_string("id1", "f1.nut", "c1", "t1", "1.0")
        db.insert_string("id2", "f2.nut", "c2", "t2", "1.0")
        db.insert_string("id3", "f3.nut", "c3", "t3", "2.0")

        v1_strings = db.get_strings_by_version("1.0")
        assert len(v1_strings) == 2

        v2_strings = db.get_strings_by_version("2.0")
        assert len(v2_strings) == 1


class TestTranslations:
    def test_save_and_get(self, db):
        string_id = "test_id"
        db.insert_string(string_id, "f.nut", "ctx", "Hello", "1.0")
        db.save_translation(string_id, "ru", "Привет", status="reviewed")

        result = db.get_translation(string_id, "ru")
        assert result is not None
        assert result['translated_text'] == "Привет"
        assert result['translation_status'] == "reviewed"

    def test_update_translation(self, db):
        string_id = "test_id"
        db.insert_string(string_id, "f.nut", "ctx", "Hello", "1.0")
        db.save_translation(string_id, "ru", "Привет", status="auto")
        db.save_translation(string_id, "ru", "Здравствуй", status="reviewed")

        result = db.get_translation(string_id, "ru")
        assert result['translated_text'] == "Здравствуй"
        assert result['translation_status'] == "reviewed"

    def test_get_untranslated(self, db):
        db.insert_string("id1", "f1.nut", "c1", "Hello", "1.0")
        db.insert_string("id2", "f2.nut", "c2", "World", "1.0")
        db.save_translation("id1", "ru", "Привет")

        untranslated = db.get_untranslated("ru", "1.0")
        assert len(untranslated) == 1
        assert untranslated[0]['id'] == "id2"

    def test_mark_for_review(self, db):
        string_id = "test_id"
        db.insert_string(string_id, "f.nut", "ctx", "Hello", "1.0")
        db.save_translation(string_id, "ru", "Привет", status="reviewed")
        db.mark_translations_for_review(string_id)

        result = db.get_translation(string_id, "ru")
        assert result['translation_status'] == "needs_review"


class TestVersionChanges:
    def test_record_change(self, db):
        db.insert_string("id1", "f.nut", "ctx", "text", "1.0")
        db.record_change("id1", "added", "1.0")

        # Just verify no error
        changes = db.get_changes(None, "1.0")
        assert len(changes['added']) == 1

    def test_get_changes_added(self, db):
        db.insert_string("id1", "f.nut", "ctx", "text", "2.0")

        changes = db.get_changes("1.0", "2.0")
        assert len(changes['added']) == 1
        assert changes['added'][0]['id'] == "id1"

    def test_get_changes_no_from_version(self, db):
        db.insert_string("id1", "f.nut", "ctx", "text", "1.0")
        db.insert_string("id2", "f2.nut", "ctx2", "text2", "1.0")

        changes = db.get_changes(None, "1.0")
        assert len(changes['added']) == 2


class TestGameVersions:
    def test_save_and_get(self, db):
        db.save_version("1.5.1.7", 3847, notes="Initial extraction")

        versions = db.get_versions()
        assert len(versions) == 1
        assert versions[0]['version'] == "1.5.1.7"
        assert versions[0]['total_strings'] == 3847

    def test_get_latest(self, db):
        db.save_version("1.0", 100)
        db.save_version("2.0", 200)

        latest = db.get_latest_version()
        assert latest == "2.0"

    def test_get_latest_empty(self, db):
        assert db.get_latest_version() is None


class TestCompile:
    def test_get_strings_for_compile(self, db):
        db.insert_string("id1", "f.nut", "ctx", "Hello", "1.0")
        db.insert_string("id2", "f2.nut", "ctx2", "World", "1.0")
        db.save_translation("id1", "ru", "Привет")

        strings = db.get_strings_for_compile("1.0", "ru")
        assert len(strings) == 2

        # id1 has translation
        s1 = next(s for s in strings if s['id'] == "id1")
        assert s1['translated_text'] == "Привет"

        # id2 has no translation
        s2 = next(s for s in strings if s['id'] == "id2")
        assert s2['translated_text'] is None


class TestCacheIntegration:
    def test_get_cached_no_table(self, db):
        # Should return None gracefully when table doesn't exist
        result = db.get_cached_translation("claude35", "Hello")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
