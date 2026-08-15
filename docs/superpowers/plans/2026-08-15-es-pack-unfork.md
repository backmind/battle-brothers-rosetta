# Plan: des-forkear battle-brothers-rosetta y crear el pack ES del juego base

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preservar la traducción castellana curada (13.804 pares), sincronizar el fork con upstream 0.4.0 sin modificar ni una línea del runtime de Rosetta, y publicar la traducción del juego base como mod independiente (`mod_rosetta_base_es`) que sobrevive a las actualizaciones del juego.

**Architecture:** Tres ramas: `legacy-es-pipeline` (archivo permanente de todo el trabajo actual), `master` (espejo limpio de upstream Suor/battle-brothers-rosetta), `es-pack` (rama de trabajo que SOLO añade ficheros nuevos bajo `es_pack/` y `docs/`, nunca toca ficheros upstream). El corpus canónico es un fichero de texto en formato Rosetta (`es_pack/corpus/base_es.nut`) regenerable con el extractor upstream (`rosetta.py -r`). Un script de build (`build_dist.py`) filtra el corpus (descarta pares sin traducir, pone en cuarentena los patrones con placeholders inválidos) y empaqueta el zip instalable.

**Tech Stack:** Git, Python 3.12 (siempre vía `uv run`), `rosetta.py` upstream 0.4.0 (extract + load_ref + modos -r/-c), Squirrel (runtime del juego), Git Bash en Windows.

**Spec:** La evaluación acordada en la conversación del 2026-08-15 (resumen en la sección "Contexto" de abajo). No existe fichero de spec separado.

## Global Constraints

- La rama `es-pack` NUNCA modifica ficheros que existan en upstream. Solo añade ficheros nuevos bajo `es_pack/` y `docs/`. Esto garantiza merges de upstream sin conflictos para siempre.
- La rama `legacy-es-pipeline` es un archivo permanente: nunca rebase, nunca force-push, nunca borrarla.
- Todo Python se ejecuta con `uv run` y con `PYTHONUTF8=1` (el `open()` de `load_ref` usa la codificación por defecto del sistema; en Windows sin esa variable corrompería las tildes).
- Runtime objetivo: Rosetta >= 0.4.0 sin parches. Cualquier limitación se resuelve en el pack o se reporta a upstream, jamás parcheando `!rosetta.nut`.
- Sintaxis válida de placeholders (la única que el runtime 0.4.0 entiende): en `en` la forma `<nombre:tipo>` (p. ej. `<actor:str_tag>`, `<hp:int>`); en `es` la forma `<nombre>` o `<nombre:flag>`. Todo par cuyo placeholder no cumpla esto va a cuarentena, no al zip.
- Sin guiones largos (em-dash) ni emojis en ningún texto generado (regla global del usuario).
- Mensajes de commit terminan con: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- Nunca afirmar que algo funciona sin haber ejecutado el comando de verificación y visto la salida esperada.

## Variables de entorno del plan

Rutas de la máquina del usuario (verificadas en Task 5; si alguna no existe, parar y preguntar al usuario):

| Variable | Valor |
|----------|-------|
| `REPO` | `D:\git\battle-brothers-rosetta` |
| `DECOMP_EN` | `D:\GOG\Battle Brothers\!Downloads\bbros\bin\comparer\original` (árbol EN descompilado, versión 1.5.1.8) |
| `DECOMP_ES` | `D:\GOG\Battle Brothers\!Downloads\bbros\bin\comparer\spanish_tr` (traducción fan descompilada, solo referencia) |
| `GAME_DATA` | `D:\GOG\Battle Brothers\data` (a verificar) |
| `BB_LOG` | `C:\Users\hda\Documents\Battle Brothers\log.html` |

En los comandos de Git Bash se usan con barras normales: `"/d/GOG/Battle Brothers/!Downloads/bbros/bin/comparer/original"`.

Nota sobre versiones: el juego instalado puede estar (y es deseable que esté) en una versión más nueva que el árbol descompilado 1.5.1.8. No bloquea nada: el pack es independiente de la versión, y verificar in-game sobre la última versión es la mejor prueba de esa promesa. El usuario actualizará el juego vía GOG antes de la Task 10; las strings nuevas del parche se verán en inglés y eso es el comportamiento esperado, no un fallo.

## Contexto (léelo aunque tengas prisa)

- Rosetta (de Suor) traduce en runtime: intercepta strings en la frontera Squirrel/JS y las sustituye si hay par EN-ES registrado. Lo que no coincide se muestra en inglés. Por eso una traducción Rosetta no se rompe con las actualizaciones del juego.
- El fork actual (backmind/battle-brothers-rosetta) tiene TODO el trabajo sin commitear en el working dir: `rosetta/base_es.nut` (13.804 pares es), `translation_1.5.1.7.po`, `translations.db` (ignorada por `*.db` en .gitignore), una capa Python `rosetta_db/`, y 3 parches al runtime `scripts/!mods_preload/!rosetta.nut`.
- Los parches al runtime sobran: upstream ya expone `::Rosetta.activate("es")` público y documenta que una traducción se distribuye como mod separado (README upstream, secciones Single-File y Multi-File).
- 1.683 pares llevan `mode = "pattern"` con placeholders crudos de extracción (`<this.Math.round(...)>`, `<ret>`). El runtime 0.4.0 espera `<nombre:tipo>`; con los crudos, `validateRule` LANZA una excepción (label en `es` que no está en `en`) y abortaría la carga de TODO el pack. Por eso el build filtra a cuarentena todo par con placeholder inválido.
- `validatePair` 0.4.0 sí descarta con warning (sin romper) los pares con traducción vacía: se pueden regenerar corpus con huecos sin peligro, pero el build los excluye del zip para no ensuciar el log.
- Sobre "¿Rosetta contempla el juego base?": los hooks interceptan strings de forma genérica (tooltips, eventos, contratos, perks), vengan de mods o del juego base; ya está demostrado in-game por el usuario. Lo único que el juego base necesita de especial es (a) activar el idioma sin depender de `detect()` (resuelto con `::Rosetta.activate("es")` desde el pack) y (b) las strings que NO pasan por Squirrel: la UI construida en JS (menú principal, botones) y los rótulos del mapa renderizados por el motor C++. Para (b) se mantiene el `.dat` con la carpeta `js` traducida como pieza aparte (Fase 5); upstream tiene `docs/js-plan.md` para hacerla obsoleta en el futuro.
- Los DLC no son un caso especial: sus scripts viven en el mismo árbol `scripts/` descompilado (p. ej. `scripts/events/events/dlc2/`), así que la extracción los cubre igual.
- Reuso sobre reescritura: el parser oficial del formato Rosetta es `load_ref()` dentro de `rosetta.py` upstream. `build_dist.py` lo importa; prohibido escribir otro parser de .nut.

