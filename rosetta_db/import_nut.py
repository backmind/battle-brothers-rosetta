"""
Import translations from base_<lang>.nut file into database.

Usage:
    python -m rosetta_db.import_nut rosetta/base_es.nut es
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rosetta_db.database import Database


def parse_nut_file(filepath: Path) -> list[dict]:
    """
    Parse a Rosetta .nut translation file and extract pairs.

    Format:
        // file\\path\\file.nut::context.path
        {
            en = "English text"
            es = "Spanish text"
            mode = "pattern"  // optional
        }
    """
    content = filepath.read_text(encoding='utf-8')
    pairs = []

    # Use regex to find all comment + block pairs
    # Pattern: // context_line followed by { ... }
    pattern = re.compile(
        r'//\s*([^\n]+::[^\n]+)\s*\n\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
        re.MULTILINE
    )

    for match in pattern.finditer(content):
        context_line = match.group(1).strip()
        block_content = match.group(2)

        pair = parse_block_simple(block_content, context_line)
        if pair:
            pairs.append(pair)

    return pairs


def parse_block_simple(block_content: str, context_line: str) -> Optional[dict]:
    """Parse block content with simpler approach."""

    # Extract file_path and context from comment
    file_path = None
    context = None

    if '::' in context_line:
        parts = context_line.split('::', 1)
        file_path = parts[0].strip()
        context = parts[1].strip() if len(parts) > 1 else None
        # Keep original path separators (DB uses backslashes)

    result = {'file_path': file_path, 'context': context}

    # Extract mode
    mode_match = re.search(r'mode\s*=\s*"([^"]+)"', block_content)
    if mode_match:
        result['mode'] = mode_match.group(1)

    # Extract strings using simpler pattern
    # Match: lang = "content" where content may span multiple lines
    for lang in ['en', 'es', 'ru']:
        # Find start of string
        lang_pattern = rf'\b{lang}\s*=\s*"'
        match = re.search(lang_pattern, block_content)
        if match:
            start_pos = match.end()
            # Find end quote (not preceded by odd number of backslashes)
            value = extract_quoted_string(block_content, start_pos)
            if value is not None:
                result[lang] = value

    # Valid pair needs at least en and one translation
    if 'en' in result and ('es' in result or 'ru' in result):
        return result

    return None


def extract_quoted_string(text: str, start: int) -> Optional[str]:
    """Extract string from position until unescaped quote."""
    result = []
    pos = start

    while pos < len(text):
        char = text[pos]

        if char == '"':
            # Check if escaped (odd number of preceding backslashes)
            num_backslashes = 0
            check_pos = pos - 1
            while check_pos >= start and text[check_pos] == '\\':
                num_backslashes += 1
                check_pos -= 1

            if num_backslashes % 2 == 0:
                # Not escaped - end of string
                break
            else:
                # Escaped quote - remove one backslash and keep quote
                if result and result[-1] == '\\':
                    result.pop()
                result.append('"')
        elif char == '\\' and pos + 1 < len(text):
            next_char = text[pos + 1]
            if next_char == 'n':
                result.append('\n')
                pos += 1
            elif next_char == 't':
                result.append('\t')
                pos += 1
            elif next_char == '"':
                # Will be handled in next iteration
                result.append('\\')
            elif next_char == '\\':
                result.append('\\')
                pos += 1
            else:
                result.append(char)
        else:
            result.append(char)

        pos += 1

    return ''.join(result) if pos < len(text) else None


def parse_block(block_text: str, context_line: Optional[str]) -> Optional[dict]:
    """Parse a single {en = "...", es = "..."} block."""

    # Extract file_path and context from comment
    file_path = None
    context = None

    if context_line and '::' in context_line:
        parts = context_line.split('::', 1)
        file_path = parts[0].strip()
        context = parts[1].strip() if len(parts) > 1 else None
        # Keep original path separators (DB uses backslashes)
        # file_path = file_path.replace('\\', '/')

    # Parse key-value pairs from block
    # Handle multiline strings with escaped quotes
    result = {'file_path': file_path, 'context': context}

    # Pattern for key = "value" or key = "value with \"quotes\""
    # Uses a state machine approach for complex strings

    # Extract mode first (simpler pattern)
    mode_match = re.search(r'mode\s*=\s*"([^"]+)"', block_text)
    if mode_match:
        result['mode'] = mode_match.group(1)

    # Extract en and es values (can be multiline)
    for lang in ['en', 'es', 'ru']:
        value = extract_string_value(block_text, lang)
        if value is not None:
            result[lang] = value

    # Valid pair needs at least en and one translation
    if 'en' in result and ('es' in result or 'ru' in result):
        return result

    return None


def extract_string_value(block: str, key: str) -> Optional[str]:
    """Extract string value for a key, handling escaped quotes and newlines."""
    # Find the key
    pattern = rf'\b{key}\s*=\s*"'
    match = re.search(pattern, block)
    if not match:
        return None

    start = match.end()

    # Find closing quote (not escaped)
    pos = start
    result = []
    while pos < len(block):
        char = block[pos]
        if char == '"':
            # Check if escaped
            num_backslashes = 0
            check_pos = pos - 1
            while check_pos >= start and block[check_pos] == '\\':
                num_backslashes += 1
                check_pos -= 1

            if num_backslashes % 2 == 0:
                # Not escaped - end of string
                break
            else:
                # Escaped quote
                result.append(char)
        elif char == '\\' and pos + 1 < len(block):
            next_char = block[pos + 1]
            if next_char == 'n':
                result.append('\n')
                pos += 1
            elif next_char == 't':
                result.append('\t')
                pos += 1
            elif next_char == '"':
                result.append('"')
                pos += 1
            elif next_char == '\\':
                result.append('\\')
                pos += 1
            else:
                result.append(char)
        else:
            result.append(char)
        pos += 1

    return ''.join(result)


def import_translations(db: Database, pairs: list[dict], lang: str,
                       status: str = 'reviewed', verbose: bool = False) -> dict:
    """Import translations from parsed pairs into database."""
    stats = {'imported': 0, 'skipped': 0, 'not_found': 0, 'already_exists': 0}

    for pair in pairs:
        if lang not in pair:
            stats['skipped'] += 1
            continue

        file_path = pair.get('file_path')
        context = pair.get('context')
        en_text = pair.get('en')
        translated = pair.get(lang)

        if not all([file_path, context, en_text, translated]):
            stats['skipped'] += 1
            continue

        # Find string in database
        string_id = db.find_string_by_content(file_path, context, en_text)

        if not string_id:
            # Try fuzzy match - same file_path and context, different en_text
            matches = db.get_strings_by_file_context(file_path, context)
            if matches:
                # Show what we found vs what we have
                if verbose:
                    print(f"No exact match for: {file_path}::{context}")
                    print(f"  NUT: {en_text[:60]}...")
                    for m in matches[:2]:
                        print(f"  DB:  {m['en_text'][:60]}...")
            stats['not_found'] += 1
            continue

        # Check if translation already exists
        existing = db.get_translation(string_id, lang)
        if existing and existing.get('translated_text'):
            stats['already_exists'] += 1
            continue

        # Save translation
        db.save_translation(string_id, lang, translated, status=status)
        stats['imported'] += 1

        if verbose and stats['imported'] % 500 == 0:
            print(f"  Imported {stats['imported']} translations...")

    return stats


def main():
    if len(sys.argv) < 3:
        print("Usage: python -m rosetta_db.import_nut <nut_file> <lang>")
        print("Example: python -m rosetta_db.import_nut rosetta/base_es.nut es")
        sys.exit(1)

    nut_file = Path(sys.argv[1])
    lang = sys.argv[2]
    verbose = '-v' in sys.argv or '--verbose' in sys.argv

    if not nut_file.exists():
        print(f"File not found: {nut_file}")
        sys.exit(1)

    print(f"Parsing {nut_file}...")
    pairs = parse_nut_file(nut_file)
    print(f"Found {len(pairs)} translation pairs")

    print(f"\nImporting to database (lang={lang})...")
    with Database() as db:
        stats = import_translations(db, pairs, lang, verbose=verbose)

    print(f"\nImport complete:")
    print(f"  Imported:       {stats['imported']}")
    print(f"  Already exists: {stats['already_exists']}")
    print(f"  Not found in DB: {stats['not_found']}")
    print(f"  Skipped:        {stats['skipped']}")


if __name__ == '__main__':
    main()
