# Rosetta Translations Framework

A framework for translating Battle Brothers mods and game files to various languages.

**Two approaches available:**

1. **Runtime Rosetta** - Intercepts strings at runtime (original approach)
2. **Rosetta DB** - Versioned database with CLI tools for batch extraction and compilation (new)

<!-- MarkdownTOC autolink="true" levels="1,2,3" autoanchor="false" -->

- [Quick Start](#quick-start)
- [Rosetta DB - Versioned Translation Database](#rosetta-db---versioned-translation-database)
    - [Installation](#installation)
    - [Workflow Overview](#workflow-overview)
    - [CLI Commands](#cli-commands)
        - [extract](#extract---extract-strings-from-nut-files)
        - [status](#status---show-database-status)
        - [diff](#diff---compare-versions)
        - [stats](#stats---translation-statistics)
        - [compile](#compile---generate-translation-file)
        - [auto-translate](#auto-translate---auto-translate-using-ai)
        - [export](#export---export-to-pojson-for-translation-platforms)
        - [import](#import---import-translations-from-po-file)
    - [Database Structure](#database-structure)
- [Runtime Rosetta](#runtime-rosetta)
    - [Using Translations](#using-translations)
    - [Writing Translations](#writing-translations)
    - [Translation Mod Structure](#translation-mod-structure)
    - [Legacy Extractor](#legacy-extractor)
- [Translation Format Reference](#translation-format-reference)
- [For Mod Authors](#for-mod-authors)
- [Compatibility](#compatibility)
- [Limitations](#limitations)
- [Feedback](#feedback)

<!-- /MarkdownTOC -->


# Quick Start

**For translating game files (base game + DLCs):**

```bash
# 1. Decrypt game .cnut files to .nut (requires external tool like nutcracker)
nutcracker decrypt game_cnut/ game_nut/

# 2. Extract strings to database
python -m rosetta_db extract game_nut/ --version 1.5.1.7

# 3. Check status
python -m rosetta_db status

# 4. Auto-translate (requires API keys in .env)
python -m rosetta_db auto-translate 1.5.1.7 ru --engine claude35

# 5. Compile to .nut file
python -m rosetta_db compile 1.5.1.7 ru -o rosetta/pack_ru.nut
```

**For translating mods (legacy approach):**

```bash
python rosetta.py -lru path/to/mod/ > mod_translation_ru.nut
```


# Rosetta DB - Versioned Translation Database

A database-backed system for managing translations across game versions. Features:

- **Version tracking** - Detects added/modified/removed strings between versions
- **Batch processing** - Extract thousands of strings from directory hierarchies
- **Translation status** - Track pending/auto/reviewed translations
- **Auto-translation** - Claude 3.5 Sonnet, Yandex Translate (with caching)
- **Platform integration** - Export to PO/JSON for Weblate/Crowdin


## Installation

Requirements: Python 3.12+

```bash
# Install dependencies
pip install -r requirements.txt

# Or manually:
pip install click polib requests

# For auto-translation, set up API keys:
cp .env.sample .env
# Edit .env with your ANTHROPIC_TOKEN and/or YANDEX credentials
```


## Workflow Overview

```
[Encrypted .cnut files]
         │
         ▼ (external decrypt tool)
[Decrypted .nut files]
         │
         ▼ python -m rosetta_db extract
[SQLite Database: translations.db]
         │
         ├──▶ python -m rosetta_db auto-translate
         │              │
         │              ▼
         │    [Translations in DB]
         │
         ▼ python -m rosetta_db compile
[pack_<lang>.nut file]
         │
         ▼ (zip packaging)
[Distributable mod]
```


## CLI Commands

### extract - Extract strings from .nut files

```bash
python -m rosetta_db extract <directory> --version <version> [-V]

# Examples:
python -m rosetta_db extract game_decrypted/ --version 1.5.1.7
python -m rosetta_db extract game_decrypted/ --version 1.5.1.7 -V  # verbose

# Options:
#   -v, --version  Game version identifier (required)
#   -V, --verbose  Show detailed progress
```

Recursively processes all `.nut` files in the directory hierarchy. Automatically skips rosetta/test/mock files.

**Output:**
```
Extracting from game_decrypted (version 1.5.1.7)...
[1/247] scripts/skills/actives/possess_undead.nut
[2/247] scripts/items/weapons/sword.nut
...

Extraction complete:
  Added:     3847
  Modified:  0
  Unchanged: 0
  Removed:   0
```


### status - Show database status

```bash
python -m rosetta_db status

# Output:
Database: C:\path\to\translations.db
Total active strings: 3847

Versions extracted:
  1.5.1.7: 3847 strings (2024-01-15 10:30:00)
  1.5.1.6: 3820 strings (2024-01-10 14:20:00)
```


### diff - Compare versions

```bash
python -m rosetta_db diff <from_version> <to_version> [-V]

# Example:
python -m rosetta_db diff 1.5.1.6 1.5.1.7 -V

# Output:
Added: 27 strings
Modified: 5 strings
Removed: 0 strings

--- Added ---
  scripts/skills/new_skill.nut::create.m.Description
    EN: A powerful new ability...
  ...
```


### stats - Translation statistics

```bash
python -m rosetta_db stats <version> <lang>

# Example:
python -m rosetta_db stats 1.5.1.7 ru

# Output:
Version: 1.5.1.7, Language: ru
  Total strings:  3847
  Translated:     3200 (83%)
  Untranslated:   647
  Pending review: 50
  Reviewed:       3150
```


### compile - Generate translation file

```bash
python -m rosetta_db compile <version> <lang> [-o output] [--stdout]

# Examples:
python -m rosetta_db compile 1.5.1.7 ru                    # writes to rosetta/pack_ru_compiled.nut
python -m rosetta_db compile 1.5.1.7 ru -o my_pack.nut     # custom output path
python -m rosetta_db compile 1.5.1.7 ru --stdout           # print to console

# Options:
#   -o, --output   Output file path
#   -a, --author   Author name for metadata (default: "community")
#   --stdout       Print to stdout instead of file
```

**Generated format:**
```squirrel
// Generated by rosetta_db compiler
// Version: 1.5.1.7, Language: ru
// Total pairs: 3200

local def = ::Rosetta;
local rosetta = {
    mod = {id = def.ID, version = def.Version}
    author = "community"
    lang = "ru"
}
local pairs = [
    // scripts/skills/actives/skill.nut::create.m.Name
    {
        en = "Powerful Strike"
        ru = "Мощный удар"
    }
    // scripts/skills/actives/skill.nut::create.m.Description
    {
        mode = "pattern"
        en = "Deals <damage:int> damage"
        ru = "Наносит <damage> урона"
    }
    ...
]
def.add(rosetta, pairs);
```


### auto-translate - Auto-translate using AI

```bash
python -m rosetta_db auto-translate <version> <lang> [OPTIONS]

# Examples:
python -m rosetta_db auto-translate 1.5.1.7 ru                    # use Claude 3.5 (default)
python -m rosetta_db auto-translate 1.5.1.7 ru --engine yt        # use Yandex Translate
python -m rosetta_db auto-translate 1.5.1.7 ru --dry-run          # check without API calls
python -m rosetta_db auto-translate 1.5.1.7 ru -V                 # verbose progress

# Options:
#   -e, --engine [claude35|yt]   Translation engine (default: claude35)
#   -b, --batch-size INTEGER     Strings per API call (default: 50)
#   -s, --status [pending|auto|reviewed]
#                                Translation status to set (default: auto)
#   --dry-run                    Show what would be translated without calling API
#   -V, --verbose                Show detailed progress
```

**Dry run example:**
```
Dry run for version 1.5.1.7, language ru:
  Total untranslated: 647
  Already cached:     203
  Would call API for: 444
```

**Translation output:**
```
Translating 647 strings with claude35...
Translating batch 1/13 (50 strings)...
Translating batch 2/13 (50 strings)...
...

Translation complete:
  Translated: 647
  Skipped:    0 (empty results)
```

Translations are cached in the database - re-running won't call APIs for already-translated strings.


### export - Export to PO/JSON for translation platforms

```bash
python -m rosetta_db export <version> <lang> [OPTIONS]

# Examples:
python -m rosetta_db export 1.5.1.7 ru                           # PO format (default)
python -m rosetta_db export 1.5.1.7 ru -f json                   # JSON format
python -m rosetta_db export 1.5.1.7 ru -o translations.po        # custom output
python -m rosetta_db export 1.5.1.7 ru --all                     # include already translated
python -m rosetta_db export 1.5.1.7 ru --stdout                  # print to console

# Options:
#   -f, --format [po|json]  Export format (default: po)
#   -o, --output PATH       Output file path
#   --all                   Include already translated strings
#   --stdout                Print to stdout
```

**PO format (for Weblate):**
```
msgctxt "scripts/skills/skill.nut::create.m.Name"
msgid "Powerful Strike"
msgstr ""

msgctxt "scripts/skills/skill.nut::create.m.Description"
msgid "Deals {damage} damage"
msgstr ""
```

Pattern placeholders are converted: `<damage:int>` → `{damage}` for translator-friendly display.


### import - Import translations from PO file

```bash
python -m rosetta_db import <po_file> <lang> [OPTIONS]

# Examples:
python -m rosetta_db import translations_ru.po ru
python -m rosetta_db import translations_ru.po ru --status reviewed

# Options:
#   -s, --status [pending|auto|reviewed]
#                          Translation status to set (default: reviewed)
```

**Output:**
```
Import complete:
  Imported:  500
  Skipped:   10 (empty translations)
  Not found: 5 (strings not in database)
```

Placeholders are automatically converted back: `{damage}` → `<damage:int>`.


## Database Structure

All data is stored in `translations.db` (SQLite). Tables:

| Table | Purpose |
|-------|---------|
| `strings` | Extracted strings with file path, context, version tracking |
| `translations` | Translations per language with status (pending/auto/reviewed) |
| `version_changes` | Change history between versions |
| `game_versions` | Metadata for each extracted version |
| `translations_cache_ru` | Cache for translation API calls (from xt.py) |


# Runtime Rosetta

The original approach - intercepts strings at runtime in the game.


## Using Translations

For translation to work you need:

1. A translation of the game installed for your language
2. The mod and its dependencies installed
3. Rosetta and its dependencies installed
4. Translation of the mod installed

When a **new version of a mod** is released you can update it right away. Old translation will mostly work, only new and changed strings will go untranslated.


## Writing Translations

A Rosetta-based translation is a squirrel script registering (english, target language) pairs:

```squirrel
// Skip if Rosetta is not installed
if (!("Rosetta" in getroottable())) return;

local rosetta = {
    mod = {id = "mod_necro", version = "0.4.0"}
    author = "hackflow"
    lang = "ru"
}
local pairs = [
    // Literal pair
    {
        en = "Proper Necro"
        ru = "Годный Некромант"
    }
    // Pattern with captures
    {
        mode = "pattern"
        en = "<actor:str_tag> heals for <hp:int> points"
        ru = "<actor> восстанавливает <hp> ОЗ"
    }
    // Pluralization
    {
        plural = "range"
        en = "Has a range of <range:int_tag> tiles"
        n1 = "Имеет дальность в <range> клетку"
        n2 = "Имеет дальность в <range> клетки"
        n5 = "Имеет дальность в <range> клеток"
    }
]
::Rosetta.add(rosetta, pairs);
```


## Translation Mod Structure

### Single-File (small mods)

```
scripts/
    !mods_preload/
        mod_hunter_es.nut
```

### Multi-File (larger mods)

```
mod_hunter_es/
    config.nut
    events.nut
    skills.nut
scripts/
    !mods_preload/
        mod_hunter_es.nut
```


## Legacy Extractor

For extracting strings from mods without using the database:

```bash
python rosetta.py [options] <mod-dir> > <output-file>

# Options:
#   -l<lang>    Target language (default: ru)
#   -t<engine>  Auto-translate: yt (Yandex), claude35 (Claude)
#   -v          Verbose output

# Examples:
python rosetta.py -lru mod_necro/ > necro_ru.nut
python rosetta.py -lru -tclaude35 mod_necro/ > necro_ru.nut
```


# Translation Format Reference

## Literal Pairs

```squirrel
{en = "Hello", ru = "Привет"}
```

## Pattern Pairs

Capture dynamic values:

```squirrel
{
    mode = "pattern"
    en = "<actor:str_tag> deals <damage:int> damage"
    ru = "<actor> наносит <damage> урона"
}
```

**Capture types:**
- `int` - Integer number
- `val` - Number with optional % sign
- `str` - Any string (non-greedy)
- `tag` - BBCode tag like `[color=...]`
- `str_tag` - String wrapped in tags
- `int_tag` - Integer wrapped in tags
- `val_tag` - Value wrapped in tags

## Plural Pairs

Language-dependent pluralization:

```squirrel
{
    plural = "count"
    en = "<count:int> items"
    n1 = "<count> предмет"    // 1, 21, 31...
    n2 = "<count> предмета"   // 2-4, 22-24...
    n5 = "<count> предметов"  // 5-20, 25-30...
}
```

## ID-based Pairs

For very long strings:

```squirrel
{
    id = "scripts/scenarios/world/necro_scenario.Description"
    ru = "[p=c][img]gfx/ui/events/event_76.png[/img][/p][p]После многих лет..."
}
```


# For Mod Authors

Rosetta works on top of unmodified mods. For special cases, you can add translation points:

```squirrel
local _ = "Rosetta" in getroottable() ? Rosetta.translate.bindenv(Rosetta) : @(s) s;

_("Some string");
_("Thing does " + num + " things");
```


# Compatibility

Should be compatible with everything. Safe to add, update or remove mid-game.


# Limitations

- Language registration is global (contact maintainer to add new languages)
- No UI for switching languages (use `::Rosetta.activate(<code>)`)
- Only strings from .nut files can be intercepted (not JS)
- Same string is translated the same everywhere (except with id matching)


# Feedback

Suggestions, bug reports, and feedback welcome:
- GitHub Issues: [battle-brothers-rosetta](https://github.com/Suor/battle-brothers-rosetta)
- BB Modding Discord: **suor.hackflow**


[nexus-mods]: https://www.nexusmods.com/battlebrothers/mods/802
[ModernHooks]: https://www.nexusmods.com/battlebrothers/mods/685
[stdlib]: https://www.nexusmods.com/battlebrothers/mods/676