## Estructura de ficheros resultante (rama es-pack)

```
es_pack/
    .gitignore                  (contiene: build/)
    corpus/
        base_es.nut             (CANONICO: todos los pares, traducidos o no; regenerable con -r)
        STATS.md                (números de cada regeneración)
    src/
        scripts/!mods_preload/mod_rosetta_base_es.nut   (wrapper del mod, escrito a mano, estable)
    tools/
        build_dist.py           (corpus -> zip distribuible + informe de cuarentena)
        test_build_dist.py      (tests del build)
        normalize_seed.py       (contingencia: solo si load_ref no traga el seed)
    README.md                   (instrucciones de instalación para usuarios finales)
docs/superpowers/plans/2026-08-15-es-pack-unfork.md     (este plan)
```

---

# FASE 0: SALVAGUARDA (no se pierde nada, hoy)

### Task 1: Rama de rescate con snapshot completo

**Files:**
- Delete: `D:\git\battle-brothers-rosetta\nul` (artefacto accidental de shell)
- Commit de TODO el working dir actual en rama nueva `legacy-es-pipeline`

**Interfaces:**
- Produces: rama `legacy-es-pipeline` en origin con `rosetta/base_es.nut`, `base_es.nut.bak`, `translation_1.5.1.7.po`, `translations.db`, `translations.db.bak`, `rosetta_db/`, `create_po.py`, `check_counts.py`, CLAUDE.md, README modificado, `!rosetta.nut` parcheado y este plan.

- [ ] **Step 1: Borrar el fichero accidental `nul`**

```bash
cd /d/git/battle-brothers-rosetta
rm nul || cmd //c 'del \\.\D:\git\battle-brothers-rosetta\nul'
ls nul 2>&1
```
Esperado: `ls: cannot access 'nul': No such file or directory`

- [ ] **Step 2: Crear la rama de rescate (arrastra el working dir tal cual)**

```bash
git switch -c legacy-es-pipeline
```
Esperado: `Switched to a new branch 'legacy-es-pipeline'`

- [ ] **Step 3: Añadir todo, incluidos los binarios ignorados por .gitignore**

```bash
git add -A
git add -f translations.db translations.db.bak base_es.nut.bak
git status --short | head -30
```
Esperado: aparecen en verde (staged) al menos: `rosetta/base_es.nut`, `translation_1.5.1.7.po`, `translations.db`, `translations.db.bak`, `base_es.nut.bak`, `rosetta_db/`, `CLAUDE.md`, `create_po.py`, `docs/superpowers/plans/2026-08-15-es-pack-unfork.md`. NO debe aparecer `.venv` ni `__pycache__` ni `nul`.

- [ ] **Step 4: Commit**

```bash
git commit -m "rescate: snapshot completo del pipeline ES y activos de traduccion

Archivo permanente del trabajo previo al des-forkeo: corpus base_es.nut
(13.804 pares), PO 1.5.1.7, translations.db (12.428 traducciones reviewed),
capa rosetta_db, scripts de bootstrap y parches al runtime 0.2.0.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Push y verificación remota**

```bash
git push -u origin legacy-es-pipeline
git ls-remote origin legacy-es-pipeline
```
Esperado: `git ls-remote` devuelve una línea con el hash del commit. Si el push falla por tamaño (no debería: ~40 MB total, límite GitHub 100 MB por fichero), parar y avisar al usuario.

### Task 2: Acta de rescate con recuentos verificables

**Files:**
- Create: `RESCUE_NOTES.md` (en la rama `legacy-es-pipeline`)

**Interfaces:**
- Consumes: rama `legacy-es-pipeline` de Task 1.
- Produces: `RESCUE_NOTES.md` con los números de referencia que las fases posteriores usan como baseline (pares totales, traducciones en DB).

- [ ] **Step 1: Obtener los recuentos**

```bash
cd /d/git/battle-brothers-rosetta
grep -c '        en = ' rosetta/base_es.nut
grep -c 'mode = "pattern"' rosetta/base_es.nut
grep -c 'en = "[^"]*<' rosetta/base_es.nut
PYTHONUTF8=1 uv run python -c "
import sqlite3
con = sqlite3.connect('translations.db')
print('strings:', con.execute('select count(*) from strings').fetchone()[0])
print('translations:', con.execute('select count(*) from translations').fetchone()[0])
print('versions:', con.execute('select version from game_versions').fetchall())
"
```
Esperado (baseline conocido, tolerancia 0): `13804`, `1683`, `1476`, `strings: 16169`, `translations: 12428`, `versions: [('1.5.1.8',)]`.

- [ ] **Step 2: Escribir RESCUE_NOTES.md**

Contenido exacto (sustituyendo los números por la salida real del Step 1 si difiere, y anotando la diferencia):

```markdown
# Acta de rescate (2026-08-15)

Rama archivo permanente del trabajo de traduccion ES previo al des-forkeo.
NO borrar, NO rebasear, NO force-push.

## Activos y recuentos

| Activo | Que es | Recuento |
|--------|--------|----------|
| rosetta/base_es.nut | Pack compilado por rosetta_db (editado a mano al final: activate) | 13.804 pares, 1.683 mode=pattern, 1.476 con placeholders crudos |
| base_es.nut.bak | Estado anterior del pack (difiere del actual) | - |
| translation_1.5.1.7.po | PO bilingue generado por create_po.py (bootstrap desde la traduccion fan) | - |
| translations.db | BBDD con schema versionado | 16.169 strings (v1.5.1.8), 12.428 traducciones reviewed |
| translations.db.bak | Estado anterior de la BBDD | - |
| rosetta_db/ | Capa Python: extractor, compiler, exporters, import_nut, web UI Flask | - |
| create_po.py | Alineador heuristico EN/ES de dos arboles .nut descompilados | - |
| scripts/!mods_preload/!rosetta.nut | Runtime 0.2.0 con 3 parches locales (regex de patrones, detect es, include base_es) | - |

