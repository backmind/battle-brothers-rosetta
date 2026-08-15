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
