"""Convierte el base_es.nut del compilador legacy a bloques minimos que
load_ref (rosetta.py 0.4.0) parsea seguro.

Ademas re-codifica las comillas dobles internas como \\x22: el tokenizador
de referencias de upstream ("[^"]+") no es consciente de escapes y trunca
en la primera comilla, aunque este escapada. \\x22 es valido en Python
(ast.literal_eval) y en el lexer de Squirrel, y evita el problema de raiz.
"""
import ast
import re
import sys
from pathlib import Path

PAIR_RE = re.compile(
    r'\{\s*(?P<mode>mode = "pattern"\s*)?'
    r'en = (?P<en>"(?:[^"\\]|\\.)*")\s*'
    r'es = (?P<es>"(?:[^"\\]|\\.)*")\s*\}',
    re.S,
)


def sq(s):
    out = (s.replace("\\", "\\\\")
            .replace('"', "\\x22")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t"))
    return '"' + out + '"'


def main():
    src = Path(sys.argv[1]).read_text(encoding="utf-8")
    out = ['if (!("Rosetta" in getroottable())) return;\n',
           'local rosetta = {\n    mod = {id = "vanilla", version = "1.5.1.8"}\n'
           '    author = "seed"\n    lang = "es"\n}\nlocal pairs = [\n']
    n = 0
    for m in PAIR_RE.finditer(src):
        mode = '        mode = "pattern"\n' if m.group("mode") else ""
        en = sq(ast.literal_eval(m.group("en")))
        es = sq(ast.literal_eval(m.group("es")))
        out.append("    {\n%s        en = %s\n        es = %s\n    }\n" % (mode, en, es))
        n += 1
    out.append("]\n::Rosetta.add(rosetta, pairs);\n")
    Path(sys.argv[2]).write_text("".join(out), encoding="utf-8")
    print("pares:", n)


if __name__ == "__main__":
    main()
