# Hallazgos de la verificacion in-game v0.1.0 (2026-08-15/16)

Log de la sesion de prueba: "Adding 12325 es pairs in vanilla", 0 errores de
rosetta, 231 lineas NOT FOUND (informativas). Juego actualizado a la ultima
version, corpus construido sobre el arbol 1.5.1.8: la independencia de
version quedo validada.

## Clases de texto en ingles observadas y su causa

1. Patrones en cuarentena (Fase 4, v0.2.0): log de combate ("X uses Y and
   hits Z (Chance, Rolled)", "has killed", "is confident"), "Paid X daily",
   "Costs X AP and Y Fatigue", mecanica de habilidades y traits, "Level X",
   "locked until X more perks", "Act in X turn(s)". Evidencia: aparecen como
   NOT FOUND en el log con colores resueltos y nombres ya traducidos dentro.
   La conversion a sintaxis <etiqueta:tipo> los activa (ver PATTERNS_TODO.md).

2. Funnels sin hook (no aparecen en NOT FOUND pese a verse en ingles; el
   texto NI SIQUIERA pasa por Rosetta): aviso del menu principal
   (scripts/ui/screens/menu/main_menu_screen.nut), tips de la pantalla de
   carga (Const.TipOfTheDay hacia ui/screens/loading/loading_screen.js),
   cuerpo de los eventos (el titulo SI se traduce: viajan por conductos
   distintos), pantalla post-batalla ("Victory", "The enemy was destroyed
   in N rounds"). Candidatos a hooks propios del pack o a contribucion
   upstream (issue a Suor).

3. Capa JS (se resuelve reinstalando trad303.zip, los 62 ficheros js
   traducidos): "Background", botones "Show/hide", pestanas "Statistics" y
   "Loot", boton "Continue".

4. Motor C++ (no interceptable por diseno): rotulos del mapa ("Northern
   Reaches"). Mitigacion historica de la traduccion fan: fuentes del kit
   gfx y nombres sin tildes.

5. Doble traduccion (inofensivo): la mayoria de los NOT FOUND del log son
   textos YA en espanol re-interceptados en re-renderizados de tooltips.

6. Pares desalineados del bootstrap heuristico: 1 encontrado y corregido
   (tooltip de "kills" mostraba el texto de renombrar personaje). Pueden
   existir mas: pendiente un barrido semantico en/es sistematico.

7. MSU referencia gfx/fonts/cinzel en ui/mods/msu/css/misc.css sin
   distribuir la fuente: 1 error IO cosmetico en el log. Se silencia
   reinstalando el kit gfx de la traduccion antigua (fuentes Cinzel).
   OJO empaquetado: el renderizador de UI carga las fuentes por RUTA DE
   DISCO (data/gfx/fonts/...), no via zips. Las fuentes deben instalarse
   como carpeta suelta gfx/ en data/; el addon de UI (zip) solo debe
   contener ui/ (js). Verificado 2026-08-16: con las fuentes dentro del
   zip el error IO persiste; con la carpeta suelta desaparece.
