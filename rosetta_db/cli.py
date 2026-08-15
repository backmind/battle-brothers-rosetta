"""
CLI entry point for rosetta_db commands.

Usage:
    python -m rosetta_db extract <dir> --version <ver>
    python -m rosetta_db diff <v1> <v2>
    python -m rosetta_db status
"""

import sys
from pathlib import Path
from typing import Optional

import click

from .database import Database
from .extractor import extract_to_database, diff_versions, print_diff
from .compiler import compile_translation, compile_stats
from .exporters import export_po, import_po, export_json
from .translator import auto_translate, check_cache_coverage
from .import_nut import parse_nut_file, import_translations


@click.group()
def cli():
    """Rosetta DB - Versioned translation database for Battle Brothers."""
    pass


@cli.command()
@click.argument('source_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--version', '-v', required=True, help='Game version (e.g., 1.5.1.7)')
@click.option('--verbose', '-V', is_flag=True, help='Show detailed progress')
def extract(source_dir: Path, version: str, verbose: bool):
    """Extract strings from .nut files to database."""
    click.echo(f"Extracting from {source_dir} (version {version})...")

    with Database() as db:
        prev_version = db.get_latest_version()
        stats = extract_to_database(source_dir, version, db, verbose=verbose)

    click.echo(f"\nExtraction complete:")
    click.echo(f"  Added:     {stats['added']}")
    click.echo(f"  Modified:  {stats['modified']}")
    click.echo(f"  Unchanged: {stats['unchanged']}")
    click.echo(f"  Removed:   {stats['removed']}")
    if stats['errors']:
        click.echo(f"  Errors:    {stats['errors']}", err=True)

    if prev_version:
        click.echo(f"\nPrevious version: {prev_version}")


@cli.command()
@click.argument('from_version')
@click.argument('to_version')
@click.option('--verbose', '-V', is_flag=True, help='Show detailed changes')
def diff(from_version: str, to_version: str, verbose: bool):
    """Show differences between two versions."""
    with Database() as db:
        changes = diff_versions(db, from_version, to_version)
        print_diff(changes, verbose=verbose)


@cli.command()
def status():
    """Show database status and versions."""
    with Database() as db:
        versions = db.get_versions()
        total = db.count_strings()

        click.echo(f"Database: {db.db_path}")
        click.echo(f"Total active strings: {total}")
        click.echo(f"\nVersions extracted:")

        if versions:
            for v in versions:
                click.echo(f"  {v['version']}: {v['total_strings']} strings ({v['extracted_at']})")
        else:
            click.echo("  (none)")


@cli.command()
@click.argument('version')
@click.argument('lang')
def stats(version: str, lang: str):
    """Show translation statistics for a version/language."""
    with Database() as db:
        strings = db.get_strings_for_compile(version, lang)
        total = len(strings)
        translated = sum(1 for s in strings if s['translated_text'])
        pending = sum(1 for s in strings if s['translation_status'] == 'pending')
        reviewed = sum(1 for s in strings if s['translation_status'] == 'reviewed')

        click.echo(f"Version: {version}, Language: {lang}")
        click.echo(f"  Total strings:  {total}")
        click.echo(f"  Translated:     {translated} ({100*translated//total if total else 0}%)")
        click.echo(f"  Untranslated:   {total - translated}")
        click.echo(f"  Pending review: {pending}")
        click.echo(f"  Reviewed:       {reviewed}")


@cli.command()
@click.argument('version')
@click.argument('lang')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file path')
@click.option('--author', '-a', default='community', help='Author name for metadata')
@click.option('--stdout', is_flag=True, help='Print to stdout instead of file')
def compile(version: str, lang: str, output: Optional[Path], author: str, stdout: bool):
    """Compile translations to pack_<lang>.nut file."""
    with Database() as db:
        # Check stats first
        s = compile_stats(db, version, lang)

        if s['translated'] == 0:
            click.echo(f"No translations found for {lang} in version {version}", err=True)
            return

        # Default output path
        if not output and not stdout:
            output = Path(f"rosetta/pack_{lang}_compiled.nut")

        # Compile
        content = compile_translation(db, version, lang, output if not stdout else None, author)

        if stdout:
            click.echo(content)
        else:
            click.echo(f"Compiled {s['translated']}/{s['total']} strings ({s['coverage']}%)")
            click.echo(f"Output: {output}")


