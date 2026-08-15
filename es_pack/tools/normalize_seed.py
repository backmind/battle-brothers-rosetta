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
