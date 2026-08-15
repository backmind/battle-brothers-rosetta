import argparse
import polib
import re
from collections import defaultdict
from pathlib import Path
import sys

# Add project root to path to import rosetta module
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import rosetta
from rosetta import extract


def fix_corrupted_unicode(text):
    """
    Fix corrupted Unicode escape sequences in translated text.

    Some translation files have literal '\\x0000' replacing accented characters.
    This function attempts to restore them based on context.
    """
    # The literal escape sequence to look for
    escape_seq = chr(92) + 'x0000'  # backslash + x0000

    if escape_seq not in text:
        return text

    result = text

    # Pattern: n + \x0000 + vowel -> ñ + vowel (e.g., "grun\x0000e" -> "gruñe")
    for vowel in 'aeiouAEIOU':
        result = result.replace('n' + escape_seq + vowel, 'ñ' + vowel)
        result = result.replace('N' + escape_seq + vowel, 'Ñ' + vowel)

    # Pattern: "a\x0000rbol" -> "árbol" (the escape replaces the accent mark)
    # This is specifically for cases where vowel + \x0000 + consonant = accented vowel + consonant
    accent_map = {
        'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ú',
        'A': 'Á', 'E': 'É', 'I': 'Í', 'O': 'Ó', 'U': 'Ú',
    }

    # Handle: vowel + \x0000 + consonant -> accented_vowel + consonant
    consonants = 'bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ'
    for vowel, accented in accent_map.items():
        for cons in consonants:
            result = result.replace(vowel + escape_seq + cons, accented + cons)

    # Fallback: any remaining \x0000 followed by a letter - just remove the escape
    import string
    for char in string.ascii_letters:
        result = result.replace(escape_seq + char, char)

    return result


def find_nut_files(directory):
    """Finds all .nut files in a directory."""
    return sorted(Path(directory).rglob('*.nut'))


def compute_similarity(orig_text, trans_text):
    """
    Compute a similarity score between original and translated text.
    Higher score = more likely to be a correct match.
    """
    score = 0.0

    # Length ratio scoring - ideal is 1.0-1.3 for EN->ES
    # Give continuous score based on how close to ideal
    len_ratio = len(trans_text) / len(orig_text) if orig_text else 0

    # Ideal ratio for EN->ES is around 1.0-1.3 (Spanish is often slightly longer)
    ideal_ratio = 1.15
    ratio_deviation = abs(len_ratio - ideal_ratio)

    if ratio_deviation < 0.2:
        score += 3.0  # Excellent match
    elif ratio_deviation < 0.4:
        score += 2.0  # Good match
    elif ratio_deviation < 0.7:
        score += 1.0  # Acceptable
    elif ratio_deviation < 1.0:
        score += 0.3  # Poor but possible
    # else: very poor ratio, no points

    # Structural markers that should be preserved
    markers = ['{', '[img]', '%SPEECH_ON%', '%SPEECH_OFF%', '%randombrother%',
               '%employer%', '|', '\n']
    for marker in markers:
        orig_has = marker in orig_text
        trans_has = marker in trans_text
        if orig_has == trans_has:
            score += 0.3
        elif orig_has != trans_has:
            score -= 1.0  # Strong penalty for missing markers

    # Starting/ending patterns
    if orig_text and trans_text:
        # Both start with same structural char
        if orig_text[0] == trans_text[0] and orig_text[0] in '{[':
            score += 1.0
        # Both end with punctuation
        if orig_text[-1] in '.!?' and trans_text[-1] in '.!?':
            score += 0.2

    return score


def find_best_match(orig_text, trans_list, used_indices, orig_pos=0):
    """
    Find the best matching translation from trans_list for orig_text.
    Returns (index, trans_pair) or (None, None) if no good match found.

    orig_pos: position of orig_text in its list, used for tie-breaking
    """
    best_score = -999
    best_idx = None
    best_pair = None

    for idx, trans_pair in enumerate(trans_list):
        if idx in used_indices:
            continue

        trans_text = trans_pair.get('en', '')
        if not trans_text or orig_text == trans_text:
            continue

        score = compute_similarity(orig_text, trans_text)

        # Position preference: bonus for being close to expected position
        # For very short strings, position is the PRIMARY signal since length ratio is unreliable
        pos_distance = abs(idx - orig_pos)
        if len(orig_text) < 15:
            # Very short strings: position dominates (up to 10.0 bonus, -3.0 per position)
            pos_bonus = max(0, 10.0 - (pos_distance * 3.0))
        elif len(orig_text) < 30:
            # Short strings: position is important (up to 3.0 bonus)
            pos_bonus = max(0, 3.0 - (pos_distance * 0.8))
        else:
            # Long strings: position is a tie-breaker
            pos_bonus = max(0, 0.5 - (pos_distance * 0.1))
        score += pos_bonus

        if score > best_score:
            best_score = score
            best_idx = idx
            best_pair = trans_pair

    # Only return if we have a reasonable match
    if best_score >= 0.5:
        return best_idx, best_pair
    return None, None


