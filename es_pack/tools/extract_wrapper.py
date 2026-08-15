"""Lanzador de rosetta.py con workaround para un bug upstream:
_prepare_code(code) crashea con min() sobre lista vacia cuando un bloque
de referencia se refresca con _code vacio, y el fichero entero pierde la
extraccion. Aqui se parchea en memoria (el fichero upstream no se toca);
el bug se reportara upstream. Uso identico a rosetta.py:

    PYTHONUTF8=1 uv run python es_pack/tools/extract_wrapper.py <dir> -les -r <ref> -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import rosetta

_orig_prepare_code = rosetta._prepare_code


def _safe_prepare_code(code):
    if not code:
        return ""
    return _orig_prepare_code(code)


rosetta._prepare_code = _safe_prepare_code

if __name__ == "__main__":
    rosetta.main()
