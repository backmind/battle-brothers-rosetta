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


FIXTURE2 = '''if (!("Rosetta" in getroottable())) return;

local rosetta = {
    mod = {id = "vanilla", version = "0.0.0"}
    author = "test"
    lang = "es"
}
local pairs = [
    {
        en = "Alpha"
        es = "Alfa"
    }
    {
        en = "Beta"
        es = "Beta"
    }
    {
        en = "Gamma"
        es = "Gama"
    }
]
::Rosetta.add(rosetta, pairs);
'''


def test_load_blocks_is_repeatable(tmp_path):
    # Dos ficheros DISTINTOS: si los globals de rosetta no se limpiaran
    # entre cargas, la segunda carga arrastraria los bloques de la
    # primera (en distintos, sin dedup por REF_BLOCKS[en]) y el conteo
    # no seria el propio del segundo fichero (3).
    f1 = tmp_path / "fixture_es.nut"
    f1.write_text(FIXTURE, encoding="utf-8")
    f2 = tmp_path / "fixture2_es.nut"
    f2.write_text(FIXTURE2, encoding="utf-8")
    assert len(load_blocks(f1)) == 4
    assert len(load_blocks(f2)) == 3


def test_get_field_unescapes():
    block = '{\n en = "a\\nb"\n es = "c \\"d\\""\n}'
    assert get_field(block, "en") == "a\nb"
    assert get_field(block, "es") == 'c "d"'


def test_emit_decodes_hex_escapes(tmp_path):
    from build_dist import emit
    block = ('{\n        en = "He said \\x22hi\\x22 \\x7bA|B\\x7d"\n'
             '        es = "Dijo \\x22hola\\x22 \\x7bA|B\\x7d"\n    }')
    out = tmp_path / "o.nut"
    emit(out, [block])
    text = out.read_text(encoding="utf-8")
    assert "\\x22" not in text and "\\x7b" not in text and "\\x7d" not in text
    assert '\\"hi\\"' in text and "{A|B}" in text


def test_decode_preserves_literal_backslash_x22():
    from build_dist import decode_hex_escapes
    assert decode_hex_escapes(r'"a\\x22"') == r'"a\\x22"'
    assert decode_hex_escapes(r'"a\x22"') == r'"a\""'


# --- F1: contrato real del runtime (validateRule en !rosetta.nut) ---

def test_classify_valid_typed_pattern_is_dist():
    block = ('{\n mode = "pattern"\n'
             ' en = "Has a range of <range:int> tiles"\n'
             ' es = "Tiene un alcance de <range> casillas"\n}')
    assert classify(block) == "dist"


def test_classify_es_label_renamed_is_wip():
    # Shape valida en ambos lados, pero la label de es no existe en en
    # (validateRule: "Label '%s' is in '%s' but not in 'en'").
    block = ('{\n mode = "pattern"\n'
             ' en = "Has a range of <range:int> tiles"\n'
             ' es = "Tiene un alcance de <alcance> casillas"\n}')
    assert classify(block) == "wip"


def test_classify_es_placeholder_without_en_is_wip():
    # en sin placeholders, es con uno: la label no puede existir en en
    # (labels vacio) y antes llegaba a dist, abortando el pack entero.
    block = '{\n en = "Your Task"\n es = "Tu <tarea>"\n}'
    assert classify(block) == "wip"


def test_classify_unsupported_sub_type_is_wip():
    # "integer" no esta en SUBS/subRes -> validateRule lanzaria
    # "Label type 'integer' is not supported".
    block = ('{\n mode = "pattern"\n'
             ' en = "Has <x:integer> value"\n'
             ' es = "Tiene <x> valor"\n}')
    assert classify(block) == "wip"


def test_classify_adjacent_str_placeholders_is_wip():
    # validateRule: "Two :str next to each other not allowed".
    block = ('{\n mode = "pattern"\n'
             ' en = "<a:str><b:str>"\n'
             ' es = "<a><b>"\n}')
    assert classify(block) == "wip"


# --- F4: cuarentena no debe ser un pack cargable ---

def test_emit_wip_has_no_rosetta_add(tmp_path):
    from build_dist import emit_wip
    block = '{\n en = "Foo"\n es = "Bar"\n}'
    out = tmp_path / "patterns_wip.nut"
    emit_wip(out, [block])
    text = out.read_text(encoding="utf-8")
    assert "::Rosetta.add" not in text
    assert "CUARENTENA" in text
    assert "Foo" in text and "Bar" in text


def test_classify_rejects_duplicate_captures():
    from build_dist import classify
    block = ('{\n        mode = "pattern"\n'
             '        en = "Level up <goal:int> times (<progress:int>/<goal:int>)"\n'
             '        es = "Sube <goal> veces (<progress>/<goal>)"\n    }')
    assert classify(block) == "wip"
