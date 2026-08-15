# Inventario de la cuarentena de patrones

Este documento es el inventario de `es_pack/build/patterns_wip.nut` (la
"cuarentena") y el procedimiento para vaciarla en lotes. Es un informe de
lectura; la conversion real de cada lote es trabajo de seguimiento, fuera del
alcance de esta tarea.

`patterns_wip.nut` no se versiona (`es_pack/build/` esta en `.gitignore`); se
regenera siempre a partir del corpus con:

```bash
PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py
```

Al regenerar (2026-08-15, HEAD `0b0cba9`): `total: 15432  dist: 12325  wip: 957  drop: 2150`.


## Por que existe la cuarentena

`classify()` en `es_pack/tools/build_dist.py` aplica el contrato real de
`validateRule` en `scripts/!mods_preload/!rosetta.nut`: los tipos de
sub-etiqueta soportados en tiempo de ejecucion son exactamente

```
int, val, word, str, line, tag, img, int_tag, val_tag, str_tag
```

Un par pasa a `dist` solo si:
- cada placeholder `<...>` en `en` tiene la forma `<nombre:tipo>` con `tipo`
  en la lista de arriba;
- no hay dos `<...:str>` adyacentes en `en` (el runtime no podria decidir
  donde termina uno y empieza el otro);
- cada placeholder `<...>` en `es` (con o sin `:t`) referencia una etiqueta
  que existe en `en`.

Si alguna de estas condiciones falla, el par cae en `wip` (cuarentena): no se
carga en el juego (el wrapper generado para `wip` no lleva `::Rosetta.add`,
solo un comentario de aviso), pero tampoco se pierde: sigue integro en el
corpus (`es_pack/corpus/base_es.nut`), listo para ser corregido.

**Esto implica que la validacion por lote es automatica**: un par convertido
correctamente pasa de `wip` a `dist` solo con volver a correr
`build_dist.py`. No hace falta un checker aparte; el propio rebuild dice si
el lote quedo bien (sube `dist`, baja `wip`) o si sigue mal (se queda en
`wip`, o revienta el `load_ref` de upstream, senal de un error de sintaxis
mas grave en el bloque).


## Categorias (salida real del script de categorizacion)

Script ejecutado tal cual sobre `patterns_wip.nut` regenerado en HEAD
`0b0cba9` (2026-08-15):

```
957 pares en cuarentena
   509 color BBCode con valor dinamico
   232 expresion squirrel cruda
   198 otros
    18 concatenacion con <ret>
```

| Categoria | Pares | % |
|---|---:|---:|
| color BBCode con valor dinamico | 509 | 53.2% |
| expresion squirrel cruda | 232 | 24.2% |
| otros | 198 | 20.7% |
| concatenacion con `<ret>` | 18 | 1.9% |
| **Total** | **957** | **100%** |

Notas sobre las categorias:
- "color BBCode con valor dinamico" (`[color=<...>]`) son en su mayoria el
  patron de "colorizar un valor" descrito en `AGENTS_TRANSLATING.md`
  (`:val_tag`, `:int_tag`, `:str_tag` segun el contenido); es el lote de
  mayor volumen y el mas mecanico de convertir.
- "expresion squirrel cruda" (`<this....>`) son placeholders que el
  extractor volco literalmente desde el codigo fuente (nombres de variable,
  llamadas a metodo); requieren decidir el tipo de captura correcto caso por
  caso.
- "otros" es la categoria residual del script (no matchea ninguna de las
  otras tres); incluye mezclas y casos que necesitan inspeccion individual
  antes de sub-clasificar.
- "concatenacion con `<ret>`" son restos de una concatenacion parcial
  (`local ret = ... + ...`); ver la nota de borrado en el procedimiento de
  abajo.

Ningun par de la cuarentena cayo en la categoria "texto con %marcadores%
(probable literal)" del script (0 pares): el corpus ya no tiene en la
cuarentena entradas que sean simplemente literales con `%marcadores%` sueltos
sin ningun `<...>` real (o bien ya se convirtieron, o bien coexisten con otro
patron real de la lista de arriba y cayeron en otra categoria).


## Desglose por dominio (aproximado)

`patterns_wip.nut` no lleva comentarios `// FILE: ...` (se generan solo en el
corpus completo; el fichero de cuarentena es un informe minimo, sin
metadatos de origen). Para atribuir dominio se hizo un cruce best-effort:
para cada texto `en` de los 957 pares en cuarentena, se busco ese mismo texto
`en` en `es_pack/corpus/base_es.nut` y se tomo el `// FILE: ...` mas cercano
anterior a el; el dominio es el primer directorio bajo `scripts/` en esa
ruta.

