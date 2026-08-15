"""Genera la version distribuible del pack ES a partir del corpus.

Uso:  PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py

Lee   es_pack/corpus/base_es.nut  (corpus completo)
Escribe:
  es_pack/build/mod_rosetta_base_es/base_es.nut          pares validos
  es_pack/build/patterns_wip.nut                         cuarentena (Fase 4)
  es_pack/build/scripts/!mods_preload/mod_rosetta_base_es.nut
  es_pack/build/mod_rosetta_base_es_<version>.zip

Reglas de clasificacion por par (contrato real de validateRule en
scripts/!mods_preload/!rosetta.nut):
  drop  sin traduccion (es = "")
  wip   algun placeholder <...> que no cumpla <nombre:tipo> en en o
        <nombre[:flag]> en es; o un tipo de sub no soportado (subRes);
        o dos <...:str> adyacentes en en; o una label en es que no
        existe en en (el runtime 0.4.0 haria throw al cargar el pack)
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

GAME_VERSION = "1.5.2.3"
PACK_VERSION = GAME_VERSION + "-1"

STR_RE = r'"(?:[^"\\]|\\.)*"'
EN_PLACE_RE = re.compile(r"^<\w+:\w+>$")
ES_PLACE_RE = re.compile(r"^<\w+(:\w+)?>$")

# Tipos de sub soportados por subRes en scripts/!mods_preload/!rosetta.nut
# (validateRule lanza "Label type '%s' is not supported" para cualquier otro).
SUBS = {"int", "val", "word", "str", "line", "tag", "img",
        "int_tag", "val_tag", "str_tag"}

# El corpus codifica caracteres problematicos como \x22 ("), \x7b ({) y
# \x7d (}) dentro de los strings de valor, para que el load_ref de upstream
# pueda re-consumirlos. El escape \xNN de Squirrel es ambiguo en longitud en
# builds UNICODE, asi que la salida de distribucion decodifica de vuelta a
# caracteres literales (evitando depender de que Squirrel interprete \xNN).
DEC_RE = re.compile(r'(?<!\\)((?:\\\\)*)\\x(22|7b|7d)')
_DEC = {"22": '\\"', "7b": "{", "7d": "}"}


def decode_hex_escapes(text):
    return DEC_RE.sub(lambda m: m.group(1) + _DEC[m.group(2)], text)


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
    en_labels = dict(re.findall(r"<(\w+):(\w+)>", en))
    ok_en = (all(EN_PLACE_RE.match(p) for p in ph_en)
             and all(t in SUBS for t in en_labels.values())
             and not re.search(r"<\w+:str><\w+:str>", en))
    ok_es = (all(ES_PLACE_RE.match(p) for p in ph_es)
             and all(m.group(1) in en_labels
                     for m in re.finditer(r"<(\w+)(?::\w+)?>", es)))
    return "dist" if ok_en and ok_es else "wip"


def emit(path, blocks):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        "    " + decode_hex_escapes(b).strip().replace("\n", "\n    ")
        for b in blocks
    )
    path.write_text(HEADER + body + "\n" + FOOTER, encoding="utf-8")


WIP_HEADER = (
    "// CUARENTENA: pares con placeholders invalidos; NO cargar en el "
    "juego. Editar el corpus, no este fichero.\n"
)


def emit_wip(path, blocks):
    """Igual que emit() pero SIN header/footer de ::Rosetta.add: este
    fichero es solo para revision humana y nunca debe ser cargable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(decode_hex_escapes(b).strip() for b in blocks)
    path.write_text(WIP_HEADER + body + "\n", encoding="utf-8")


def main():
    blocks = load_blocks(CORPUS)
    print("dups omitidos (en identico): %d" % len(rosetta.DUP_BLOCKS))
    buckets = {"dist": [], "wip": [], "drop": []}
    for b in blocks:
        buckets[classify(b)].append(b)
    print("total: %d  dist: %d  wip: %d  drop: %d" % (
        len(blocks), len(buckets["dist"]), len(buckets["wip"]),
        len(buckets["drop"])))

    pairs_rel = Path("mod_rosetta_base_es/base_es.nut")
    wrapper_rel = Path("scripts/!mods_preload/mod_rosetta_base_es.nut")

    emit(BUILD / pairs_rel, buckets["dist"])
    emit_wip(BUILD / "patterns_wip.nut", buckets["wip"])
    (BUILD / wrapper_rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / wrapper_rel, BUILD / wrapper_rel)

    zip_path = BUILD / ("mod_rosetta_base_es_%s.zip" % PACK_VERSION)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(BUILD / wrapper_rel, wrapper_rel.as_posix())
        z.write(BUILD / pairs_rel, pairs_rel.as_posix())
    print("zip:", zip_path)


if __name__ == "__main__":
    main()