def create_po_from_dirs(orig_dir, trans_dir, output_file):
    """
    Creates a PO file by comparing original and translated .nut files.

    Matching strategy:
    - Group strings by context
    - If counts match: use position-based matching
    - If counts differ: use similarity-based matching (length, structure markers)
    """
    print(f"Original directory: {orig_dir}")
    print(f"Translated directory: {trans_dir}")

    orig_files = find_nut_files(orig_dir)
    trans_files = find_nut_files(trans_dir)

    orig_path_map = {p.relative_to(orig_dir): p for p in orig_files}
    trans_path_map = {p.relative_to(trans_dir): p for p in trans_files}

    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': 'Battle Brothers Translation',
        'Report-Msgid-Bugs-To': '',
        'POT-Creation-Date': '2024-01-01 00:00+0000',
        'PO-Revision-Date': '2024-01-01 00:00+0000',
        'Last-Translator': 'User',
        'Language-Team': 'Spanish',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
    }

    processed_files = 0
    total_files = len(orig_path_map)
    paired_strings = 0
    mismatched_contexts = 0

    for rel_path, orig_abs_path in orig_path_map.items():
        processed_files += 1
        print(f"[{processed_files}/{total_files}] Processing: {rel_path}", end='\r')

        if rel_path not in trans_path_map:
            continue

        trans_abs_path = trans_path_map[rel_path]

        try:
            orig_content = orig_abs_path.read_text(encoding='utf-8')
            trans_content = trans_abs_path.read_text(encoding='utf-8')

            # Fix corrupted Unicode in translated files before extraction
            trans_content = fix_corrupted_unicode(trans_content)

            # Extract strings from both files
            # IMPORTANT: Clear SEEN set before each extraction to avoid cross-contamination
            rosetta.SEEN.clear()
            orig_pairs = [p for p in extract(orig_content, filename=str(orig_abs_path)) if isinstance(p, dict)]
            rosetta.SEEN.clear()
            trans_pairs = [p for p in extract(trans_content, filename=str(trans_abs_path)) if isinstance(p, dict)]

            # Group strings by context
            orig_by_context = defaultdict(list)
            for op in orig_pairs:
                ctx = op.get('_context', '')
                if ctx:
                    orig_by_context[ctx].append(op)

            trans_by_context = defaultdict(list)
            for tp in trans_pairs:
                ctx = tp.get('_context', '')
                if ctx:
                    trans_by_context[ctx].append(tp)

            # Process each context group
            for context_str, orig_list in orig_by_context.items():
                trans_list = trans_by_context.get(context_str, [])

                if not trans_list:
                    continue

                # Check if counts match
                use_similarity = len(orig_list) != len(trans_list)
                if use_similarity:
                    mismatched_contexts += 1

                used_indices = set()

                for pos, orig_pair in enumerate(orig_list):
                    orig_text = orig_pair.get('en')
                    if not orig_text:
                        continue

                    trans_pair = None

                    if use_similarity:
                        # Use similarity-based matching
                        idx, trans_pair = find_best_match(orig_text, trans_list, used_indices, orig_pos=pos)
                        if idx is not None:
                            used_indices.add(idx)
                    else:
                        # Use position-based matching
                        if pos < len(trans_list):
                            trans_pair = trans_list[pos]
                            used_indices.add(pos)

                    if trans_pair is None:
                        continue

                    trans_text = trans_pair.get('en')

                    if not trans_text or orig_text == trans_text:
                        continue

                    # Build msgctxt for disambiguation
                    file_path_str = str(rel_path)
                    msgctxt = f"{file_path_str}::{context_str}"

                    entry = polib.POEntry(
                        msgid=orig_text,
                        msgstr=trans_text,
                        msgctxt=msgctxt
                    )
                    po.append(entry)
                    paired_strings += 1

        except Exception as e:
            print(f"\nError processing file {rel_path}: {e}")

    po.save(output_file)
    print(f"\n\nProcessing complete.")
    print(f"Successfully created '{output_file}' with {paired_strings} translation pairs.")
    if mismatched_contexts > 0:
        print(f"Used similarity matching for {mismatched_contexts} context groups with count mismatches.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Create a .po file from original and translated .nut file directories."
    )
    parser.add_argument(
        "original_dir",
        help="Path to the directory with original (English) .nut files."
    )
    parser.add_argument(
        "translated_dir",
        help="Path to the directory with translated (Spanish) .nut files."
    )
    parser.add_argument(
        "-o", "--output",
        default="translation_1.5.1.7.po",
        help="Name of the output .po file."
    )
    args = parser.parse_args()

    create_po_from_dirs(args.original_dir, args.translated_dir, args.output)
