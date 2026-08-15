"""
Extractor wrapper - bridges rosetta.py parser to database.

Thin wrapper that calls extract() and stores results with version tracking.
"""

import sys
from pathlib import Path
from typing import Optional, List, Tuple

# Add parent dir to path to import rosetta
sys.path.insert(0, str(Path(__file__).parent.parent))

from rosetta import extract, FILES_SKIP_RE
from .database import Database, compute_string_id


def extract_to_database(
    source_dir: Path,
    version: str,
    db: Optional[Database] = None,
    verbose: bool = False
) -> dict:
    """
    Extract strings from .nut files and store in database.

    Args:
        source_dir: Directory containing .nut files
        version: Game version identifier (e.g., "1.5.1.7")
        db: Database instance (creates new if None)
        verbose: Print progress info

    Returns:
        dict with counts: {added, modified, unchanged, removed, errors}
    """
    own_db = db is None
    if own_db:
        db = Database()

    try:
        previous_version = db.get_latest_version()
        stats = {'added': 0, 'modified': 0, 'unchanged': 0, 'removed': 0, 'errors': 0}
        seen_ids = []

        # Find all .nut files
        nut_files = sorted(source_dir.glob("**/*.nut"))
        total_files = len(nut_files)

        for i, file_path in enumerate(nut_files, 1):
            # Skip rosetta/test/mock files
            rel_path = str(file_path.relative_to(source_dir))
            if FILES_SKIP_RE.search(rel_path):
                if verbose:
                    print(f"[{i}/{total_files}] SKIP: {rel_path}", file=sys.stderr)
                continue

            if verbose:
                print(f"[{i}/{total_files}] {rel_path}", file=sys.stderr)

            try:
                file_stats = _extract_file(db, file_path, rel_path, version, seen_ids)
                for key in stats:
                    if key in file_stats:
                        stats[key] += file_stats[key]
            except Exception as e:
                stats['errors'] += 1
                print(f"ERROR in {rel_path}: {e}", file=sys.stderr)

        # Mark strings not seen in this version as removed
        if previous_version and seen_ids:
            stats['removed'] = db.mark_strings_removed(version, seen_ids)

        # Save version metadata
        total_strings = stats['added'] + stats['modified'] + stats['unchanged']
        db.save_version(version, total_strings)

        return stats

    finally:
        if own_db:
            db.close()


def _extract_file(
    db: Database,
    file_path: Path,
    rel_path: str,
    version: str,
    seen_ids: List[str]
) -> dict:
    """Extract strings from a single file."""
    stats = {'added': 0, 'modified': 0, 'unchanged': 0}

    code = file_path.read_text(encoding='utf-8')
    pairs = list(extract(code, filename=str(file_path)))

    for pair in pairs:
        if isinstance(pair, str):
            # Skip comment/reference strings from parser
            continue

        en_text = pair.get('en', '')
        context = pair.get('_context', '')
        mode = pair.get('mode', 'literal')

        if not en_text:
            continue

        string_id = compute_string_id(rel_path, context, en_text)
        seen_ids.append(string_id)

        existing = db.get_string(string_id)

        if not existing:
            # New string
            db.insert_string(
                string_id=string_id,
                file_path=rel_path,
                context=context,
                en_text=en_text,
                version=version,
                mode=mode
            )
            db.record_change(string_id, 'added', version)
            stats['added'] += 1

        elif existing['en_text'] != en_text:
            # Modified string (same ID but different text - shouldn't happen often
            # since ID includes en_text, but handle edge cases)
            old_text = existing['en_text']
            db.update_string_text(string_id, en_text, version)
            db.record_change(
                string_id, 'modified', version,
                from_version=existing['last_seen_version'],
                old_en_text=old_text
            )
            db.mark_translations_for_review(string_id)
            stats['modified'] += 1

        else:
            # Unchanged - just update version
            db.update_string_version(string_id, version)
            stats['unchanged'] += 1

    return stats


def diff_versions(db: Database, from_version: str, to_version: str) -> dict:
    """
    Get diff between two versions.

    Returns:
        dict with 'added', 'modified', 'removed' lists
    """
    return db.get_changes(from_version, to_version)


def print_diff(diff: dict, verbose: bool = False):
    """Print version diff summary."""
    print(f"Added: {len(diff['added'])} strings")
    print(f"Modified: {len(diff['modified'])} strings")
    print(f"Removed: {len(diff['removed'])} strings")

    if verbose:
        if diff['added']:
            print("\n--- Added ---")
            for s in diff['added'][:10]:
                print(f"  {s['file_path']}::{s['context']}")
                print(f"    EN: {s['en_text'][:60]}...")
            if len(diff['added']) > 10:
                print(f"  ... and {len(diff['added']) - 10} more")

        if diff['modified']:
            print("\n--- Modified ---")
            for s in diff['modified'][:10]:
                print(f"  {s['file_path']}::{s['context']}")
                print(f"    OLD: {s.get('old_en_text', '?')[:60]}...")
                print(f"    NEW: {s['en_text'][:60]}...")
            if len(diff['modified']) > 10:
                print(f"  ... and {len(diff['modified']) - 10} more")
