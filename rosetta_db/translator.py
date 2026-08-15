"""
Auto-translation wrapper around xt.py engines.

Integrates xt.py translation engines (Claude, Yandex) with the rosetta_db database.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path to import xt
sys.path.insert(0, str(Path(__file__).parent.parent))

from .database import Database


def auto_translate(
    db: Database,
    lang: str,
    version: str,
    engine: str = 'claude35',
    batch_size: int = 50,
    status: str = 'auto',
    verbose: bool = False
) -> Dict[str, int]:
    """
    Auto-translate untranslated strings using xt.py engines.

    Args:
        db: Database instance
        lang: Target language code (e.g., 'ru')
        version: Game version to translate
        engine: Translation engine ('claude35' or 'yt')
        batch_size: Number of strings to translate per API call
        status: Translation status to set ('auto', 'pending', 'reviewed')
        verbose: Print progress

    Returns:
        Stats dict: {translated, cached, errors, skipped}
    """
    # Import xt.py (lazy import to avoid initialization until needed)
    import xt
    xt.init()

    # Get untranslated strings
    strings = db.get_untranslated(lang, version)

    if not strings:
        return {'translated': 0, 'cached': 0, 'errors': 0, 'skipped': 0}

    stats = {'translated': 0, 'cached': 0, 'errors': 0, 'skipped': 0}

    # Process in batches
    for i in range(0, len(strings), batch_size):
        batch = strings[i:i + batch_size]

        # Extract English texts
        texts = [s['en_text'] for s in batch]

        if verbose:
            print(f"Translating batch {i // batch_size + 1}/{(len(strings) + batch_size - 1) // batch_size} "
                  f"({len(batch)} strings)...", file=sys.stderr)

        try:
            # Call xt.translate - it handles caching internally
            translations = xt.translate(engine, texts)

            # Save translations to database
            for s, translated in zip(batch, translations):
                if translated:
                    db.save_translation(
                        string_id=s['id'],
                        lang=lang,
                        translated_text=translated,
                        status=status,
                        auto_engine=engine
                    )
                    stats['translated'] += 1
                else:
                    stats['skipped'] += 1

        except Exception as e:
            if verbose:
                print(f"Error translating batch: {e}", file=sys.stderr)
            stats['errors'] += len(batch)

    return stats


def translate_modified(
    db: Database,
    lang: str,
    from_version: str,
    to_version: str,
    engine: str = 'claude35',
    verbose: bool = False
) -> Dict[str, int]:
    """
    Translate only strings that were added or modified between versions.

    Args:
        db: Database instance
        lang: Target language code
        from_version: Previous version
        to_version: Current version
        engine: Translation engine
        verbose: Print progress

    Returns:
        Stats dict
    """
    # Get changes between versions
    changes = db.get_changes(from_version, to_version)

    # Collect string IDs that need translation
    needs_translation = []

    # Added strings - definitely need translation
    for s in changes['added']:
        needs_translation.append(s)

    # Modified strings - mark for review and re-translate
    for s in changes['modified']:
        db.mark_translations_for_review(s['id'])
        needs_translation.append(s)

    if not needs_translation:
        return {'translated': 0, 'cached': 0, 'errors': 0, 'skipped': 0}

    if verbose:
        print(f"Found {len(needs_translation)} strings needing translation "
              f"({len(changes['added'])} added, {len(changes['modified'])} modified)",
              file=sys.stderr)

    # Import xt.py
    import xt
    xt.init()

    stats = {'translated': 0, 'cached': 0, 'errors': 0, 'skipped': 0}

    texts = [s['en_text'] for s in needs_translation]

    try:
        translations = xt.translate(engine, texts)

        for s, translated in zip(needs_translation, translations):
            if translated:
                db.save_translation(
                    string_id=s['id'],
                    lang=lang,
                    translated_text=translated,
                    status='auto',
                    auto_engine=engine
                )
                stats['translated'] += 1
            else:
                stats['skipped'] += 1

    except Exception as e:
        if verbose:
            print(f"Error translating: {e}", file=sys.stderr)
        stats['errors'] += len(needs_translation)

    return stats


def check_cache_coverage(
    db: Database,
    lang: str,
    version: str,
    engine: str = 'claude35'
) -> Dict[str, int]:
    """
    Check how many strings already have cached translations in xt.py cache.

    Useful for estimating API costs before running auto_translate.

    Returns:
        Dict with 'cached', 'uncached', 'total' counts
    """
    strings = db.get_untranslated(lang, version)

    cached = 0
    for s in strings:
        # Check xt.py's translations_cache_ru
        cached_trans = db.get_cached_translation(engine, s['en_text'])
        if cached_trans:
            cached += 1

    return {
        'cached': cached,
        'uncached': len(strings) - cached,
        'total': len(strings)
    }
