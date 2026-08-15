# Battle Brothers en Castellano (pack Rosetta)

Traduccion al castellano del juego base de Battle Brothers y sus expansiones que **no modifica ningun archivo del juego**: registra pares ingles-espanol y sustituye los textos en caliente mientras juegas, usando el framework [Rosetta](https://github.com/Suor/battle-brothers-rosetta) de Suor.

La consecuencia practica: **las actualizaciones del juego no rompen la traduccion**. Cuando sale un parche, todo lo que no cambio sigue en castellano y las frases nuevas aparecen en ingles hasta que se traducen. Se acabo esperar semanas a que la traduccion se repare.

> *English note: this branch hosts a Spanish base-game translation pack built on top of Suor's Rosetta framework. The upstream framework docs live on the `master` branch and at [Suor/battle-brothers-rosetta](https://github.com/Suor/battle-brothers-rosetta).*

## Creditos: sobre hombros de gigantes

Este proyecto **no parte de cero**. El corpus de traduccion nace del trabajo de anos de la comunidad en [Battle Brothers - Traduccion completa al Castellano](https://www.nexusmods.com/battlebrothers/mods/640) de NexusMods:

- **MagnusLioncaster, Hjensikk y AMarauder**: autores de la traduccion original.
- **ElGranFoca**: mantenedor actual de aquella traduccion y autor de su reconstruccion 3.x.
- **Suor (hackflow)**: autor del framework Rosetta y sus herramientas.
- **backmind**: adaptacion del corpus al modelo Rosetta, limpieza UTF y este pack.

Si esta traduccion te sirve, pasa por la pagina de Nexus original y dales tu endorse: sin ellos no habria nada que empaquetar.

## Instalacion paso a paso

Necesitas 6 archivos en la carpeta `data` del juego. La carpeta esta en:

- GOG: `<instalacion>\Battle Brothers\data`
- Steam: `<Steam>\steamapps\common\Battle Brothers\data`

Descarga estos 5 mods de NexusMods (el archivo .zip de cada uno va tal cual a `data`, no hace falta renombrar nada):

1. [Modding Script Hooks](https://www.nexusmods.com/battlebrothers/mods/42) (los hooks clasicos de Adam)
2. [Modern Hooks](https://www.nexusmods.com/battlebrothers/mods/685)
3. [MSU - Modding Standards and Utilities](https://www.nexusmods.com/battlebrothers/mods/479) (version 1.6.0 o superior)
4. [stdlib](https://www.nexusmods.com/battlebrothers/mods/676) (version 2.5 o superior)
5. [Rosetta Translations Framework](https://www.nexusmods.com/battlebrothers/mods/802) (version 0.4.0 o superior)

Y por ultimo el pack de traduccion:

6. `mod_rosetta_base_es_<version>.zip`, desde la seccion [Releases](https://github.com/backmind/battle-brothers-rosetta/releases) de este repositorio.

Arranca el juego. No hay que configurar nada: el pack activa el castellano solo.

### Como saber que funciona

Al crear una campana nueva, los origenes de compania y sus descripciones deben verse en castellano. Si quieres comprobarlo a fondo, abre el log del juego (`Documentos\Battle Brothers\log.html`) y busca la linea `Adding NNNNN es pairs in vanilla`.

## Que traduce y que no (todavia)

- **Traducido**: eventos, contratos, tooltips, habilidades, perks, origenes, ambiciones, rasgos, estadisticas y en general el texto que generan los scripts del juego. Mas de 12.000 textos en la v0.1.0.
- **En proceso** (v0.2.x): los textos con partes variables (log de combate, "Paid X daily", mecanica numerica de habilidades), que requieren el formato de patrones de Rosetta. Su estado se sigue en [es_pack/corpus/PATTERNS_TODO.md](es_pack/corpus/PATTERNS_TODO.md).
- **Pendiente de permiso**: el complemento opcional de menus (archivos js derivados de la traduccion de Nexus).
- **Limite conocido**: los rotulos que dibuja el motor grafico directamente sobre el mapa (nombres de regiones). Detalle completo en [es_pack/corpus/KNOWN_ISSUES.md](es_pack/corpus/KNOWN_ISSUES.md).

## Como colaborar

La traduccion entera es un archivo de texto: [es_pack/corpus/base_es.nut](es_pack/corpus/base_es.nut). Cada correccion es editar una linea y abrir un pull request; no hay que saber programar ni tocar el juego. Los pares pendientes estan marcados con `es = ""`. Para los patrones (textos con `<variables:tipo>`), la guia es [AGENTS_TRANSLATING.md](AGENTS_TRANSLATING.md) mas el procedimiento de [PATTERNS_TODO.md](es_pack/corpus/PATTERNS_TODO.md).

## Para desarrolladores

- Corpus canonico: `es_pack/corpus/base_es.nut` (formato Rosetta, fuente de verdad).
- Build del zip distribuible: `PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py` (filtra pares vacios y patrones invalidos, decodifica escapes, empaqueta).
- Regeneracion tras un parche del juego: descompilar la version nueva y `PYTHONUTF8=1 uv run python es_pack/tools/extract_wrapper.py <arbol>/scripts -les -r es_pack/corpus/base_es.nut -q > es_pack/corpus/base_es.nut.nuevo`, despues `quote_fix.py`. Siempre via `extract_wrapper.py` (incluye el workaround de un bug del extractor upstream, reportado en [Suor/battle-brothers-rosetta#2](https://github.com/Suor/battle-brothers-rosetta/issues/2)).
- Ramas: `es-pack` (este pack; solo anade archivos), `master` (espejo limpio de upstream), `legacy-es-pipeline` (archivo historico del pipeline anterior).

## Licencia y agradecimientos

El framework Rosetta es de Suor (ver su [licencia](LICENSE)). El contenido de la traduccion deriva del trabajo de los autores citados en creditos, con su conocimiento; si eres uno de ellos y quieres cualquier cambio en la atribucion o el uso del material, abre un issue y se atiende de inmediato.