@cli.command('export')
@click.argument('version')
@click.argument('lang')
@click.option('--format', '-f', 'fmt', type=click.Choice(['po', 'json']), default='po',
              help='Export format (default: po)')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file path')
@click.option('--all', 'include_all', is_flag=True, help='Include already translated strings')
@click.option('--stdout', is_flag=True, help='Print to stdout')
def export_cmd(version: str, lang: str, fmt: str, output: Optional[Path],
               include_all: bool, stdout: bool):
    """Export strings to PO/JSON for translation platforms."""
    with Database() as db:
        # Default output path
        if not output and not stdout:
            output = Path(f"translations_{lang}_{version}.{fmt}")

        if fmt == 'po':
            content = export_po(db, version, lang, output if not stdout else None,
                               include_translated=include_all)
        else:
            content = export_json(db, version, lang, output if not stdout else None)

        if stdout:
            click.echo(content)
        else:
            # Count entries
            count = db.count_strings(version)
            click.echo(f"Exported {count} strings to {output}")
            click.echo(f"Format: {fmt.upper()} (for {'Weblate' if fmt == 'po' else 'Crowdin'})")


@cli.command('import')
@click.argument('po_file', type=click.Path(exists=True, path_type=Path))
@click.argument('lang')
@click.option('--status', '-s', type=click.Choice(['pending', 'auto', 'reviewed']),
              default='reviewed', help='Translation status to set')
def import_cmd(po_file: Path, lang: str, status: str):
    """Import translations from PO file."""
    with Database() as db:
        stats = import_po(db, po_file, lang, status)

        click.echo(f"Import complete:")
        click.echo(f"  Imported:  {stats['imported']}")
        click.echo(f"  Skipped:   {stats['skipped']} (empty translations)")
        click.echo(f"  Not found: {stats['not_found']} (strings not in database)")


@cli.command('auto-translate')
@click.argument('version')
@click.argument('lang')
@click.option('--engine', '-e', type=click.Choice(['claude35', 'yt']), default='claude35',
              help='Translation engine (default: claude35)')
@click.option('--batch-size', '-b', type=int, default=50,
              help='Strings per API call (default: 50)')
@click.option('--status', '-s', type=click.Choice(['pending', 'auto', 'reviewed']),
              default='auto', help='Translation status to set (default: auto)')
@click.option('--dry-run', is_flag=True, help='Show what would be translated without calling API')
@click.option('--verbose', '-V', is_flag=True, help='Show detailed progress')
def auto_translate_cmd(version: str, lang: str, engine: str, batch_size: int,
                       status: str, dry_run: bool, verbose: bool):
    """Auto-translate untranslated strings using Claude/Yandex."""
    with Database() as db:
        if dry_run:
            # Check cache coverage without translating
            stats = check_cache_coverage(db, lang, version, engine)
            click.echo(f"Dry run for version {version}, language {lang}:")
            click.echo(f"  Total untranslated: {stats['total']}")
            click.echo(f"  Already cached:     {stats['cached']}")
            click.echo(f"  Would call API for: {stats['uncached']}")
            return

        # Get count before translation
        untranslated_count = len(db.get_untranslated(lang, version))

        if untranslated_count == 0:
            click.echo(f"No untranslated strings for {lang} in version {version}")
            return

        click.echo(f"Translating {untranslated_count} strings with {engine}...")

        stats = auto_translate(
            db, lang, version,
            engine=engine,
            batch_size=batch_size,
            status=status,
            verbose=verbose
        )

        click.echo(f"\nTranslation complete:")
        click.echo(f"  Translated: {stats['translated']}")
        click.echo(f"  Skipped:    {stats['skipped']} (empty results)")
        if stats['errors']:
            click.echo(f"  Errors:     {stats['errors']}", err=True)


@cli.command('import-nut')
@click.argument('nut_file', type=click.Path(exists=True, path_type=Path))
@click.argument('lang')
@click.option('--status', '-s', type=click.Choice(['pending', 'auto', 'reviewed']),
              default='reviewed', help='Translation status to set')
@click.option('--verbose', '-V', is_flag=True, help='Show detailed progress')
def import_nut_cmd(nut_file: Path, lang: str, status: str, verbose: bool):
    """Import translations from .nut file (e.g., base_es.nut)."""
    click.echo(f"Parsing {nut_file}...")
    pairs = parse_nut_file(nut_file)
    click.echo(f"Found {len(pairs)} translation pairs")

    click.echo(f"\nImporting to database (lang={lang})...")
    with Database() as db:
        stats = import_translations(db, pairs, lang, status=status, verbose=verbose)

    click.echo(f"\nImport complete:")
    click.echo(f"  Imported:       {stats['imported']}")
    click.echo(f"  Already exists: {stats['already_exists']}")
    click.echo(f"  Not found in DB: {stats['not_found']}")
    click.echo(f"  Skipped:        {stats['skipped']}")


