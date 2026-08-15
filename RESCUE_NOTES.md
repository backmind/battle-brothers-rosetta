# Acta de rescate (2026-08-15)

Rama archivo permanente del trabajo de traduccion ES previo al des-forkeo.
NO borrar, NO rebasear, NO force-push.

## Activos y recuentos

| Activo | Que es | Recuento |
|--------|--------|----------|
| rosetta/base_es.nut | Pack compilado por rosetta_db (editado a mano al final: activate) | 13.804 pares, 1.683 mode=pattern, 1.476 con placeholders crudos |
| base_es.nut.bak | Estado anterior del pack (difiere del actual) | - |
| translation_1.5.1.7.po | PO bilingue generado por create_po.py (bootstrap desde la traduccion fan) | - |
| translations.db | BBDD con schema versionado | 16.169 strings (v1.5.1.8), 12.428 traducciones reviewed |
| translations.db.bak | Estado anterior de la BBDD | - |
| rosetta_db/ | Capa Python: extractor, compiler, exporters, import_nut, web UI Flask | - |
| create_po.py | Alineador heuristico EN/ES de dos arboles .nut descompilados | - |
| scripts/!mods_preload/!rosetta.nut | Runtime 0.2.0 con 3 parches locales (regex de patrones, detect es, include base_es) | - |

## Procedencia de la traduccion

Traduccion fan de reemplazo (elgranfoca y anteriores, NexusMods "Traduccion completa
al Castellano") descompilada en DECOMP_ES, alineada contra DECOMP_EN (1.5.1.8) con
create_po.py (matching posicional + heuristico), importada a translations.db y
compilada a base_es.nut.

## Defectos conocidos (por eso se regenera en la rama es-pack)

- Los 1.683 pares mode=pattern usan placeholders crudos (<this...>, <ret>) que el
  runtime 0.4.0 no parsea; en 0.4.0 ademas harian throw en validateRule.
- extractor.py no limpiaba rosetta.SEEN entre ficheros: strings repetidas perdidas
  o mal atribuidas.
- base_es.nut fue editado a mano tras compilar (activate final).
