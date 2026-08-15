// Traduccion del juego base Battle Brothers al castellano, via Rosetta.
// Requiere: Modern Hooks, MSU >= 1.6.0, stdlib >= 2.5, Rosetta >= 0.4.0.
// Las strings sin par registrado se muestran en ingles: este mod no se
// rompe con las actualizaciones del juego.
if (!("Rosetta" in getroottable())) return;

local def = {
    ID = "mod_rosetta_base_es"
    Name = "Battle Brothers en Castellano (Rosetta)"
    Version = "1.5.1.8-1"
}
local mod = ::Hooks.register(def.ID, def.Version, def.Name);
mod.require("mod_rosetta >= 0.4.0");

::include("mod_rosetta_base_es/base_es");

// El juego instalado esta en ingles, asi que la autodeteccion de idioma
// de Rosetta (que mira strings ya traducidas) no aplica: activamos es.
::Rosetta.activate("es");