@cli.command('missing')
@click.argument('version')
@click.argument('lang')
@click.option('--limit', '-n', type=int, default=20, help='Number of strings to show')
@click.option('--file', '-f', 'file_filter', help='Filter by file path pattern')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output to file')
def missing_cmd(version: str, lang: str, limit: int, file_filter: Optional[str],
                output: Optional[Path]):
    """Show untranslated strings."""
    with Database() as db:
        untranslated = db.get_untranslated(lang, version)

        if file_filter:
            untranslated = [s for s in untranslated if file_filter.lower() in s['file_path'].lower()]

        total = len(untranslated)
        click.echo(f"Untranslated strings for {lang} in version {version}: {total}")

        if output:
            # Write all to file
            with open(output, 'w', encoding='utf-8') as f:
                for s in untranslated:
                    f.write(f"// {s['file_path']}::{s['context']}\n")
                    f.write(f"EN: {s['en_text']}\n")
                    f.write(f"{lang.upper()}: \n\n")
            click.echo(f"Written to {output}")
        else:
            # Show limited output
            shown = untranslated[:limit]
            click.echo("")
            for s in shown:
                click.echo(f"[{s['file_path']}::{s['context']}]")
                en_preview = s['en_text'][:100] + '...' if len(s['en_text']) > 100 else s['en_text']
                click.echo(f"  EN: {en_preview}")
                click.echo("")

            if total > limit:
                click.echo(f"... and {total - limit} more. Use --limit or --output to see all.")


@cli.command('review')
@click.argument('version')
@click.argument('lang')
@click.option('--status', '-s', type=click.Choice(['all', 'pending', 'auto', 'reviewed']),
              default='all', help='Filter by translation status')
@click.option('--file', '-f', 'file_filter', help='Filter by file path pattern')
@click.option('--limit', '-n', type=int, default=20, help='Number of strings to show')
def review_cmd(version: str, lang: str, status: str, file_filter: Optional[str], limit: int):
    """Review existing translations."""
    with Database() as db:
        strings = db.get_strings_for_compile(version, lang)

        # Filter by status
        if status != 'all':
            strings = [s for s in strings if s.get('translation_status') == status]

        # Filter only translated
        strings = [s for s in strings if s.get('translated_text')]

        # Filter by file
        if file_filter:
            strings = [s for s in strings if file_filter.lower() in s['file_path'].lower()]

        total = len(strings)
        click.echo(f"Translations for {lang} in version {version}: {total}")
        click.echo("")

        shown = strings[:limit]
        for s in shown:
            click.echo(f"[{s['file_path']}::{s['context']}]")
            en_preview = s['en_text'][:80] + '...' if len(s['en_text']) > 80 else s['en_text']
            tr_preview = s['translated_text'][:80] + '...' if len(s['translated_text']) > 80 else s['translated_text']
            click.echo(f"  EN: {en_preview}")
            click.echo(f"  {lang.upper()}: {tr_preview}")
            click.echo(f"  Status: {s.get('translation_status', 'unknown')}")
            click.echo("")

        if total > limit:
            click.echo(f"... and {total - limit} more. Use --limit to see more.")


@cli.command('serve')
@click.option('--port', '-p', type=int, default=8000, help='Port to run on')
@click.option('--version', '-v', 'game_version', help='Game version to show')
@click.option('--lang', '-l', default='es', help='Language to show')
def serve_cmd(port: int, game_version: Optional[str], lang: str):
    """Start a simple web UI for reviewing translations."""
    try:
        from .web_ui import create_app
    except ImportError:
        click.echo("Web UI requires flask. Install with: uv pip install flask")
        return

    with Database() as db:
        if not game_version:
            game_version = db.get_latest_version()

    if not game_version:
        click.echo("No game version found. Run 'extract' first.")
        return

    click.echo(f"Starting web UI at http://localhost:{port}")
    click.echo(f"Version: {game_version}, Language: {lang}")
    click.echo("Press Ctrl+C to stop")

    app = create_app(game_version, lang)
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    cli()
