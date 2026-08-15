# Battle Brothers Rosetta - Versioned Translation Database

## Project Overview

Fork of [Battle Brothers Rosetta](https://github.com/Suor/battle-brothers-mods) extending the extraction system with versioned database architecture and collaborative translation UI. Maintains backward compatibility with legacy runtime-hook approach while enabling structured, incremental translation workflows.

**Architecture Principle: REUSE OVER REWRITE**

This project wraps existing, proven components rather than reimplementing them. Estimated new code: ~400 lines (database layer + CLI wrapper). Everything else reuses `rosetta.py`, `xt.py`, and existing build tools.

## Key Files Reference

| File | Purpose |
|------|---------|
| `rosetta.py` | Parser with `extract(code)` function (~55 tests) |
| `xt.py` | Translation engines (Claude, Yandex) with SQLite cache |
| `scripts/!mods_preload/!rosetta.nut` | Main `::Rosetta` definition and `add()` API |
| `rosetta/hooks.nut` | Runtime hooks for tooltips, perks, etc. |
| `rosetta/pack_ru.nut` | Example translation pack format |
| `translations.db` | Existing translation cache (will be extended) |
| `Makefile` | Syntax check + zip packaging (no encryption needed) |

## Problem Statement

### Current Limitations

**Battle Brothers modding constraints:**
- Game version-dependent: `.cnut` files must match exact game version (1.5.1.7 → 1.5.1.8 breaks mods)
- Manual update workflow: translators use visual diff tools (Meld) to identify changed strings
- No collaboration infrastructure: monolithic `.nut` files prevent parallel translation
- Update bottleneck: mod updates require full re-translation cycle

**Existing Rosetta approach:**
- Runtime interception works but doesn't solve version management
- `rosetta.py` extractor generates flat files without version tracking
- Update process: re-extract → manual diff → merge → re-translate
- Single-translator workflow only

### Core Technical Challenge

**String extraction from Squirrel (.nut) files:**
- Simple literals: `"Hello"` ✓
- Concatenations: `"Hello, " + name + "!"` → `"Hello, <name>!"`
- Dynamic construction: `Text.positive(val) + " damage"` → `"<Text.positive(val)> damage"`
- Ternaries: `cond ? "First" : "Second"` → both variants
- Format strings: `format("Has %s items", count)` → `"Has <count> items"`

Existing `rosetta.py` parser (see `test_rosetta.py`) already handles these cases. Need to preserve this capability while restructuring output.

## Architecture Principles: Reuse Over Rewrite

### What Already Exists (DO NOT REIMPLEMENT)

| Component | Location | Functionality | Status |
|-----------|----------|---------------|--------|
| **Parser** | `rosetta.py::extract()` | Squirrel AST parsing, pattern detection, context tracking | ✅ Tested (~55 test cases) |
| **Translation engines** | `xt.py` | Claude API, Yandex API, SQLite caching | ✅ Working with cache |
| **Runtime hooks** | `scripts/!mods_preload/!rosetta.nut` | `::Rosetta` definition, `add()` API, language detection | ✅ Stable API |
| **Translation hooks** | `rosetta/hooks.nut` | String interception, tooltip/perk translation | ✅ Stable |
| **Build pipeline** | `Makefile` | Syntax check (`squirrel -c`), zip packaging | ✅ No encryption needed |
| **Output format** | `rosetta/pack_ru.nut` | Reference `::Rosetta.add(metadata, pairs)` format | ✅ Working example |

### What's Actually New (IMPLEMENT THESE)

| Component | Purpose | Estimated LOC |
|-----------|---------|---------------|
| **Database schema** | Extend `translations.db` with version tracking | ~50 |
| **DB wrapper** | CRUD operations, diff queries | ~100 |
| **CLI commands** | `extract`, `diff`, `compile`, `auto-translate` | ~130 |
| **Platform export** | Weblate/Crowdin PO/JSON converters | ~50 |

**Total new code: ~330 lines** (vs. 2000+ if reimplementing parser/translation)

### Reuse Architecture Diagram

```
┌─────────────────────────────────────────────┐
│  EXISTING: rosetta.py                       │
│  extract(code) → [{en, context, mode}]      │  ✅ ~55 tests passing
└──────────────┬──────────────────────────────┘
               │ Called by ↓
┌──────────────▼──────────────────────────────┐
│  NEW: rosetta_db/extractor.py               │
│  extract_to_db(files, version):             │  ~50 LOC
│    for pair in extract(code):               │
│      db.upsert(hash(pair), pair, version)   │
└──────────────┬──────────────────────────────┘
               │ Writes to ↓
┌──────────────▼──────────────────────────────┐
│  EXTENDED: translations.db                  │
│  • EXISTING: translations_cache_ru (xt.py)  │
│  • NEW: strings, translations, versions     │  ~150 LOC queries
│  • Change detection (diff between versions) │
└──────────────┬──────────────────────────────┘
               │ Reads from ↓
┌──────────────▼──────────────────────────────┐
│  EXISTING: xt.py                            │
│  translate(engine, texts) → translations    │  ✅ Working + cache
└──────────────┬──────────────────────────────┘
               │ OR export to ↓
┌──────────────▼──────────────────────────────┐
│  OPTIONAL: Translation Platforms            │
│  • Weblate (PO/XLIFF export)                │  ~50 LOC converters
│  • Crowdin (JSON export)                    │
│  • POEditor (CSV export)                    │
└──────────────┬──────────────────────────────┘
               │ Import back ↓
┌──────────────▼──────────────────────────────┐
│  NEW: rosetta_db/compiler.py                │
│  compile_mod(version, lang):                │  ~30 LOC
│    pairs = db.get_strings(version, lang)    │
│    nut = generate pack_<lang>.nut           │  Format from pack_ru.nut
└──────────────┬──────────────────────────────┘
               │ Calls ↓
┌──────────────▼──────────────────────────────┐
│  EXISTING: Makefile                         │
│  check-compile (squirrel -c)                │  ✅ Syntax validation
│  zip (directory → .zip)                     │  ✅ No encryption needed
└─────────────────────────────────────────────┘
```

### Integration with Translation Platforms

Modern translation platforms (Weblate, Crowdin, POEditor) solve collaboration, review workflows, and translation memory. Instead of building custom UI, **integrate with existing platforms**.

#### Platform Compatibility Matrix

| Platform | Format | Features | Integration Approach |
|----------|--------|----------|---------------------|
| **Weblate** | PO, XLIFF, JSON | OSS, self-hosted, Git integration, context, glossary | Export DB → PO/XLIFF, import translations |
| **Crowdin** | JSON, XLIFF, CSV | Cloud, API, screenshots, TM, plurals | Export DB → JSON, sync via API |
| **POEditor** | JSON, CSV, PO | Cloud, API, simple, collaborative | Export DB → JSON/CSV, API sync |
| **Lokalise** | JSON, XLIFF | Cloud, API, advanced features | Export DB → JSON |

**Recommended: Weblate** (self-hosted, free, game localization friendly)

#### Export/Import Flow

```bash
# 1. Extract to database (as before)
rosetta extract decrypted_1.5.1.7/ --version 1.5.1.7

# 2. Export to Weblate-compatible format
rosetta export --format po --lang ru --output translations_ru.po

# Weblate PO format:
# msgctxt "scripts/skills/possess_undead_skill.nut::create.m.Description"
# msgid "Possess an undead minion"
# msgstr ""

# 3. Translate in Weblate (web UI, collaborative, with context)

# 4. Import completed translations
rosetta import --format po --lang ru translations_ru.po

# 5. Compile mod (as before)
rosetta compile --lang ru --version 1.5.1.7 --output mods/
```

#### Format Converters (minimal implementation)

```python
# rosetta_db/exporters.py (~50 lines total)

def export_to_po(db: Database, lang: str, version: str) -> str:
    """Generate Gettext PO file for Weblate"""
    strings = db.get_strings(version, status='active')
    po_entries = []
    
    for s in strings:
        # msgctxt = file::context for disambiguation
        msgctxt = f"{s.file_path}::{s.context}"
        msgid = s.en_text
        msgstr = db.get_translation(s.id, lang) or ""
        
        po_entries.append(f"""
msgctxt "{msgctxt}"
msgid "{escape_po(msgid)}"
msgstr "{escape_po(msgstr)}"
""")
    
    return f"""# Battle Brothers Translation
# Language: {lang}
# Version: {version}
{"".join(po_entries)}
"""

def import_from_po(db: Database, po_file: str, lang: str):
    """Import translations from PO file"""
    import polib  # Standard library
    po = polib.pofile(po_file)
    
    for entry in po:
        # Extract file::context from msgctxt
        file_path, context = entry.msgctxt.split('::', 1)
        en_text = entry.msgid
        translated = entry.msgstr
        
        # Find string by file + context + en_text
        string_id = db.find_string(file_path, context, en_text)
        if string_id and translated:
            db.save_translation(string_id, lang, translated, status='reviewed')

# Similar for export_to_json() for Crowdin/POEditor
# Similar for export_to_xliff() for advanced platforms
```

## Proposed Solution

### Simplified Architecture (Reuse-First)

**Philosophy: Database layer between existing parser and existing compiler**

```
[Game .nut files]
    ↓
[EXISTING: rosetta.py extract()] ← Reuse ~55 tested cases
    ↓
[EXTENDED: translations.db] ← Add tables to existing database
    ↓
[EXISTING: xt.py translate()] OR [Export to Weblate/Crowdin] ← Reuse or integrate
    ↓
[NEW: Compiler] ← Generate pack_<lang>.nut (~30 LOC)
    ↓
[EXISTING: Makefile check-compile + zip] ← No encryption needed
    ↓
[.zip mod ready to install]
```

### Database Schema

**Strategy: Extend existing `translations.db`** with new tables. The existing `translations_cache_ru` table is kept for `xt.py` engine caching; new tables handle version tracking and structured translations.

```sql
-- EXISTING (from xt.py) - DO NOT MODIFY
-- translations_cache_ru (engine, conf, input, output)
-- cache (ckey, cval, expires)

-- NEW: Core strings table
CREATE TABLE strings (
    id TEXT PRIMARY KEY,  -- SHA256(file_path || context || en_text)
    file_path TEXT NOT NULL,
    context TEXT NOT NULL,  -- e.g., "create.m.Description"
    en_text TEXT NOT NULL,
    mode TEXT DEFAULT 'literal',  -- literal|pattern|plural
    pattern_data TEXT,  -- JSON for mode=pattern: captured placeholders

    first_seen_version TEXT NOT NULL,
    last_seen_version TEXT,
    status TEXT DEFAULT 'active',  -- active|modified|removed

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NEW: Translations with status tracking
CREATE TABLE translations (
    string_id TEXT NOT NULL,
    lang TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    translation_status TEXT DEFAULT 'pending',  -- pending|auto|reviewed|approved
    translator TEXT,
    auto_engine TEXT,  -- claude35|yt|null

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (string_id, lang),
    FOREIGN KEY (string_id) REFERENCES strings(id)
);

-- NEW: Version tracking
CREATE TABLE version_changes (
    string_id TEXT NOT NULL,
    from_version TEXT,
    to_version TEXT NOT NULL,
    change_type TEXT NOT NULL,  -- added|modified|removed
    diff_context TEXT,  -- What changed in the surrounding code

    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (string_id) REFERENCES strings(id)
);

-- NEW: Metadata
CREATE TABLE game_versions (
    version TEXT PRIMARY KEY,
    extracted_at TIMESTAMP,
    total_strings INTEGER,
    notes TEXT
);

-- Integration: When auto-translating, check translations_cache_ru first
-- for cached engine results before calling xt.py APIs
```

### Runtime Components (Preserved)

The database approach **does not replace** runtime hooks. Both coexist:

**Compile-time (new):** Database → .nut generation → .cnut encryption  
**Runtime (existing):** Rosetta hooks intercept and translate strings dynamically

#### Key Files to Preserve

1. **`scripts/!mods_preload/!rosetta.nut`**
   - Core mod initialization
   - Language detection & activation
   - Translation registration API

2. **`rosetta/hooks.nut`**
   - String interception logic
   - Pattern matching engine
   - Plural form selection

These files define the runtime behavior. The compiler generates `.nut` files that **call** these APIs:

```squirrel
// Generated by compiler from database
local pairs = [
    {en = "Barkeep", ru = "Трактирщик"},
    {mode = "pattern", en = "Has <ap:int> AP", ru = "Требует <ap> ОД"}
]

// Calls existing Rosetta runtime
::Rosetta.add(rosetta_meta, pairs);
```

### Key Components

#### 1. Enhanced Extractor (`rosetta_db/extractor.py`) - ~50 LOC

**Wraps existing `rosetta.py::extract()` function:**

```python
from rosetta import extract  # REUSE existing parser

def extract_to_database(nut_files: list[Path], version: str, db: Database):
    """
    Thin wrapper around existing extract() that writes to database.
    
    Args:
        nut_files: Decrypted .nut files from game version
        version: Game version identifier (e.g., "1.5.1.7")
        db: Database connection
    """
    for file_path in nut_files:
        code = file_path.read_text()
        pairs = list(extract(code))  # EXISTING FUNCTION - DO NOT REWRITE
        
        for pair in pairs:
            string_id = compute_id(file_path, pair["_context"], pair["en"])
            
            # Simple upsert logic
            existing = db.get_string(string_id)
            
            if not existing:
                db.insert_string(string_id, file_path, pair, version)
            elif existing.en_text != pair["en"]:
                db.update_string(string_id, pair["en"], version, status="modified")
                db.mark_translations_for_review(string_id)
            else:
                db.touch_string(string_id, version)  # Update last_seen_version
```

**That's it. No parser reimplementation needed.**

#### 2. Version Diff Tool (`rosetta_db/differ.py`) - ~30 LOC

**Simple SQL queries, no complex logic:**

```python
def diff_versions(db: Database, v1: str, v2: str) -> VersionDiff:
    """
    Compare two game versions via SQL queries.
    """
    # Strings added in v2
    added = db.query("""
        SELECT * FROM strings 
        WHERE first_seen_version = ? AND status = 'active'
    """, (v2,))
    
    # Strings modified between v1 and v2
    modified = db.query("""
        SELECT * FROM version_changes 
        WHERE from_version = ? AND to_version = ? AND change_type = 'modified'
    """, (v1, v2))
    
    # Strings removed (present in v1, not in v2)
    removed = db.query("""
        SELECT * FROM strings 
        WHERE last_seen_version = ? AND status != 'active'
    """, (v1,))
    
    return VersionDiff(added=added, modified=modified, removed=removed)
```

#### 3. Translation Compiler (`rosetta_db/compiler.py`) - ~30 LOC

**Generates format expected by `scripts/!mods_preload/!rosetta.nut`:**

```python
def compile_translation(db: Database, lang: str, version: str, output_dir: Path):
    """
    Generate .nut files matching ::Rosetta.add() format.
    No encryption needed - Battle Brothers loads .nut source files directly.
    """
    strings = db.query("""
        SELECT s.*, t.translated_text
        FROM strings s
        LEFT JOIN translations t ON s.id = t.string_id AND t.lang = ?
        WHERE s.last_seen_version = ? AND s.status = 'active'
    """, (lang, version))

    # Generate pairs in exact format ::Rosetta.add() expects
    # (see rosetta/pack_ru.nut for reference)
    pairs = []
    for s in strings:
        pair = {"en": s.en_text, lang: s.translated_text or s.en_text}
        if s.mode == "pattern":
            pair["mode"] = "pattern"
        # ... handle plural (n1, n2, n5 keys), etc.
        pairs.append(pair)

    # Write .nut file in Rosetta format (matches pack_ru.nut structure)
    nut_content = f'''local def = ::Rosetta;
local rosetta = {{
    mod = {{id = def.ID, version = def.Version}}
    author = "community"
    lang = "{lang}"
}}
local pairs = {format_as_squirrel(pairs)}
def.add(rosetta, pairs);
'''

    output_file = output_dir / f"pack_{lang}.nut"
    output_file.write_text(nut_content)

    # Package as .zip (no encryption - game loads .nut directly)
    # subprocess.run(["make", "zip"], cwd=output_dir)
```

**No encryption needed** - Battle Brothers mods are distributed as `.zip` files containing `.nut` source files.

#### 4. Translation Interface - REUSE EXISTING PLATFORMS

**Instead of building custom UI, integrate with proven platforms:**

**Option A: Weblate (Recommended for OSS)**
```bash
# 1. Export to PO format
rosetta export --format po --lang ru > translations_ru.po

# 2. Upload to Weblate instance (web UI or API)
# Translators work in Weblate with:
# - Context display (file::function shown)
# - Translation memory
# - Glossary support
# - Review workflow
# - Git integration

# 3. Download completed translations
rosetta import --format po translations_ru.po
```

**Option B: Crowdin (Cloud, free tier available)**
```bash
# Upload via API
crowdin upload sources --file translations.json

# Download via API
crowdin download --lang ru
rosetta import --format json crowdin_ru.json
```

**Option C: Simple CLI (MVP for solo translators)**
```bash
# Interactive mode (if no platform available)
rosetta translate --lang ru --interactive

# Shows:
# [1/3847] scripts/skills/possess_undead_skill.nut::create.m.Description
# EN: Possess an undead minion
# RU: [auto] Одержать нежить
# Status: [pending] (p=pending, r=reviewed, a=approved, s=skip)
# > r  # Mark as reviewed

# Batch auto-translate remaining
rosetta auto-translate --lang ru --engine claude35 --status pending
```

**No custom web UI needed in Phase 1-4.**

### Workflow Example

#### Initial Setup (v1.5.1.7)

```bash
# 1. Decrypt game files (assume tool exists)
decrypt_game_files game_1.5.1.7/ decrypted_1.5.1.7/

# 2. Extract to database
rosetta extract decrypted_1.5.1.7/ --version 1.5.1.7

# Output: Extracted 3,847 strings from 247 files

# 3. Auto-translate
rosetta auto-translate --lang ru --engine claude35

# Output: Translated 3,847 strings (cached: 1,203, new: 2,644)

# 4. Compile mod
rosetta compile --lang ru --version 1.5.1.7 --output mods/

# Output: Generated mod_bb_ru_1.5.1.7.dat (ready to install)
```

#### Update Workflow (v1.5.1.8 released)

```bash
# 1. Extract new version
rosetta extract decrypted_1.5.1.8/ --version 1.5.1.8

# Output: 
#   Added: 23 strings
#   Modified: 8 strings
#   Removed: 5 strings
#   Unchanged: 3,811 strings

# 2. Review changes
rosetta diff 1.5.1.7 1.5.1.8 --format detailed

# Output shows modified strings with context

# 3. Translate delta only
rosetta auto-translate --lang ru --engine claude35 --status pending

# Output: Translated 31 strings (23 new + 8 modified)

# 4. Compile updated mod
rosetta compile --lang ru --version 1.5.1.8 --output mods/

# Output: Generated mod_bb_ru_1.5.1.8.dat
#   Includes: 3,829 translated strings (3,798 reused + 31 new)
```

## Pre-Implementation Requirements

### 1. Build System (VERIFIED - No Encryption Needed)

**Makefile analysis confirms no encryption:**
```makefile
# Makefile only does syntax check + zip packaging:
check-compile:
    find . -name \*.nut -print0 | xargs -0 -n1 squirrel -c
zip: test
    zip --filesync -r "$${FILENAME}" $(SOURCES)
```

Battle Brothers mods are distributed as `.zip` files containing `.nut` source files directly. **No `.cnut` encryption required.**

### 2. Validate Runtime API Contract (VERIFIED)

**Main API is in `scripts/!mods_preload/!rosetta.nut` (line 46):**

```squirrel
function add(_def, _pairs) {
    // _def = {mod = {id, version}, author, lang}
    // _pairs = array of pair objects
}
```

**Confirmed pair formats (from `rosetta/pack_ru.nut`):**
- Literal pairs: `{en = "...", ru = "..."}`
- Pattern pairs: `{mode = "pattern", en = "<actor:str_tag> heals...", ru = "<actor> лечит..."}`
- Plural pairs: `{plural = "var", en = "...", n1 = "...", n2 = "...", n5 = "..."}`

**Compiler must generate matching format.**

### 3. Test Existing Parser (VERIFIED)

**Run full test suite:**

```bash
pytest test_rosetta.py -v

# ~55 tests covering:
# - Concatenation (test_concat, test_concat_ref, etc.)
# - Ternary expressions (test_ternary_*, test_tricky_ternary)
# - Function calls (test_func, test_func_first, etc.)
# - Context tracking (test_context_*)
# - Edge cases (test_flags, test_brackets, etc.)
```

**If any test fails:** Fix parser before proceeding. Database depends on parser correctness.

### 4. Build Pipeline (VERIFIED)

**Existing workflow is simple:**

```bash
make check-compile  # Syntax check all .nut files
make zip            # Package as mod_rosetta_<version>.zip
make install        # Copy to game data directory
```

**Pipeline for new compiler:**
1. Generate `pack_<lang>.nut` in `rosetta/` directory
2. Run `make check-compile` to validate syntax
3. Run `make zip` to create distributable mod

No additional documentation needed - existing Makefile handles everything.

### 5. API Key Setup

**Copy `.env.sample` → `.env`:**

```bash
cp .env.sample .env

# Fill in:
ANTHROPIC_URL=https://api.anthropic.com/v1/messages
ANTHROPIC_TOKEN=sk-ant-...
YANDEX_OAUTH_TOKEN=...
YANDEX_FOLDER_ID=...
```

**Test translation engines:**

```bash
python xt.py  # Should run example translations
```

## Implementation Phases (Simplified)

### Phase 1: Database Infrastructure (1-2 days)
**Goal:** Extend `translations.db` with version tracking tables

- [ ] Add new tables to existing `translations.db` (strings, translations, version_changes, game_versions)
- [ ] Basic CRUD: `insert_string()`, `get_string()`, `save_translation()`
- [ ] String ID hash function: `compute_id(file, context, en_text)`
- [ ] Version tracking queries
- [ ] Integration with existing `translations_cache_ru` for cache lookups

**Deliverable:** `rosetta_db/database.py` (~150 LOC)

**No parser work - reuse `rosetta.py::extract()`**

### Phase 2: Extractor Wrapper (1 day)
**Goal:** Bridge parser to database

- [ ] Thin wrapper calling `extract()` → database
- [ ] CLI command: `rosetta extract <dir> --version <ver>`
- [ ] Change detection (compare with previous version)

**Deliverable:** `rosetta_db/extractor.py` (~50 LOC)

**Critical:** Run `pytest test_rosetta.py` - all tests must still pass

### Phase 3: Diff & Compiler (1 day)
**Goal:** Version comparison + mod generation

- [ ] `rosetta diff <v1> <v2>` - SQL queries only
- [ ] `rosetta compile` - generate `pack_<lang>.nut` matching `::Rosetta.add()` format
- [ ] Run `make check-compile` to validate generated .nut syntax

**Deliverable:** `rosetta_db/{differ,compiler}.py` (~60 LOC total)

**No encryption needed** - game loads .nut source files directly

### Phase 4: Platform Integration (1-2 days)
**Goal:** Export/import for Weblate/Crowdin

- [ ] PO export: `rosetta export --format po`
- [ ] PO import: `rosetta import --format po`
- [ ] JSON export for Crowdin (optional)
- [ ] CLI translate command (fallback if no platform)

**Deliverable:** `rosetta_db/exporters.py` (~50 LOC)

**No custom UI - integrate with existing platforms**

### Phase 5: Auto-Translation (0.5 days)
**Goal:** Reuse `xt.py` engines

- [ ] Wrapper calling `xt.translate()`
- [ ] CLI: `rosetta auto-translate --engine claude35`
- [ ] Batch processing pending strings
- [ ] Leverage existing `translations_cache_ru` for cache hits

**Deliverable:** Thin wrapper (~20 LOC)

**No API reimplementation - reuse `xt.py` with existing cache**

---

**Total implementation time: ~5-6 days**

**Total new code: ~330 LOC (vs. 2000+ if reimplementing)**

## Technical Decisions

### String ID Generation

Use SHA256 hash of concatenated components:
```python
def compute_string_id(file_path: str, context: str, en_text: str) -> str:
    """
    Generate stable identifier for string across versions.
    
    Hash input: file_path + "|" + context + "|" + en_text
    
    Rationale:
        - file_path: strings from different files are distinct
        - context: same string in different contexts is distinct
        - en_text: core content identifier
        
    Edge case: If file moves, creates new ID (acceptable - treat as new string)
    """
    content = f"{file_path}|{context}|{en_text}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

### Change Detection Strategy

**Modified string detection:**
```python
# String is "modified" if:
modified = (
    string_id_exists_in_previous_version 
    and current_en_text != previous_en_text
)

# String is "added" if:
added = not string_id_exists_in_previous_version

# String is "removed" if:
removed = (
    string_id_exists_in_previous_version 
    and not found_in_current_version
)
```

**Translation invalidation:**
When string is modified, mark all translations with `translation_status = 'needs_review'`. Translator must re-review even if auto-translation is re-run.

### Backward Compatibility

**Legacy mode preserved:**
```bash
# Old command still works
python rosetta.py -lru mod_necro > mod_necro/necro/rosetta_ru.nut

# Internally calls new architecture but outputs flat file
```

**Migration path:**
```bash
# Import existing translation into database
rosetta import-legacy rosetta_ru.nut --version 1.5.1.7
```

### Auto-Translation Integration

Reuse existing `xt.py` infrastructure:
- Yandex Translate API
- Claude 3.5 Sonnet API
- Translation cache (SQLite)
- Batch processing

Integrate as plugin system:
```python
# rosetta_translate.py
ENGINES = {
    'claude35': Claude35Engine,
    'yt': YandexEngine,
}

class TranslationEngine:
    def translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        """Translate batch of strings, return in same order"""
        pass
    
    def get_cache_key(self) -> str:
        """Identifier for caching (includes model version, settings)"""
        pass
```

### Build System Integration

Existing `Makefile` contains:
- `check-compile`: Syntax validation via `squirrel -c`
- `zip`: Package as `.zip` for distribution
- `install`: Copy to game data directory

**Integration approach:**

```makefile
# New database workflow (add to Makefile)
.PHONY: extract
extract:
	python -m rosetta_db extract game_$(VERSION)/ --version $(VERSION)

.PHONY: compile-db
compile-db:
	python -m rosetta_db compile --lang $(LANG) --version $(VERSION)

# Full workflow: extract → compile → validate → package
.PHONY: build-translation
build-translation: compile-db check-compile zip
```

**No encryption needed** - existing Makefile already handles everything.

## Testing Strategy

### Unit Tests

**Parser regression:**
- All existing `test_rosetta.py` tests must pass
- Add version tracking tests
- Add database operation tests

**Database integrity:**
- Foreign key constraints
- Unique constraints (string_id + lang)
- Transaction rollback on errors

### Integration Tests

**End-to-end workflow:**
```python
def test_full_workflow():
    # 1. Extract v1
    extract("game_v1/", "1.0.0", db)
    assert db.count_strings() == 100
    
    # 2. Translate
    auto_translate(db, "ru", "claude35")
    assert db.count_translations("ru", "approved") == 100
    
    # 3. Extract v2 (with changes)
    extract("game_v2/", "1.0.1", db)
    diff = compute_diff(db, "1.0.0", "1.0.1")
    assert len(diff.modified) == 5
    assert db.count_translations("ru", "needs_review") == 5
    
    # 4. Compile v2
    compile_mod(db, "ru", "1.0.1", output_dir)
    assert (output_dir / "translation_ru_1.0.1.dat").exists()
```

### Validation

**Compiled mod verification:**
- Decrypt compiled .cnut files
- Verify all translated strings present
- Check format matches Rosetta expectations
- Test in-game (manual QA)

## Dependencies

**Python 3.12+**

**Existing (DO NOT ADD):**
- `rosetta.py` - Parser with 47 tests ✅
- `xt.py` - Translation engines with cache ✅
- `Makefile` - Encryption/packaging ✅
- `requests` - Already used by xt.py ✅

**New (minimal additions):**
- `sqlite3` (stdlib) - Database
- `click` - CLI framework
- `polib` - PO file parsing (for Weblate integration)

**Optional:**
- `pytest` - Testing (already used)
- `rich` - Pretty CLI output

**Build tools (document existing):**
- Encryption command from Makefile
- Packaging command from Makefile

**Translation platforms (choose one):**
- Weblate (self-hosted, free)
- Crowdin (cloud, free tier)
- POEditor (cloud, paid)

## Repository Structure

```
battle-brothers-rosetta/
├── CLAUDE.md                 # This file (project spec)
├── README.md                 # User documentation (update)
├── CHANGELOG                 # Version history (PRESERVE)
├── LICENSE                   # License (PRESERVE)
├── Makefile                  # Build: check-compile + zip (PRESERVE)
├── .env.sample               # API config (PRESERVE)
├── .env                      # Local API keys (gitignored)
│
├── rosetta.py                # PRESERVE - ~55 tests, parser with extract()
├── xt.py                     # PRESERVE - translation engines (Claude, Yandex)
├── test_rosetta.py           # PRESERVE - all tests must pass
├── translations.db           # EXTENDED - add version tracking tables
│
├── rosetta/                  # PRESERVE - Squirrel runtime
│   ├── hooks.nut             # Runtime translation hooks
│   └── pack_ru.nut           # Russian translations (reference format)
│
├── scripts/                  # PRESERVE - Squirrel mod structure
│   └── !mods_preload/
│       └── !rosetta.nut      # Main ::Rosetta definition + add() API
│
├── rosetta_db/               # NEW - ~330 LOC total
│   ├── __init__.py
│   ├── database.py           # ~150 LOC: schema + CRUD (extends translations.db)
│   ├── extractor.py          # ~50 LOC: wrapper around rosetta.py
│   ├── differ.py             # ~30 LOC: SQL queries for version diff
│   ├── compiler.py           # ~30 LOC: generate pack_<lang>.nut
│   ├── exporters.py          # ~50 LOC: PO/JSON export/import
│   ├── translator.py         # ~20 LOC: wrapper around xt.py
│   └── cli.py                # CLI entry point (uses click)
│
├── tests/
│   ├── test_rosetta.py       # PRESERVE - existing ~55 tests
│   ├── test_database.py      # NEW - schema tests
│   └── test_integration.py   # NEW - end-to-end workflow
│
└── docs/
    ├── weblate_setup.md      # NEW - platform integration guide
    └── migration.md          # NEW - from legacy workflow
```

**Key principle: Preserve 90% of existing code, add 10% wrapper layer**

## Success Criteria

**Phase 1-5 Complete (~5-6 days):**
- [ ] Extract game v1.5.1.7 → database (3,800+ strings)
- [ ] Extract game v1.5.1.8 → detect changes automatically
- [ ] Export to Weblate PO format
- [ ] Import translations from Weblate
- [ ] Compile working `pack_<lang>.nut` file
- [ ] Package as `.zip` and verify translations in-game
- [ ] All ~55 `test_rosetta.py` tests still passing
- [ ] Update time: <5 minutes (extract → compile)

**Code Quality:**
- [ ] New code: ~330 LOC (not 2000+)
- [ ] Zero parser modifications (reuse rosetta.py)
- [ ] Zero translation engine modifications (reuse xt.py)
- [ ] Database extends existing `translations.db`

**Platform Integration:**
- [ ] PO export/import working
- [ ] Weblate instance deployable via Docker
- [ ] Translators can work without CLI knowledge

**Backward Compatibility:**
- [ ] Legacy `python rosetta.py` still works
- [ ] Existing .nut translations importable

**Documentation:**
- [ ] Weblate setup guide (`docs/weblate_setup.md`)
- [ ] Build pipeline documented (`docs/build_pipeline.md`)
- [ ] Migration guide from legacy (`docs/migration.md`)
- [ ] CLI help complete (`rosetta --help`)

## Open Questions

1. **Rosetta.add() format validation**: ✅ RESOLVED
   - Verified: `scripts/!mods_preload/!rosetta.nut` defines the API
   - Reference: `rosetta/pack_ru.nut` shows exact pair format
   - Test: Run `make check-compile` to validate generated .nut syntax

2. **Weblate vs. Crowdin**: Which platform should docs focus on?
   - Proposal: Primary guide for Weblate (self-hosted, free)
   - Secondary guide for Crowdin (cloud, easier setup)
   - Let community choose based on needs

3. **Pattern string translation**: How to show patterns in Weblate?
   - Example: `"Has <ap:int> AP"` should display as `"Has {ap} AP"` in UI
   - Action: Transform `<tag:type>` → `{tag}` in PO export, reverse on import

4. **Large game updates**: What if 500+ strings change?
   - Auto-translate all → Weblate review queue
   - Or: Mark all "needs review" → manual translation
   - Decision: Phase 4 based on translator preference

5. **Database migration**: How to import existing `pack_ru.nut` translations?
   - Parse existing file and populate `translations` table
   - One-time migration script needed

## File Inspection Checklist

All critical files have been inspected and verified. Summary:

### ✅ Verified Files

| File | Status | Key Findings |
|------|--------|--------------|
| `Makefile` | ✅ | No encryption; uses `squirrel -c` + `zip` |
| `scripts/!mods_preload/!rosetta.nut` | ✅ | Main `::Rosetta` definition, `add()` at line 46 |
| `rosetta/hooks.nut` | ✅ | Runtime translation hooks |
| `rosetta/pack_ru.nut` | ✅ | Reference format for translation pairs |
| `rosetta.py` | ✅ | `extract()` function at line 437 |
| `test_rosetta.py` | ✅ | ~55 test cases |
| `xt.py` | ✅ | `translate()` function, SQLite cache |

### Output Format (from `rosetta/pack_ru.nut`)

```squirrel
local def = ::Rosetta;
local rosetta = {
    mod = {id = def.ID, version = def.Version}
    author = "hackflow"
    lang = "ru"
}
local pairs = [
    {
        mode = "pattern"
        en = "<actor:str_tag> has hit <victim:str_tag>'s shield for <damage:int> damage"
        ru = "<actor> нанёс щиту <victim> <damage> урона"
    }
    {en = "Is always content with being in reserve", ru = "Не ухудшается настроение..."}
]
def.add(rosetta, pairs);
```

### Validation Command

```bash
make check-compile  # Validates all .nut syntax via squirrel -c
```

## Translation Platform Deep Dive

### Why Use Existing Platforms?

Building custom translation UI requires:
- User authentication/authorization
- Review workflow (pending → reviewed → approved)
- Translation memory/glossary
- Collaboration features (assignments, comments)
- Version control integration
- UI/UX development

**Estimated effort: 4-6 weeks of development**

Using existing platforms: **0 development, ~1 day integration**

### Platform Comparison

| Feature | Weblate | Crowdin | POEditor | Custom UI |
|---------|---------|---------|----------|-----------|
| **Cost** | Free (self-hosted) | Free tier (10k strings) | Paid ($19/mo) | Free (dev time) |
| **Setup** | Docker deploy | Cloud signup | Cloud signup | 4-6 weeks dev |
| **Context display** | ✅ msgctxt | ✅ Full context | ✅ Notes | Need to build |
| **Translation memory** | ✅ Built-in | ✅ AI-powered | ✅ Built-in | Need to build |
| **Review workflow** | ✅ States + QA | ✅ Proofreading | ✅ Contributors | Need to build |
| **Git integration** | ✅ Native | ✅ Native | ❌ | Would need to build |
| **API** | ✅ Full REST | ✅ Full REST | ✅ Full REST | Would need to build |
| **Game localization** | ✅ Used by games | ✅ Used by games | ✅ Used by games | Unknown |
| **Offline work** | ✅ Download PO | ❌ Cloud only | ❌ Cloud only | Could build |

### Recommended: Weblate

**Reasons:**
1. **Free and self-hosted** - No recurring costs
2. **Git integration** - Commit translations directly to repo
3. **Game-friendly** - Used by 0 A.D., OpenTTD, SuperTuxKart
4. **Context support** - Shows `msgctxt` with file::function
5. **Checks system** - Detects untranslated, formatting issues
6. **Translation memory** - Suggests similar translations
7. **Docker deployment** - Easy to set up

**Setup (5 minutes):**
```bash
# 1. Deploy Weblate via Docker
docker run -d -p 8080:8080 weblate/weblate

# 2. Create project "Battle Brothers"
# 3. Add component with PO file format
# 4. Configure Git repository (optional)

# Done - translators can start working
```

**Integration:**
```bash
# Export from database
rosetta export --format po --lang ru > translations_ru.po

# Upload to Weblate (web UI or CLI)
wlc upload battle-brothers/main translations_ru.po

# Translators work in Weblate...

# Download completed translations
wlc download battle-brothers/main
rosetta import --format po translations_ru.po

# Compile mod
rosetta compile --lang ru --version 1.5.1.8
```

### Alternative: Crowdin

**Good for cloud-based teams:**
- No server maintenance
- Free tier: 10,000 strings (enough for Battle Brothers)
- AI-powered suggestions
- Screenshot context (upload game screenshots)

**Trade-offs:**
- Requires internet connection
- Free tier limits
- Less control vs. self-hosted

### Fallback: CLI-only

**For solo translators or offline work:**
```bash
# Simple interactive mode
rosetta translate --lang ru --interactive

# Or export to CSV for spreadsheet editing
rosetta export --format csv > translations.csv
# Edit in Excel/LibreOffice
rosetta import --format csv translations.csv
```

**When to use:**
- No collaboration needed
- Prefer offline work
- Translating alone
- Quick one-off translation

## References

- **Original Rosetta**: https://github.com/Suor/battle-brothers-mods
- **Battle Brothers Modding**: https://www.nexusmods.com/battlebrothers/mods/
- **Squirrel Language**: http://www.squirrel-lang.org/
- **Weblate**: https://weblate.org/ (recommended platform)
- **Weblate for games**: https://docs.weblate.org/en/latest/formats.html
- **Crowdin**: https://crowdin.com/
- **POEditor**: https://poeditor.com/
- **PO file format**: https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html
- **Translation platform comparison**: https://phrase.com/blog/posts/translation-management-systems-comparison/
