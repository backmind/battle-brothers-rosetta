"""Re-codifica \\" como \\x22 en un fichero de formato rosetta.

El tokenizador de referencias de rosetta.py 0.4.0 trunca los tokens
en = "..." en la primera comilla, aunque este escapada como \\". Este
filtro se aplica al corpus tras cada regeneracion para que siga siendo
consumible como referencia (-r) en el futuro. Idempotente.
"""
import re
import sys
from pathlib import Path

ESCAPED_QUOTE_RE = re.compile(r'(?<!\\)((?:\\\\)*)\\"')


def fix(text):
    return ESCAPED_QUOTE_RE.sub(r'\1\\x22', text)


def main():
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    n = len(ESCAPED_QUOTE_RE.findall(text))
    path.write_text(fix(text), encoding="utf-8")
    print("comillas re-codificadas:", n)


if __name__ == "__main__":
    main()