## Procedencia de la traduccion

Traduccion fan de reemplazo (elgranfoca y anteriores, NexusMods "Traduccion completa
al Castellano") descompilada en DECOMP_ES, alineada contra DECOMP_EN (1.5.1.8) con
create_po.py (matching posicional + heuristico), importada a translations.db y
compilada a base_es.nut.

## Defectos conocidos (por eso se regenera en la rama es-pack)

- Los 1.683 pares mode=pattern usan placeholders crudos (<this...>, <ret>) que el
  runtime 0.4.0 no parsea; en 0.4.0 ademas harian throw en validateRule.
- extractor.py no limpiaba rosetta.SEEN entre ficheros: strings repetidas perdidas
  o mal atribuidas.
- base_es.nut fue editado a mano tras compilar (activate final).
```

- [ ] **Step 3: Commit y push**

```bash
git add RESCUE_NOTES.md
git commit -m "rescate: acta con recuentos baseline y defectos conocidos

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin legacy-es-pipeline
```

---

# FASE 1: SINCRONIZAR EL FORK Y CREAR LA RAMA DE TRABAJO

### Task 3: master = upstream/master (0.4.0)

**Interfaces:**
- Consumes: Task 1 completada (working dir limpio tras el commit de rescate).
- Produces: `master` local y en origin apuntando al HEAD de Suor (commit `8d9b612` o posterior).

- [ ] **Step 1: Volver a master (el working dir queda limpio, el trabajo vive en la rama de rescate)**

```bash
cd /d/git/battle-brothers-rosetta
git switch master
git status --short
```
Esperado: sin salida (working dir limpio). Si aparece algo, PARAR: significa que Task 1 no commiteó todo; volver a Task 1.

- [ ] **Step 2: Asegurar el remoto upstream y traer**

```bash
git remote add upstream https://github.com/Suor/battle-brothers-rosetta.git 2>/dev/null
git fetch upstream
```

- [ ] **Step 3: Fast-forward y push**

```bash
git merge --ff-only upstream/master
git log --oneline -1
git push origin master
```
Esperado: el merge dice `Fast-forward`; el log muestra `8d9b612 Add plan for migrating old-style inplace translations to rosetta` (o un commit más nuevo de Suor si upstream avanzó). Si `--ff-only` falla, PARAR e investigar (no debería: master era ancestro directo).

### Task 4: Rama es-pack con esqueleto

**Files:**
- Create: `es_pack/.gitignore`
- Create: `docs/superpowers/plans/2026-08-15-es-pack-unfork.md` (traído de la rama de rescate)

**Interfaces:**
- Produces: rama `es-pack` publicada, con el directorio `es_pack/` y este plan versionado en ella.

- [ ] **Step 1: Crear la rama desde master**

```bash
git switch -c es-pack master
```

- [ ] **Step 2: Traer el plan desde la rama de rescate**

```bash
git checkout legacy-es-pipeline -- docs/superpowers/plans/2026-08-15-es-pack-unfork.md
```

- [ ] **Step 3: Esqueleto de es_pack con gitignore anidado (así no tocamos el .gitignore de upstream)**

```bash
mkdir -p es_pack/corpus es_pack/src/scripts/'!mods_preload' es_pack/tools es_pack/build
printf 'build/\n' > es_pack/.gitignore
```

- [ ] **Step 4: Commit y push**

```bash
git add docs es_pack
git commit -m "es-pack: esqueleto del pack de traduccion y plan de trabajo

Rama que solo AGREGA ficheros bajo es_pack/ y docs/. Nunca modifica
ficheros de upstream, para que el merge de futuras versiones de Rosetta
sea siempre trivial.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push -u origin es-pack
```

---

# FASE 2: CORPUS CANONICO REGENERADO CON EL EXTRACTOR 0.4.0

### Task 5: Verificar el entorno (árboles descompilados y carpeta del juego)

**Interfaces:**
- Produces: confirmación de las rutas `DECOMP_EN` y `GAME_DATA`. Si alguna falla, USER GATE: preguntar al usuario dónde están antes de seguir.

- [ ] **Step 1: Árbol EN descompilado**

```bash
ls "/d/GOG/Battle Brothers/!Downloads/bbros/bin/comparer/original/scripts" | head
find "/d/GOG/Battle Brothers/!Downloads/bbros/bin/comparer/original/scripts" -name '*.nut' | wc -l
```
Esperado: listado con `ambitions`, `contracts`, `events`, `ui`...; recuento de .nut mayor que 1500.

- [ ] **Step 2: Presencia de DLCs en el árbol**

```bash
ls "/d/GOG/Battle Brothers/!Downloads/bbros/bin/comparer/original/scripts/events/events" | grep -c dlc
```
Esperado: 1 o más (hay subdirectorios `dlc*`). Los DLC comparten árbol; no requieren tratamiento aparte.

- [ ] **Step 3: Carpeta data del juego**

```bash
ls "/d/GOG/Battle Brothers/data" | head -20
```
Esperado: ficheros `data_*.dat` del juego. Anotar además si ya están los zips de dependencias (mod_rosetta, MSU, modern hooks, stdlib) o el usuario tendrá que instalarlos en Task 10.

### Task 6: Seed y smoke test de load_ref

**Files:**
- Create: `es_pack/build/seed_base_es.nut` (efímero, gitignored)
- Create (solo si hace falta la contingencia): `es_pack/tools/normalize_seed.py`

**Interfaces:**
- Consumes: `rosetta/base_es.nut` de la rama `legacy-es-pipeline`; `rosetta.py` 0.4.0 en la raíz.
- Produces: seed validado que `load_ref` parsea, listo para la regeneración completa de Task 7.

- [ ] **Step 1: Extraer el seed desde la rama de rescate**

```bash
cd /d/git/battle-brothers-rosetta
git show legacy-es-pipeline:rosetta/base_es.nut > es_pack/build/seed_base_es.nut
wc -c es_pack/build/seed_base_es.nut
```
Esperado: ~8.8 MB (8842852 bytes).

- [ ] **Step 2: Smoke test sobre un subdirectorio pequeño**

```bash
PYTHONUTF8=1 uv run python rosetta.py "/d/GOG/Battle Brothers/!Downloads/bbros/bin/comparer/original/scripts/ambitions" -les -r es_pack/build/seed_base_es.nut > es_pack/build/smoke_ambitions.nut
grep -c 'Tu tarea' es_pack/build/smoke_ambitions.nut
grep -c 'es = ""' es_pack/build/smoke_ambitions.nut
```
Esperado: sin traceback de Python en stderr; `Tu tarea` aparece 1 o más veces (el seed rellenó traducciones conocidas); el número de `es = ""` es bajo comparado con el total del fichero.

- [ ] **Step 3 (SOLO SI el Step 2 falla con traceback en load_ref): contingencia normalize_seed**

Crear `es_pack/tools/normalize_seed.py` con este contenido y regenerar el seed:

```python
"""Convierte el base_es.nut del compilador legacy a bloques minimos que
load_ref parsea seguro. Solo se usa si load_ref falla con el seed original."""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text(encoding="utf-8")
PAIR_RE = re.compile(
    r'\{\s*(?P<mode>mode = "pattern"\s*)?'
    r'en = (?P<en>"(?:[^"\\]|\\.)*")\s*'
    r'es = (?P<es>"(?:[^"\\]|\\.)*")\s*\}',
    re.S,
)
out = ['if (!("Rosetta" in getroottable())) return;\n',
       'local rosetta = {\n    mod = {id = "vanilla", version = "1.5.1.8"}\n'
       '    author = "seed"\n    lang = "es"\n}\nlocal pairs = [\n']
n = 0
for m in PAIR_RE.finditer(src):
    mode = '        mode = "pattern"\n' if m.group("mode") else ""
    out.append("    {\n%s        en = %s\n        es = %s\n    }\n"
               % (mode, m.group("en"), m.group("es")))
    n += 1
out.append("]\n::Rosetta.add(rosetta, pairs);\n")
Path(sys.argv[2]).write_text("".join(out), encoding="utf-8")
print("pares:", n)
```

```bash
PYTHONUTF8=1 uv run python es_pack/tools/normalize_seed.py es_pack/build/seed_base_es.nut es_pack/build/seed_norm.nut
```
Esperado: `pares: 13804`. Usar `seed_norm.nut` como seed en adelante y repetir el Step 2. Commitear el script:

```bash
git add es_pack/tools/normalize_seed.py
git commit -m "es-pack: normalizador de seed legacy para load_ref

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 7: Regeneración completa del corpus

**Files:**
- Create: `es_pack/corpus/base_es.nut` (EL fichero canónico a partir de ahora)
- Create: `es_pack/corpus/STATS.md`

**Interfaces:**
- Consumes: seed validado de Task 6.
- Produces: `es_pack/corpus/base_es.nut` en formato rosetta.py 0.4.0, con las traducciones del seed volcadas y las strings nuevas o sin match con `es = ""`. `STATS.md` con los recuentos.

- [ ] **Step 1: Regenerar (tarda varios minutos sobre ~1500+ ficheros)**

```bash
cd /d/git/battle-brothers-rosetta
PYTHONUTF8=1 uv run python rosetta.py "/d/GOG/Battle Brothers/!Downloads/bbros/bin/comparer/original/scripts" -les -r es_pack/build/seed_base_es.nut -q > es_pack/corpus/base_es.nut
```
(Si Task 6 usó la contingencia, referenciar `seed_norm.nut`.)

- [ ] **Step 2: Recuentos y criterio de aceptación**

```bash
grep -c '\ben = "' es_pack/corpus/base_es.nut
grep -c 'es = ""' es_pack/corpus/base_es.nut
```
Sea TOTAL el primer número y VACIOS el segundo: TRADUCIDOS = TOTAL - VACIOS.
Aceptación: TRADUCIDOS >= 11000. (Baseline seed: 13.804 pares; se espera alguna pérdida por deduplicación correcta y algún no-match, no un desplome.)
Si TRADUCIDOS < 11000: PARAR. Causa más probable: load_ref no parseó bien el seed (volver a Task 6 Step 3) o la ruta de extracción no es la correcta (volver a Task 5).

- [ ] **Step 3: Escribir STATS.md**

```markdown
# Estadisticas del corpus

## Regeneracion 2026-MM-DD (arbol 1.5.1.8, seed legacy 13.804 pares)

- Pares totales: <TOTAL>
- Traducidos: <TRADUCIDOS>
- Sin traducir (es = ""): <VACIOS>
- Comando: rosetta.py <DECOMP_EN>/scripts -les -r seed_base_es.nut
```

- [ ] **Step 4: Commit**

```bash
git add es_pack/corpus/base_es.nut es_pack/corpus/STATS.md
git commit -m "es-pack: corpus canonico regenerado con extractor 0.4.0

Regenerado desde el arbol EN 1.5.1.8 con -r sobre el seed legacy.
El corpus incluye pares sin traducir (es = \"\") a proposito: es el
fichero de trabajo; el filtrado para distribucion lo hace build_dist.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin es-pack
```

---

# FASE 3: PACK v0.1.0 (SOLO LITERALES VALIDOS) Y VERIFICACION IN-GAME

### Task 8: build_dist.py con TDD

**Files:**
- Create: `es_pack/tools/build_dist.py`
- Test: `es_pack/tools/test_build_dist.py`

**Interfaces:**
- Consumes: `es_pack/corpus/base_es.nut` (Task 7); `rosetta.load_ref` y sus globals `REF_BLOCKS`, `REF_PAIRS`, `REF_RULES`, `CODE_RULES`, `DUP_BLOCKS`, `KNOWN_WORDS` (upstream 0.4.0); `es_pack/src/scripts/!mods_preload/mod_rosetta_base_es.nut` (Task 9, para el zip; ver nota en Step 6).
- Produces: funciones `load_blocks(path) -> list[str]`, `classify(block) -> "dist"|"wip"|"drop"`, `get_field(block, name) -> str|None`; artefactos `es_pack/build/mod_rosetta_base_es/base_es.nut`, `es_pack/build/patterns_wip.nut`, `es_pack/build/mod_rosetta_base_es_1.5.1.8-1.zip`.

- [ ] **Step 1: Escribir el test que falla**

`es_pack/tools/test_build_dist.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dist import classify, get_field, load_blocks

FIXTURE = '''if (!("Rosetta" in getroottable())) return;

local rosetta = {
    mod = {id = "vanilla", version = "0.0.0"}
    author = "test"
    lang = "es"
}
local pairs = [
    {
        en = "Your Task"
        es = "Tu tarea"
    }
    {
        en = "Not yet translated"
        es = ""
    }
    {
        mode = "pattern"
        en = "You gain <this.Const.Strings.getArticle(item.getName())>"
        es = "Ganas <this.Const.Strings.getArticle(item.getName())>"
    }
    {
        mode = "pattern"
        en = "Has a range of <range:int> tiles"
        es = "Tiene un alcance de <range> casillas"
    }
]
::Rosetta.add(rosetta, pairs);
'''


def test_load_blocks_and_classify(tmp_path):
    f = tmp_path / "fixture_es.nut"
    f.write_text(FIXTURE, encoding="utf-8")
    blocks = load_blocks(f)
    assert len(blocks) == 4
    kinds = [classify(b) for b in blocks]
    # literal traducido -> dist; vacio -> drop; placeholder crudo -> wip;
    # patron tipado valido -> dist
    assert kinds == ["dist", "drop", "wip", "dist"]


def test_load_blocks_is_repeatable(tmp_path):
    f = tmp_path / "fixture_es.nut"
    f.write_text(FIXTURE, encoding="utf-8")
    assert len(load_blocks(f)) == 4
    assert len(load_blocks(f)) == 4  # los globals de rosetta se limpian entre cargas


def test_get_field_unescapes():
    block = '{\n en = "a\\nb"\n es = "c \\"d\\""\n}'
    assert get_field(block, "en") == "a\nb"
    assert get_field(block, "es") == 'c "d"'
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

```bash
cd /d/git/battle-brothers-rosetta
PYTHONUTF8=1 uv run pytest es_pack/tools/test_build_dist.py -v
```
Esperado: FAIL o ERROR con `ModuleNotFoundError: No module named 'build_dist'`.

- [ ] **Step 3: Implementar build_dist.py**

`es_pack/tools/build_dist.py`:

```python
"""Genera la version distribuible del pack ES a partir del corpus.

Uso:  PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py

Lee   es_pack/corpus/base_es.nut  (corpus completo)
Escribe:
  es_pack/build/mod_rosetta_base_es/base_es.nut          pares validos
  es_pack/build/patterns_wip.nut                         cuarentena (Fase 4)
  es_pack/build/scripts/!mods_preload/mod_rosetta_base_es.nut
  es_pack/build/mod_rosetta_base_es_<version>.zip

Reglas de clasificacion por par:
  drop  sin traduccion (es = "")
  wip   algun placeholder <...> que no cumpla <nombre:tipo> en en
        o <nombre[:flag]> en es (el runtime 0.4.0 haria throw o no matchearia)
  dist  todo lo demas
"""
import ast
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import rosetta  # upstream 0.4.0 en la raiz del repo: load_ref es el parser oficial

CORPUS = REPO / "es_pack" / "corpus" / "base_es.nut"
SRC = REPO / "es_pack" / "src"
BUILD = REPO / "es_pack" / "build"

GAME_VERSION = "1.5.1.8"
PACK_VERSION = GAME_VERSION + "-1"

STR_RE = r'"(?:[^"\\]|\\.)*"'
EN_PLACE_RE = re.compile(r"^<\w+:\w+>$")
ES_PLACE_RE = re.compile(r"^<\w+(:\w+)?>$")

HEADER = (
    'if (!("Rosetta" in getroottable())) return;\n'
    'if (::Hooks.SQClass.ModVersion(::Rosetta.Version) '
    '< ::Hooks.SQClass.ModVersion("0.4.0")) return;\n\n'
    "local rosetta = {\n"
    '    mod = {id = "vanilla", version = "%s"}\n'
    '    author = "comunidad hispana de Battle Brothers"\n'
    '    lang = "es"\n'
    "}\n"
    "local pairs = [\n" % GAME_VERSION
)
FOOTER = "]\n::Rosetta.add(rosetta, pairs);\n"


def get_field(block, name):
    m = re.search(rf"\b{name}\s*=\s*({STR_RE})", block)
    return ast.literal_eval(m.group(1)) if m else None


def load_blocks(path):
    for g in (rosetta.REF_BLOCKS, rosetta.REF_PAIRS, rosetta.REF_RULES,
              rosetta.CODE_RULES, rosetta.KNOWN_WORDS):
        g.clear()
    del rosetta.DUP_BLOCKS[:]
    rosetta.OPTS["lang"] = "es"
    rosetta.OPTS["quiet"] = True
    rosetta.load_ref(str(path))
    return list(rosetta.REF_BLOCKS.values())


def classify(block):
    en = get_field(block, "en")
    es = get_field(block, "es")
    if en is None or not es:
        return "drop"
    ph_en = re.findall(r"<[^>]*>", en)
    ph_es = re.findall(r"<[^>]*>", es)
    if not ph_en and not ph_es:
        return "dist"
    ok_en = all(EN_PLACE_RE.match(p) for p in ph_en)
    ok_es = all(ES_PLACE_RE.match(p) for p in ph_es)
    return "dist" if ok_en and ok_es else "wip"


def emit(path, blocks):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join("    " + b.replace("\n", "\n    ") for b in blocks)
    path.write_text(HEADER + body + "\n" + FOOTER, encoding="utf-8")


def main():
    blocks = load_blocks(CORPUS)
    buckets = {"dist": [], "wip": [], "drop": []}
    for b in blocks:
        buckets[classify(b)].append(b)
    print("total: %d  dist: %d  wip: %d  drop: %d" % (
        len(blocks), len(buckets["dist"]), len(buckets["wip"]),
        len(buckets["drop"])))

    pairs_rel = Path("mod_rosetta_base_es/base_es.nut")
    wrapper_rel = Path("scripts/!mods_preload/mod_rosetta_base_es.nut")

    emit(BUILD / pairs_rel, buckets["dist"])
    emit(BUILD / "patterns_wip.nut", buckets["wip"])
    (BUILD / wrapper_rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / wrapper_rel, BUILD / wrapper_rel)

    zip_path = BUILD / ("mod_rosetta_base_es_%s.zip" % PACK_VERSION)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(BUILD / wrapper_rel, wrapper_rel.as_posix())
        z.write(BUILD / pairs_rel, pairs_rel.as_posix())
    print("zip:", zip_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Correr los tests hasta verde**

```bash
PYTHONUTF8=1 uv run pytest es_pack/tools/test_build_dist.py -v
```
Esperado: 3 passed. Si `load_blocks` devuelve otro número de bloques, depurar contra el comportamiento real de `load_ref` (leerlo en `rosetta.py`), no relajar el assert.

- [ ] **Step 5: Comprobar que los tests de upstream siguen intactos**

```bash
PYTHONUTF8=1 uv run pytest test_rosetta.py -q
```
Esperado: todos pasan (no hemos tocado nada de upstream; esto lo demuestra).

- [ ] **Step 6: Commit**

Nota: `main()` necesita el wrapper de Task 9 para el zip; los TESTS no (solo cubren funciones puras). Commitear ya:

```bash
git add es_pack/tools/build_dist.py es_pack/tools/test_build_dist.py
git commit -m "es-pack: build_dist con clasificacion dist/wip/drop y tests

Reusa rosetta.load_ref como parser (cero parsers nuevos de .nut).
Cuarentena para placeholders no tipados: en 0.4.0 harian throw en
validateRule y abortarian la carga del pack entero.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 9: Wrapper del mod y primer build completo

**Files:**
- Create: `es_pack/src/scripts/!mods_preload/mod_rosetta_base_es.nut`

**Interfaces:**
- Consumes: `build_dist.py` (Task 8), corpus (Task 7).
- Produces: `es_pack/build/mod_rosetta_base_es_1.5.1.8-1.zip` con el layout exacto que el juego espera.

- [ ] **Step 1: Escribir el wrapper (formato oficial del README upstream, secciones Single-File y Multi-File)**

`es_pack/src/scripts/!mods_preload/mod_rosetta_base_es.nut`:

```squirrel
// Traduccion del juego base Battle Brothers al castellano, via Rosetta.
// Requiere: Modern Hooks, MSU >= 1.6.0, stdlib >= 2.5, Rosetta >= 0.4.0.
// Las strings sin par registrado se muestran en ingles: este mod no se
// rompe con las actualizaciones del juego.
if (!("Rosetta" in getroottable())) return;

local def = {
    ID = "mod_rosetta_base_es"
    Name = "Battle Brothers en Castellano (Rosetta)"
    Version = "1.5.1.8-1"
}
local mod = ::Hooks.register(def.ID, def.Version, def.Name);
mod.require("mod_rosetta >= 0.4.0");

::include("mod_rosetta_base_es/base_es");

// El juego instalado esta en ingles, asi que la autodeteccion de idioma
// de Rosetta (que mira strings ya traducidas) no aplica: activamos es.
::Rosetta.activate("es");
```

- [ ] **Step 2: Build completo**

```bash
cd /d/git/battle-brothers-rosetta
PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py
```
Esperado: línea `total: <TOTAL> dist: <DIST> wip: <WIP> drop: <DROP>` con DIST >= 10000 y WIP en el orden de 1400-1700, y línea `zip: ...`. Si DIST < 10000, PARAR y revisar Task 7.

- [ ] **Step 3: Verificar el layout del zip**

```bash
uv run python -c "
import zipfile
z = zipfile.ZipFile('es_pack/build/mod_rosetta_base_es_1.5.1.8-1.zip')
print('\n'.join(sorted(z.namelist())))
"
```
Esperado exactamente estas dos entradas:
```
mod_rosetta_base_es/base_es.nut
scripts/!mods_preload/mod_rosetta_base_es.nut
```

- [ ] **Step 4: Registrar números en STATS.md (añadir sección "Build v0.1.0" con DIST/WIP/DROP) y commit**

```bash
git add es_pack/src es_pack/corpus/STATS.md
git commit -m "es-pack: wrapper del mod y primer build v0.1.0

Pack como mod independiente segun el modelo oficial de upstream:
registro con Modern Hooks, require de mod_rosetta, include de pares
y activate(es) explicito (el juego instalado esta en ingles).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin es-pack
```

### Task 10: Instalación y verificación in-game (USER GATE)

**Interfaces:**
- Consumes: zip de Task 9.
- Produces: confirmación del usuario de que el pack carga y traduce; salida del log del juego sin errores de rosetta.

- [ ] **Step 1: Instalar el zip**

```bash
cp es_pack/build/mod_rosetta_base_es_1.5.1.8-1.zip "/d/GOG/Battle Brothers/data/"
ls "/d/GOG/Battle Brothers/data" | grep -i -E "rosetta|msu|hooks|stdlib"
```
Esperado: el zip nuevo más las dependencias (mod_rosetta 0.4.x, MSU, modern hooks, stdlib). Si falta mod_rosetta 0.4.x: descargarlo de NexusMods (mod 802) o construirlo desde master (`make zip` requiere make y zip; alternativa: avisar al usuario). Si el runtime instalado es el 0.2.0 parcheado del fork antiguo, SUSTITUIRLO: el pack requiere >= 0.4.0 y el guard del wrapper hará que sin él simplemente no cargue.

- [ ] **Step 2: (Usuario) Arrancar el juego y pasar este checklist**

1. El juego arranca sin crash y sin popup de error de Modern Hooks.
2. Menú de nueva campaña: los textos de ambiciones u orígenes aparecen en castellano (el menú principal en sí es JS y seguirá en inglés: esperado, se cubre en Fase 5).
3. En partida: tooltip de una habilidad o perk en castellano.
4. Abrir un evento o contrato: texto en castellano.
5. Ambición activa: "Tu tarea" / "Tu recompensa" visibles.
6. Strings nuevas o sin traducir se ven en inglés, NUNCA vacías ni con basura `<...>`.

- [ ] **Step 3: Revisar el log del juego**

```bash
grep -o 'rosetta: [^<]*' "/c/Users/hda/Documents/Battle Brothers/log.html" | sort | uniq -c | sort -rn | head -20
```
Esperado: una línea tipo `Adding <DIST> es pairs in vanilla`; ningún `ERROR`; los warnings `untranslated pair ... skipping` deben ser 0 (el build ya filtra vacíos).

- [ ] **Step 4: Si todo verde, tag y (opcional) release**

```bash
git tag es-pack-v0.1.0
git push origin es-pack-v0.1.0
gh release create es-pack-v0.1.0 es_pack/build/mod_rosetta_base_es_1.5.1.8-1.zip --repo backmind/battle-brothers-rosetta --title "Pack ES juego base v0.1.0 (literales)" --notes "Traduccion del juego base via Rosetta 0.4.0. Solo pares literales validados; los patrones llegan en v0.2.0." 2>/dev/null || echo "release opcional: crear a mano si gh no esta autenticado"
```

### Task 11: README del pack para usuarios finales

**Files:**
- Create: `es_pack/README.md`

- [ ] **Step 1: Escribir el README**

```markdown
# Battle Brothers en Castellano (pack Rosetta)

Traduccion del juego base (y DLCs) al castellano que NO modifica los
archivos del juego: sustituye los textos en caliente. Si el juego se
actualiza, la traduccion sigue funcionando y las frases nuevas se ven
en ingles hasta que se traduzcan.

## Instalacion

1. Instala en la carpeta `data` del juego, por este orden de descarga:
   - Modern Hooks (NexusMods)
   - MSU - Modding Standards & Utilities (NexusMods)
   - stdlib (NexusMods)
   - Rosetta Translations (NexusMods, mod 802), version 0.4.0 o superior
   - `mod_rosetta_base_es_<version>.zip` (este pack)
2. Arranca el juego. No hay que configurar nada.

## Que traduce y que no

- Traduce: eventos, contratos, tooltips, habilidades, perks, ambiciones
  y en general todo texto generado por los scripts del juego.
- No traduce (todavia): el menu principal y botones construidos en JS,
  y los rotulos del mapa que dibuja el motor. Ver hoja de ruta.

## Para desarrolladores

- Corpus canonico: `corpus/base_es.nut` (formato Rosetta; se regenera
  con `rosetta.py -r` sobre un arbol descompilado del juego).
- Build: `PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py`
- Los pares con placeholders sin tipar quedan en `build/patterns_wip.nut`
  hasta convertirlos a la sintaxis `<nombre:tipo>` (ver
  AGENTS_TRANSLATING.md de upstream).

## Creditos

Traduccion original de reemplazo: MagnusLioncaster, Hjensikk, AMarauder
y elgranfoca (NexusMods, "Battle Brothers - Traduccion completa al
Castellano"). Adaptacion a Rosetta: backmind. Framework Rosetta: Suor.
```

- [ ] **Step 2: Commit y push**

```bash
git add es_pack/README.md
git commit -m "es-pack: README de instalacion y creditos

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin es-pack
```

---

# FASE 4: PATRONES (v0.2.0)

### Task 12: Inventario de la cuarentena

**Files:**
- Create: `es_pack/corpus/PATTERNS_TODO.md`

**Interfaces:**
- Consumes: `es_pack/build/patterns_wip.nut` (regenerable con build_dist).
- Produces: inventario por dominio para atacar la conversión en lotes.

- [ ] **Step 1: Generar el inventario**

```bash
PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py
PYTHONUTF8=1 uv run python -c "
import re, collections
from pathlib import Path
txt = Path('es_pack/build/patterns_wip.nut').read_text(encoding='utf-8')
ens = re.findall(r'\ben = (\"(?:[^\"\\\\]|\\\\.)*\")', txt)
kinds = collections.Counter()
for e in ens:
    if '%SPEECH' in e or '%companyname%' in e: kinds['texto con %marcadores% (probable literal)'] += 1
    elif '[color=<' in e: kinds['color BBCode con valor dinamico'] += 1
    elif '<this.' in e: kinds['expresion squirrel cruda'] += 1
    elif '<ret>' in e: kinds['concatenacion con <ret>'] += 1
    else: kinds['otros'] += 1
print(len(ens), 'pares en cuarentena'); [print(f'{v:6} {k}') for k, v in kinds.most_common()]
"
```

- [ ] **Step 2: Escribir PATTERNS_TODO.md con esos números y el procedimiento de conversión**

Procedimiento por lote (documentarlo tal cual en el fichero):
1. Elegir un lote de 30-50 pares de la misma categoría en `patterns_wip.nut`.
2. Convertirlos EDITANDO `es_pack/corpus/base_es.nut` (el corpus es el canónico; la cuarentena es solo un informe generado) siguiendo `AGENTS_TRANSLATING.md` de upstream (está en la raíz del repo desde la sincronización con master). Reglas clave:
   - `[color=<this.Const...>]50%[/color]` -> `en = "... <x:val_tag> ..."` y en es `<x>`.
   - `<this.Const.Strings.getArticle(...) + item.getName()>` -> `<item:str_tag>` o `<item:str>` segun el caso; en es `<item>` o `<item:t>` si el contenido se traduce por separado.
   - Los pares cuyo texto solo tiene `%marcadores%` y ningún `<...>` real suelen poder pasar a literales: quitarles el `mode = "pattern"`.
   - Los pares con `<ret>` (concatenaciones parciales) casi nunca son salvables como patrón: valorar borrarlos del corpus (la string completa ya se captura en otro par).
3. Rebuild y comprobar que el lote migró de cuarentena a dist:
   ```bash
   PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py
   ```
   (dist sube, wip baja exactamente en el tamaño del lote salvo los borrados).
4. Cada 3-4 lotes: instalar el zip y comprobar in-game una string del lote, más el log sin errores.
5. Commit por lote: `es-pack: patrones lote N (<categoria>), -X wip / +Y dist`.

- [ ] **Step 3: Criterio de cierre de la fase**

Cuarentena por debajo de 100 pares (los irreducibles se documentan en PATTERNS_TODO.md con el motivo). Entonces: bump de `PACK_VERSION` a `"1.5.1.8-2"` en `build_dist.py` y en el wrapper `Version`, rebuild, verificación in-game (checklist de Task 10), tag `es-pack-v0.2.0`.

---

# FASE 5: SEGUIMIENTO (tareas independientes, cada una con su decisión)

### Task 13: Bump a la versión actual del juego

El juego ha recibido parches desde 1.5.1.8 (junio 2026). El pack v0.1.0 seguirá funcionando en la versión actual (esa es la gracia de Rosetta); este task solo maximiza cobertura.

- [ ] Descompilar la versión actual con la herramienta de Adam Milazzo (bbros.zip, ya usada por el usuario para el árbol 1.5.1.8) a un directorio nuevo `comparer/original_<version>/`.
- [ ] Regenerar: `PYTHONUTF8=1 uv run python rosetta.py "<nuevo_arbol>/scripts" -les -r es_pack/corpus/base_es.nut > es_pack/corpus/base_es_new.nut`, revisar stats, y si TRADUCIDOS no cae más de un 2%, reemplazar el corpus con el nuevo fichero.
- [ ] Actualizar `GAME_VERSION` en `build_dist.py` y `Version` en el wrapper, rebuild, checklist in-game, tag.

### Task 14: Pieza JS (menú y UI construida en JavaScript)

Insumo previo (USER, ya resuelto 2026-08-15): la última versión descargada está en `D:\GOG\Battle Brothers\!Downloads\Traduccion castellano Battle Brothers 640 3.0.5.02082026 2026-08-02T04-14Z s6dELHgGQ.zip`. No se commitea: es trabajo de terceros y el permiso se gestiona en Task 15. Sirve para esta task (carpeta js) y para el re-bootstrap de Task 13/15.

AVISO IMPORTANTE para el re-bootstrap (Task 13/15): el corpus rescatado NO salió de esta 3.0.5 sino de una versión anterior a la que el usuario aplicó ETL considerable (corrección de UTF corrupto y compatibilidad Rosetta; hay detalles en sus comentarios de NexusMods). La 3.0.5 es cruda: cualquier string que se importe de ella necesita pasar por la misma limpieza UTF, y sus traducciones solo deben RELLENAR huecos (strings sin traducir en el corpus), nunca sobreescribir pares ya curados.

- [ ] Localizar el `.dat` con la carpeta `js` traducida que el usuario ya creó (mencionado en Nexus como `zdata_011_es`): `es -r "zdata.*es" | head` y `es -r "\.dat$" bbros | head` (Everything CLI). Si aparece: archivarlo en la rama `legacy-es-pipeline` (`git add -f`) y documentar en `es_pack/README.md` cómo instalarlo como descarga aparte.
- [ ] Si no aparece: regenerarlo empaquetando la carpeta `ui/` (js) de la descarga de elgranfoca en un zip que solo contenga `ui/...`.
- [ ] Seguir `docs/js-plan.md` de upstream: cuando Rosetta soporte strings JS, migrar esos textos a pares y retirar el .dat.

### Task 15: Contacto con upstream y con los traductores (USER, borradores preparados)

- [ ] Issue en Suor/battle-brothers-rosetta: contar el caso de uso (traducción del juego base ES funcionando sobre 0.4.0 sin tocar el runtime), ofrecer la experiencia del bootstrap (create_po.py alineando árbol EN contra traducción de reemplazo, exactamente el `docs/old-plan.md` de upstream con su modo `-o`), y preguntar si aceptaría PRs en esa dirección. Beneficio: cuando `-o` exista upstream, se retira normalize_seed y cualquier resto del pipeline propio.
- [ ] Mensaje a elgranfoca en Nexus: enseñar el pack, pedir su bendición y créditos formales, y proponer re-bootstrap desde su traducción 3.0.5 (más completa que el corpus 1.5.1.7/1.5.1.8): mismo procedimiento de Task 13 pero usando su árbol descompilado como referencia adicional. Él ya dijo públicamente que le gustaría que esto acabara en Rosetta.

### Task 16: Colaboración abierta (posponer hasta que haya colaboradores)

Decisión de backend (2026-08-15, acordada con el usuario): git es la única base de datos.

- Fuente de verdad: `es_pack/corpus/base_es.nut` en git. Estado implícito: `es = ""` es pendiente; mergeado por PR es revisado. No se mantiene SQLite ni web UI propia (quedan archivadas en `legacy-es-pipeline`).
- Versionado del juego: regeneración con `-r` por parche; el `git diff` del corpus es el informe de cambios (nuevas con `es = ""`, eliminadas desaparecen del corpus pero quedan en el historial, modificadas aparecen como nuevas). Versionado del pack: tags `<version_juego>-<n>`.
- Niveles de colaboración, activar solo el que toque:
  1. Solo o colaboradores con git: editar el corpus y PRs en GitHub. La revisión de PR es el flujo de QA. Cero infraestructura.
  2. Colaboradores no técnicos: Weblate hosted (gratis para proyectos libres) con puente PO.
  3. Opcional: GitHub Action que corre build_dist en cada PR y comenta dist/wip/drop.

- [ ] Cuando haya 2+ personas traduciendo: escribir el puente PO (~60 líneas: export corpus -> PO con polib reutilizando load_ref, e import PO -> corpus; msgid = en, msgstr = es) y montar el proyecto en hosted.weblate.org apuntando a la rama es-pack con commit de vuelta al repo. Hasta entonces, el flujo es editar `corpus/base_es.nut` directamente (el formato Rosetta es legible y AGENTS_TRANSLATING.md lo documenta).
- [ ] (Opcional) Memoria de traducción: si en un bump de versión desaparecen pares traducidos del corpus, volcarlos a `es_pack/corpus/tm_es.nut` y concatenarlo al ref en futuras regeneraciones, para que una string que reaparezca recupere su traducción sin buscar en el historial.
- [ ] Decidir si `es_pack/` se muda a repo propio (`backmind/battle-brothers-es`). Criterio: hacerlo cuando el pack tenga releases estables y usuarios; mientras tanto la rama del fork es más simple.

---

## Autochequeo del plan (hecho al escribirlo)

- Cobertura de la evaluación: rescate (T1-2), sincronización (T3-4), des-forkeo sin tocar runtime (T4, T9, constraint global), regeneración con extractor 0.4.0 (T6-7), patrones muertos (filtro T8 + conversión T12), verificación in-game (T10), JS/mapa (T14 y Contexto), upstream y elgranfoca (T15), Weblate (T16).
- Riesgos con contingencia explícita: load_ref no parsea el seed (T6 Step 3), caída de traducidos tras regenerar (T7 Step 2), falta mod_rosetta 0.4.0 instalado (T10 Step 1).
- Números baseline verificados hoy contra el repo real: 13.804 / 1.683 / 1.476 / 16.169 / 12.428.
