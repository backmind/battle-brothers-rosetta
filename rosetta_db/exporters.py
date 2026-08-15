"""
Exporters - PO/JSON export/import for translation platforms.

Supports:
- PO (Gettext) format for Weblate
- JSON format for Crowdin (TODO)
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any

import polib

from .database import Database


# Pattern placeholder transformation: <name:type> <-> {name}
PATTERN_RE = re.compile(r'<(\w+):(\w+)>')
PLACEHOLDER_RE = re.compile(r'\{(\w+)\}')


def _pattern_to_placeholder(text: str) -> str:
    """Convert <name:type> to {name} for display in translation tools."""
    return PATTERN_RE.sub(r'{\1}', text)


def _placeholder_to_pattern(text: str, reference: str) -> str:
    """
    Convert {name} back to <name:type> using reference string for types.

    Args:
        text: Translated text with {name} placeholders
        reference: Original English text with <name:type> patterns
    """
    # Extract type info from reference
    types = {m.group(1): m.group(2) for m in PATTERN_RE.finditer(reference)}

    def replace(m):
        name = m.group(1)
        typ = types.get(name, 'str')  # Default to str if not found
        return f'<{name}:{typ}>'

    return PLACEHOLDER_RE.sub(replace, text)


def export_po(
    db: Database,
    version: str,
    lang: str,
    output_path: Optional[Path] = None,
    include_translated: bool = True
) -> str:
    """
    Export strings to PO (Gettext) format for Weblate.

    Args:
        db: Database instance
        version: Game version to export
        lang: Target language code
        output_path: Where to write file (None = return string only)
        include_translated: Include already translated strings

    Returns:
        PO file content as string
    """
    strings = db.get_strings_for_compile(version, lang)

    # Create PO file
    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': f'battle-brothers-{version}',
        'Report-Msgid-Bugs-To': 'https://github.com/Suor/battle-brothers-rosetta/issues',
        'POT-Creation-Date': '',
        'PO-Revision-Date': '',
        'Last-Translator': '',
        'Language-Team': lang,
        'Language': lang,
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
    }

    for s in strings:
        translated = s.get('translated_text') or ''

        # Skip translated if not requested
        if not include_translated and translated:
            continue

        en_text = s['en_text']
        mode = s.get('mode', 'literal')
        context = s.get('context', '')
        file_path = s.get('file_path', '')

        # Build msgctxt for disambiguation
        msgctxt = f"{file_path}::{context}" if context else file_path

        # Transform patterns for readability
        msgid = _pattern_to_placeholder(en_text) if mode == 'pattern' else en_text
        msgstr = _pattern_to_placeholder(translated) if mode == 'pattern' and translated else translated

        # Add comment about mode
        comment = f"mode: {mode}" if mode != 'literal' else ""

        entry = polib.POEntry(
            msgid=msgid,
            msgstr=msgstr,
            msgctxt=msgctxt,
            occurrences=[(file_path, '')],
            comment=comment
        )
        po.append(entry)

    content = str(po)

    if output_path:
        output_path.write_text(content, encoding='utf-8')

    return content


def import_po(
    db: Database,
    po_path: Path,
    lang: str,
    status: str = 'reviewed'
) -> Dict[str, int]:
    """
    Import translations from PO file into database.

    Args:
        db: Database instance
        po_path: Path to PO file
        lang: Target language code
        status: Translation status to set (pending/auto/reviewed)

    Returns:
        Stats dict: {imported, skipped, not_found}
    """
    po = polib.pofile(str(po_path))

    stats = {'imported': 0, 'skipped': 0, 'not_found': 0}

    for entry in po:
        if not entry.msgstr:
            stats['skipped'] += 1
            continue

        # Parse msgctxt to get file_path and context
        msgctxt = entry.msgctxt or ''
        if '::' in msgctxt:
            file_path, context = msgctxt.split('::', 1)
        else:
            file_path = msgctxt
            context = ''

        msgid = entry.msgid
        msgstr = entry.msgstr

        # Check if this is a pattern (has placeholders)
        is_pattern = bool(PLACEHOLDER_RE.search(msgid))

        # Convert placeholders back to patterns if needed
        if is_pattern:
            # Find original string in DB to get type info
            strings = db.get_strings_by_file_context(file_path, context)
            if strings:
                original = strings[0]['en_text']
                msgid = _placeholder_to_pattern(msgid, original)
                msgstr = _placeholder_to_pattern(msgstr, original)

        # Find string in database
        string_id = db.find_string_by_content(file_path, context, msgid)

        if string_id:
            db.save_translation(
                string_id=string_id,
                lang=lang,
                translated_text=msgstr,
                status=status,
                translator='weblate-import'
            )
            stats['imported'] += 1
        else:
            stats['not_found'] += 1

    return stats


def export_json(
    db: Database,
    version: str,
    lang: str,
    output_path: Optional[Path] = None
) -> str:
    """
    Export strings to JSON format for Crowdin.

    TODO: Implement based on Crowdin format requirements.
    """
    import json

    strings = db.get_strings_for_compile(version, lang)

    data = {
        'version': version,
        'language': lang,
        'strings': []
    }

    for s in strings:
        data['strings'].append({
            'id': s['id'],
            'file': s['file_path'],
            'context': s.get('context', ''),
            'source': s['en_text'],
            'translation': s.get('translated_text') or '',
            'mode': s.get('mode', 'literal')
        })

    content = json.dumps(data, ensure_ascii=False, indent=2)

    if output_path:
        output_path.write_text(content, encoding='utf-8')

    return content
