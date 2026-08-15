"""Re-codifica caracteres problematicos en un fichero de formato rosetta
para que siga siendo consumible como referencia (-r) por rosetta.py 0.4.0:

- \\" dentro de valores -> \\x22 (el tokenizador de en trunca en la primera
  comilla, escapada o no)
- { y } dentro de valores en/es/nN -> \\x7b / \\x7d (las llaves sueltas
  desincronizan el contador de bloques de load_ref)

Solo se tocan lineas de asignacion de valores; los comentarios // _code se
dejan intactos para que sus claves de matching no cambien entre ciclos.
Idempotente.
"""
import re
import sys
from pathlib import Path

ESCAPED_QUOTE_RE = re.compile(r'(?<!\\)((?:\\\\)*)\\"')
VALUE_LINE_RE = re.compile(r'^(\s*(?:en|es|n\d+)\s*=\s*)("(?:[^"\\]|\\.)*")(,?\s*)$', re.M)


def _encode_braces(m):
    return m.group(1) + m.group(2).replace("{", "\\x7b").replace("}", "\\x7d") + m.group(3)


def fix(text):
    text = ESCAPED_QUOTE_RE.sub(r'\1\\x22', text)
    return VALUE_LINE_RE.sub(_encode_braces, text)


def main():
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    quotes = len(ESCAPED_QUOTE_RE.findall(text))
    fixed = fix(text)
    braces = fixed.count("\\x7b") + fixed.count("\\x7d") - (text.count("\\x7b") + text.count("\\x7d"))
    path.write_text(fixed, encoding="utf-8")
    print("comillas re-codificadas:", quotes)
    print("llaves re-codificadas:", braces)


if __name__ == "__main__":
    main()
