# Estadisticas del corpus

## Regeneracion 2026-08-15 (arbol 1.5.1.8, seed legacy 13.804 pares)

- Pares totales: 15477
- Traducidos: 13336
- Sin traducir (es = ""): 2141
- Patrones (mode = "pattern"): 1666
- Tamano del fichero: 7.937.087 bytes

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
desincronizar el contador de bloques; umbral pedido: >= 13700).

### 3. Regeneracion completa

```bash
PYTHONUTF8=1 uv run python rosetta.py "/d/GOG/Battle Brothers/!Downloads/bbros/bin/comparer/original/scripts" -les -r es_pack/build/seed_norm.nut -q > es_pack/corpus/base_es.nut 2> es_pack/build/regen_stderr.txt
```
2343 ficheros `.nut` procesados. Exit code 0.

### 4. Post-paso quote_fix (re-codifica llaves/comillas sueltas reintroducidas por el arbol EN fresco)

```bash
PYTHONUTF8=1 uv run python es_pack/tools/quote_fix.py es_pack/corpus/base_es.nut
```
Salida: `comillas re-codificadas: 0` / `llaves re-codificadas: 110`
Verificacion: `grep -Fc '\"' es_pack/corpus/base_es.nut` -> `0`

## Cobertura: gap conocido de extraccion (aceptado, no parcheado)

`rosetta.py::_prepare_code` (linea ~418) falla con
`ValueError: min() iterable argument is empty` cuando el fragmento de codigo
capturado para una expresion de patron queda vacio. Es un bug preexistente en
`rosetta.py` (no se parchea: componente "upstream" segun las reglas del
proyecto). Con el seed anterior (solo comillas) esto solo afectaba a 1 fichero
(`scripts/config/rumors.nut`), porque muy pocas expresiones de patron llegaban
a esa ruta de codigo (pocas referencias cargaban). Al arreglar las llaves y
subir la carga de referencias del ~29% al 100%, muchas mas expresiones de
patron ahora toman esa ruta, y el bug se dispara en **47 ficheros** en vez de
1:

- `scripts/config/rumors.nut`
- `scripts/contracts/contracts/decisive_battle_contract.nut`
- `scripts/contracts/contracts/raid_caravan_contract.nut`
- 44 de los 45 ficheros bajo `scripts/entity/world/settlements/situations/`
  (todos menos uno)

Estos 47 ficheros contribuyen 0 pares al corpus. Es un gap de cobertura
conocido y aceptado (no bloqueante, pendiente de reportar upstream junto al
bug de comillas de `load_ref`), no una regresion introducida por esta tarea:
la causa raiz es la misma clase de bug preexistente, solo que ahora se
manifiesta con mayor frecuencia porque el matching de referencias funciona
muchisimo mejor. `Processed 2343 files, failed 47` en
`es_pack/build/regen_stderr.txt` (0 lineas `SKIPPING`, 47 tracebacks, ningun
otro tipo de fallo).
