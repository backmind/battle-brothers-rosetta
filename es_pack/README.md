# Battle Brothers en Castellano (pack Rosetta)

Traduccion del juego base (y DLCs) al castellano que NO modifica los
archivos del juego: sustituye los textos en caliente. Si el juego se
actualiza, la traduccion sigue funcionando y las frases nuevas se ven
en ingles hasta que se traduzcan.

## Instalacion

1. Instala en la carpeta `data` del juego, por este orden de descarga:
   - Modern Hooks (NexusMods)
   - MSU - Modding Standards & Utilities (NexusMods)
   - stdlib (NexusMods)
   - Rosetta Translations (NexusMods, mod 802), version 0.4.0 o superior. Si aun no esta publicada en Nexus, este repositorio permite construirla: git archive --format=zip -o mod_rosetta_0.4.0.zip HEAD rosetta scripts
   - `mod_rosetta_base_es_<version>.zip` (este pack)
2. Arranca el juego. No hay que configurar nada.

## Que traduce y que no

- Traduce: eventos, contratos, tooltips, habilidades, perks, ambiciones
  y en general todo texto generado por los scripts del juego.
- No traduce (todavia): el menu principal y botones construidos en JS,
  y los rotulos del mapa que dibuja el motor. Ver hoja de ruta.

## Para desarrolladores

- Corpus canonico: `corpus/base_es.nut` (formato Rosetta; se regenera
  con `rosetta.py -r` sobre un arbol descompilado del juego).
- Build: `PYTHONUTF8=1 uv run python es_pack/tools/build_dist.py`
- Los pares con placeholders sin tipar quedan en `build/patterns_wip.nut`
  hasta convertirlos a la sintaxis `<nombre:tipo>` (ver
  AGENTS_TRANSLATING.md de upstream).

## Creditos

Traduccion original de reemplazo: MagnusLioncaster, Hjensikk, AMarauder
y elgranfoca (NexusMods, "Battle Brothers - Traduccion completa al
Castellano"). Adaptacion a Rosetta: backmind. Framework Rosetta: Suor.
