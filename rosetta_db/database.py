"""
Database layer for versioned translation management.

Extends existing translations.db with new tables for version tracking.
Preserves existing translations_cache_ru table used by xt.py.
"""

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Use same database file as xt.py
DB_PATH = Path(__file__).parent.parent / "translations.db"


def compute_string_id(file_path: str, context: str, en_text: str) -> str:
    """
    Generate stable identifier for a string across versions.

    Hash input: file_path + "|" + context + "|" + en_text

    If file moves, creates new ID (acceptable - treat as new string).
    """
    content = f"{file_path}|{context}|{en_text}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class Database:
    """Database connection and operations for versioned translations."""

    SCHEMA = """
    -- NOTE: Existing tables from xt.py are preserved:
    -- translations_cache_ru (engine, conf, input, output)
    -- cache (ckey, cval, expires)

    -- Core strings table
    CREATE TABLE IF NOT EXISTS strings (
        id TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        context TEXT NOT NULL,
        en_text TEXT NOT NULL,
        mode TEXT DEFAULT 'literal',
        pattern_data TEXT,

        first_seen_version TEXT NOT NULL,
        last_seen_version TEXT,
        status TEXT DEFAULT 'active',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_strings_version ON strings(last_seen_version);
    CREATE INDEX IF NOT EXISTS idx_strings_status ON strings(status);
    CREATE INDEX IF NOT EXISTS idx_strings_file ON strings(file_path);

    -- Translations with status tracking
    CREATE TABLE IF NOT EXISTS translations (
        string_id TEXT NOT NULL,
        lang TEXT NOT NULL,
        translated_text TEXT NOT NULL,
        translation_status TEXT DEFAULT 'pending',
        translator TEXT,
        auto_engine TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        PRIMARY KEY (string_id, lang),
        FOREIGN KEY (string_id) REFERENCES strings(id)
    );

    -- Version tracking
    CREATE TABLE IF NOT EXISTS version_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        string_id TEXT NOT NULL,
        from_version TEXT,
        to_version TEXT NOT NULL,
        change_type TEXT NOT NULL,
        old_en_text TEXT,

        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (string_id) REFERENCES strings(id)
    );

    CREATE INDEX IF NOT EXISTS idx_changes_version ON version_changes(to_version);

    -- Game versions metadata
    CREATE TABLE IF NOT EXISTS game_versions (
        version TEXT PRIMARY KEY,
        extracted_at TIMESTAMP,
        total_strings INTEGER,
        notes TEXT
    );
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.con = sqlite3.connect(self.db_path)
        self.con.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize schema (idempotent - safe to call multiple times)."""
        self.con.executescript(self.SCHEMA)
        self.con.commit()

    def close(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # --- String CRUD ---

    def get_string(self, string_id: str) -> Optional[Dict[str, Any]]:
        """Get string by ID."""
        cur = self.con.execute(
            "SELECT * FROM strings WHERE id = ?", (string_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def insert_string(
        self,
        string_id: str,
        file_path: str,
        context: str,
        en_text: str,
        version: str,
        mode: str = 'literal',
        pattern_data: Optional[str] = None
    ) -> None:
        """Insert a new string."""
        self.con.execute("""
            INSERT INTO strings (id, file_path, context, en_text, mode, pattern_data,
                                 first_seen_version, last_seen_version, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (string_id, file_path, context, en_text, mode, pattern_data, version, version))
        self.con.commit()

    def update_string_version(self, string_id: str, version: str) -> None:
        """Update last_seen_version for an existing string."""
        self.con.execute("""
            UPDATE strings
            SET last_seen_version = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (version, string_id))
        self.con.commit()

    def update_string_text(
        self,
        string_id: str,
        en_text: str,
        version: str
    ) -> None:
        """Update en_text when string content changes."""
        self.con.execute("""
            UPDATE strings
            SET en_text = ?, last_seen_version = ?, status = 'modified',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (en_text, version, string_id))
        self.con.commit()

    def mark_strings_removed(self, version: str, exclude_ids: List[str]) -> int:
        """Mark strings not seen in this version as removed."""
        if not exclude_ids:
            # No strings found - mark all previous as removed
            cur = self.con.execute("""
                UPDATE strings
                SET status = 'removed', updated_at = CURRENT_TIMESTAMP
                WHERE status = 'active'
            """)
        else:
            placeholders = ','.join('?' * len(exclude_ids))
            cur = self.con.execute(f"""
                UPDATE strings
                SET status = 'removed', updated_at = CURRENT_TIMESTAMP
                WHERE status = 'active' AND id NOT IN ({placeholders})
                  AND last_seen_version != ?
            """, (*exclude_ids, version))
        self.con.commit()
        return cur.rowcount

    def get_strings_by_version(
        self,
        version: str,
        status: str = 'active'
    ) -> List[Dict[str, Any]]:
        """Get all strings for a specific version."""
        cur = self.con.execute("""
            SELECT * FROM strings
            WHERE last_seen_version = ? AND status = ?
            ORDER BY file_path, context
        """, (version, status))
        return [dict(row) for row in cur.fetchall()]

    def get_strings_for_compile(
        self,
        version: str,
        lang: str
    ) -> List[Dict[str, Any]]:
        """Get strings with translations for compilation."""
        cur = self.con.execute("""
            SELECT s.*, t.translated_text, t.translation_status
            FROM strings s
            LEFT JOIN translations t ON s.id = t.string_id AND t.lang = ?
            WHERE s.last_seen_version = ? AND s.status = 'active'
            ORDER BY s.file_path, s.context
        """, (lang, version))
        return [dict(row) for row in cur.fetchall()]

    def count_strings(self, version: Optional[str] = None) -> int:
        """Count strings, optionally filtered by version."""
        if version:
            cur = self.con.execute(
                "SELECT COUNT(*) FROM strings WHERE last_seen_version = ? AND status = 'active'",
                (version,)
            )
        else:
            cur = self.con.execute(
                "SELECT COUNT(*) FROM strings WHERE status = 'active'"
            )
        return cur.fetchone()[0]

    # --- Translation CRUD ---

    def get_translation(self, string_id: str, lang: str) -> Optional[Dict[str, Any]]:
        """Get translation for a string."""
        cur = self.con.execute("""
            SELECT * FROM translations WHERE string_id = ? AND lang = ?
        """, (string_id, lang))
        row = cur.fetchone()
        return dict(row) if row else None

    def save_translation(
        self,
        string_id: str,
        lang: str,
        translated_text: str,
        status: str = 'pending',
        translator: Optional[str] = None,
        auto_engine: Optional[str] = None
    ) -> None:
        """Save or update a translation."""
        self.con.execute("""
            INSERT INTO translations (string_id, lang, translated_text, translation_status,
                                      translator, auto_engine)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(string_id, lang) DO UPDATE SET
                translated_text = excluded.translated_text,
                translation_status = excluded.translation_status,
                translator = excluded.translator,
                auto_engine = excluded.auto_engine,
                updated_at = CURRENT_TIMESTAMP
        """, (string_id, lang, translated_text, status, translator, auto_engine))
        self.con.commit()

    def get_untranslated(self, lang: str, version: str) -> List[Dict[str, Any]]:
        """Get strings without translations for a language."""
        cur = self.con.execute("""
            SELECT s.* FROM strings s
            LEFT JOIN translations t ON s.id = t.string_id AND t.lang = ?
            WHERE s.last_seen_version = ? AND s.status = 'active'
              AND (t.translated_text IS NULL OR t.translated_text = '')
            ORDER BY s.file_path, s.context
        """, (lang, version))
        return [dict(row) for row in cur.fetchall()]

    def mark_translations_for_review(self, string_id: str) -> None:
        """Mark all translations of a string as needing review."""
        self.con.execute("""
            UPDATE translations
            SET translation_status = 'needs_review', updated_at = CURRENT_TIMESTAMP
            WHERE string_id = ?
        """, (string_id,))
        self.con.commit()

    # --- Version Changes ---

    def record_change(
        self,
        string_id: str,
        change_type: str,
        to_version: str,
        from_version: Optional[str] = None,
        old_en_text: Optional[str] = None
    ) -> None:
        """Record a version change for a string."""
        self.con.execute("""
            INSERT INTO version_changes (string_id, from_version, to_version, change_type, old_en_text)
            VALUES (?, ?, ?, ?, ?)
        """, (string_id, from_version, to_version, change_type, old_en_text))
        self.con.commit()

    def get_changes(
        self,
        from_version: Optional[str],
        to_version: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get changes between versions."""
        result = {'added': [], 'modified': [], 'removed': []}

        if from_version:
            # Added: first_seen in to_version
            cur = self.con.execute("""
                SELECT * FROM strings WHERE first_seen_version = ?
            """, (to_version,))
            result['added'] = [dict(row) for row in cur.fetchall()]

            # Modified: changed between versions
            cur = self.con.execute("""
                SELECT s.*, vc.old_en_text FROM strings s
                JOIN version_changes vc ON s.id = vc.string_id
                WHERE vc.from_version = ? AND vc.to_version = ? AND vc.change_type = 'modified'
            """, (from_version, to_version))
            result['modified'] = [dict(row) for row in cur.fetchall()]

            # Removed: status changed to removed in to_version
            cur = self.con.execute("""
                SELECT * FROM strings
                WHERE status = 'removed' AND last_seen_version = ?
            """, (from_version,))
            result['removed'] = [dict(row) for row in cur.fetchall()]
        else:
            # No from_version - all strings in to_version are "added"
            result['added'] = self.get_strings_by_version(to_version)

        return result

    # --- Game Versions ---

    def save_version(
        self,
        version: str,
        total_strings: int,
        notes: Optional[str] = None
    ) -> None:
        """Save or update game version metadata."""
        self.con.execute("""
            INSERT INTO game_versions (version, extracted_at, total_strings, notes)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            ON CONFLICT(version) DO UPDATE SET
                extracted_at = CURRENT_TIMESTAMP,
                total_strings = excluded.total_strings,
                notes = excluded.notes
        """, (version, total_strings, notes))
        self.con.commit()

    def get_versions(self) -> List[Dict[str, Any]]:
        """Get all recorded game versions."""
        cur = self.con.execute("""
            SELECT * FROM game_versions ORDER BY extracted_at DESC
        """)
        return [dict(row) for row in cur.fetchall()]

    def get_latest_version(self) -> Optional[str]:
        """Get the most recently extracted version."""
        cur = self.con.execute("""
            SELECT version FROM game_versions ORDER BY extracted_at DESC, version DESC LIMIT 1
        """)
        row = cur.fetchone()
        return row[0] if row else None

    # --- Search helpers for import ---

    def get_strings_by_file_context(
        self,
        file_path: str,
        context: str
    ) -> List[Dict[str, Any]]:
        """Find strings by file path and context."""
        cur = self.con.execute("""
            SELECT * FROM strings
            WHERE file_path = ? AND context = ? AND status = 'active'
        """, (file_path, context))
        return [dict(row) for row in cur.fetchall()]

    def find_string_by_content(
        self,
        file_path: str,
        context: str,
        en_text: str
    ) -> Optional[str]:
        """Find string ID by file, context, and English text."""
        cur = self.con.execute("""
            SELECT id FROM strings
            WHERE file_path = ? AND context = ? AND en_text = ? AND status = 'active'
        """, (file_path, context, en_text))
        row = cur.fetchone()
        return row[0] if row else None

    # --- Integration with xt.py cache ---

    def get_cached_translation(self, engine: str, en_text: str) -> Optional[str]:
        """
        Look up cached translation from xt.py's translations_cache_ru.

        This allows reusing existing translations without re-calling APIs.
        """
        # Check if table exists (may not if xt.py hasn't been run)
        cur = self.con.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='translations_cache_ru'
        """)
        if not cur.fetchone():
            return None

        cur = self.con.execute("""
            SELECT output FROM translations_cache_ru
            WHERE engine = ? AND input = ?
            ORDER BY added DESC LIMIT 1
        """, (engine, en_text))
        row = cur.fetchone()
        return row[0] if row else None
