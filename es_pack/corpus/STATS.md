# Estadisticas del corpus

## Regeneracion 2026-08-15 (arbol 1.5.1.8, seed legacy 13.804 pares)

- Pares totales: 16031
- Traducidos: 13881
- Sin traducir (es = ""): 2150
- Patrones (mode = "pattern"): 1825
- Tamano del fichero: 8.313.781 bytes

Historial de esta misma regeneracion (mismo seed, mismo arbol EN), a medida
que se identificaron y arreglaron bugs de la cadena de herramientas:
ronda 1 (solo comillas re-codificadas, carga de refs ~29%): 16795 pares totales,
5097 traducidos. Ronda 2 (llaves re-codificadas ademas de comillas, carga de
refs 100%, pero 47 ficheros perdidos por crash de extraccion): 15477 pares
totales, 13336 traducidos. Ronda 3 (esta; wrapper recupera los 47 ficheros):
16031 pares totales, 13881 traducidos.

## Comandos reales usados

### 1. Normalizacion del seed (con codificacion de llaves)

`es_pack/tools/normalize_seed.py` se extendio para re-codificar tambien `{`/`}`
como `\x7b`/`\x7d` ademas de las comillas (`\x22`) ya existentes: las llaves
sueltas dentro de un valor `es = "..."` desincronizan el contador de bloques
de `load_ref` (no hay rama de tokenizador dedicada para `es`, cae al catch-all
`other` que excluye `{`/`}`). Esto se detecto durante la regeneracion inicial
de esta misma tarea: con el seed anterior (solo comillas re-codificadas)
`load_ref` solo registraba 3980/13804 bloques (~29%); con el fix de llaves
registra los 13804/13804.

```bash
PYTHONUTF8=1 uv run python es_pack/tools/normalize_seed.py es_pack/build/seed_base_es.nut es_pack/build/seed_norm.nut
```
Salida: `pares: 13804`

### 2. Pre-chequeo agregado de carga de referencias (antes de la regeneracion completa)

```bash
PYTHONUTF8=1 uv run python -c "import rosetta; rosetta.OPTS['lang']='es'; rosetta.OPTS['quiet']=True; rosetta.load_ref('es_pack/build/seed_norm.nut'); print('REF_BLOCKS:', len(rosetta.REF_BLOCKS))"
```
Resultado: `REF_BLOCKS: 13804` (100% de los 13804 pares del seed cargan sin
desincronizar el contador de bloques; umbral pedido: >= 13700). No hizo falta
repetir este chequeo en la ronda 3: el seed no cambio, solo el extractor.

### 3. Regeneracion completa, vía `extract_wrapper.py`

`rosetta.py::_prepare_code` (linea ~418) crashea con
`ValueError: min() iterable argument is empty` cuando el fragmento `_code`
capturado para refrescar un bloque de referencia queda vacio
(`_refresh_code` -> `_prepare_code(code)` con `code == []`). Con la carga de
referencias al 100% (fix de llaves), muchas mas expresiones de patron toman
esa ruta de codigo y el bug tumbaba la extraccion completa de **47 ficheros**
(`scripts/config/rumors.nut`, 2 ficheros de contratos, y 44 de los 45 bajo
`scripts/entity/world/settlements/situations/`), perdiendo toda su categoria
de contenido.

Se creo `es_pack/tools/extract_wrapper.py`, que parchea `rosetta._prepare_code`
en memoria (sin tocar `rosetta.py`, componente upstream) para devolver cadena
vacia cuando `code` esta vacio, en vez de crashear, y luego invoca
`rosetta.main()` normalmente. Bug pendiente de reportar upstream.

```bash
PYTHONUTF8=1 uv run python es_pack/tools/extract_wrapper.py "/d/GOG/Battle Brothers/!Downloads/bbros/bin/comparer/original/scripts" -les -r es_pack/build/seed_norm.nut -q > es_pack/corpus/base_es.nut 2> es_pack/build/regen_stderr.txt
```
2343 ficheros `.nut` procesados. Exit code 0. `es_pack/build/regen_stderr.txt`
contiene una unica linea: `Processed 2343 files` (sin sufijo `failed N`, 0
tracebacks, 0 lineas `SKIPPING`) — los 47 ficheros ya no fallan.

Verificacion de recuperacion: los 44 ficheros `*_situation.nut` que fallaban
en la ronda 2 aparecen ahora como comentarios `FILE:` en el corpus (44/44),
igual que `rumors.nut` y los 2 ficheros de contratos.

### 4. Post-paso quote_fix (re-codifica llaves/comillas sueltas reintroducidas por el arbol EN fresco)

```bash
PYTHONUTF8=1 uv run python es_pack/tools/quote_fix.py es_pack/corpus/base_es.nut
```
Salida: `comillas re-codificadas: 0` / `llaves re-codificadas: 110`
Verificacion: `grep -Fc '\"' es_pack/corpus/base_es.nut` -> `0`

## Cobertura: gap de extraccion arreglado (workaround en memoria, no upstream)

Ver seccion 3 arriba. El gap de 47 ficheros (categoria completa de
`situations` de asentamientos + `rumors.nut` + 2 contratos) que existia en la
ronda 2 esta ahora recuperado via `extract_wrapper.py`. El bug de origen sigue
siendo de `rosetta.py` (upstream, no parcheado en el fichero); el workaround
vive enteramente en `es_pack/tools/extract_wrapper.py` como monkeypatch en
memoria, y debe usarse en toda regeneracion futura hasta que se resuelva
upstream.