Resultado: los 957 pares tuvieron un match exacto de texto en el corpus (0
sin match). Aun asi el numero es aproximado: si un mismo texto `en` aparece
en mas de un fichero del corpus, se usa la primera ocurrencia encontrada, que
puede no ser el fichero real de origen del par en cuarentena.

| Dominio (`scripts/<dominio>/...`) | Pares |
|---|---:|
| skills | 355 |
| events | 204 |
| items | 93 |
| entity | 62 |
| ui | 55 |
| ambitions | 53 |
| contracts | 52 |
| config | 50 |
| retinue | 14 |
| states | 12 |
| scenarios | 4 |
| factions | 3 |
| **Total** | **957** |

(Son 12 dominios en total, todos listados: no llegan a 15.)

`skills` y `events` concentran mas de la mitad de la cuarentena (559/957,
58.4%); son buenos candidatos para los primeros lotes porque su volumen
permite agrupar por categoria tecnica (BBCode, expresion cruda, etc.) dentro
de un mismo dominio y revisar in-game con un numero razonable de pruebas
manuales.


## Procedimiento de conversion por lotes

Este es el procedimiento a seguir en las tareas de seguimiento que vacien la
cuarentena. Documentado aqui, no ejecutado en esta tarea.

1. Elegir un lote de 30 a 50 pares de la misma categoria en
   `patterns_wip.nut`.
2. Convertirlos editando `es_pack/corpus/base_es.nut` (el corpus es el
   fichero canonico; la cuarentena es solo un informe generado, nunca se
   edita a mano). Seguir `AGENTS_TRANSLATING.md` (raiz del repo, sincronizado
   desde upstream master). Reglas clave:
   - `[color=<this.Const...>]50%[/color]` se convierte en
     `en = "... <x:val_tag> ..."` y en `es` simplemente `<x>`.
   - `<this.Const.Strings.getArticle(...) + item.getName()>` se convierte en
     `<item:str_tag>` o `<item:str>` segun el caso; en `es`, `<item>`, o
     `<item:t>` si ese contenido tiene su propio par literal y conviene
     traducirlo por separado (recursion via Rosetta).
   - Los pares cuyo texto solo contiene `%marcadores%` y ningun `<...>` real
     normalmente pueden pasar a ser literales: quitarles `mode = "pattern"`.
   - Los pares con `<ret>` (restos de una concatenacion parcial) casi nunca
     son salvables como patron: valorar borrarlos directamente del corpus (el
     texto completo ya esta capturado en otro par).
3. Rebuild y comprobar que el lote migro de cuarentena a dist:
   ```bash
   PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py
   ```
   `dist` sube y `wip` baja exactamente en el tamano del lote, salvo los
   pares borrados en el paso 2. Esta comprobacion automatica (via
   `classify()`, ver seccion de arriba) es la validacion del lote: no hace
   falta ningun otro chequeo antes de pasar al siguiente lote.
4. Cada 3 o 4 lotes: instalar el zip generado y comprobar in-game al menos
   una string del lote, ademas del log del juego sin errores.
5. Commit por lote, con el mensaje:
   `es-pack: patrones lote N (<categoria>), -X wip / +Y dist`


## Criterio de cierre de la fase

La fase se cierra cuando la cuarentena baja de 100 pares. Los pares
irreducibles que queden por debajo de ese umbral se documentan en este mismo
fichero con el motivo por el que no se pueden convertir a patron (por
ejemplo: expresion demasiado dinamica para cualquiera de los tipos de
captura soportados).

Entonces, en ese orden:
1. Subir `PACK_VERSION` a `"1.5.1.8-2"` en `es_pack/tools/build_dist.py`.
2. Subir `Version` a `"1.5.1.8-2"` en el wrapper
   `es_pack/src/scripts/!mods_preload/mod_rosetta_base_es.nut`.
3. Rebuild (`build_dist.py`).
4. Verificacion in-game siguiendo el mismo checklist de la Tarea 10
   (`.superpowers/sdd/2026-08-15-es-pack-unfork/task-10-brief.md`): arranque
   sin errores de Modern Hooks, textos en castellano en menu de campania,
   tooltips, eventos/contratos y ambiciones, y log del juego sin `ERROR` de
   rosetta.
5. Tag `es-pack-v0.2.0`.


## Fuera de alcance en esta tarea

Esta tarea (12, pasos 1 y 2) cubre solo el inventario anterior y este
procedimiento documentado. La conversion real de los lotes (paso 3 de la
tarea 12 en `task-12-brief.md`) y el cierre de fase con el bump de version y
el tag `es-pack-v0.2.0` quedan para tareas de seguimiento posteriores.
