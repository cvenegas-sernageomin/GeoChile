# Visor GeoChile — notas para Claude

Visor Leaflet (ahora PWA instalable) de cartas geológicas y mapas de peligros.
Repo `cvenegas-sernageomin/GeoChile` (rama `main`) → https://cvenegas-sernageomin.github.io/GeoChile/
Ficha en memoria: `proyecto-geo-repo-maule-sernageomin`.

## Estructura
`index.html` + `viewer_legend.js` leen `capas.json` en vivo (`fetch(...,{cache:'no-cache'})`).
`overlays/*.webp` (mapa recortado), `leyendas/*.jpg`, `peligros/`, `hillshade/`, `tools/` (pipeline Python).
PDF de informes: los grandes van en la **Release «informes»** del repo (Pages no aguanta >1 GB).

## Reglas
- Al cambiar overlays: subir **`ASSET_V`** (`?v=AAAAMMDD…`). Al cambiar el shell: subir **`VER`** en `sw.js`.
- Los overlays de cartas se corrigen en el repo `cartas-geologicas-sernageomin` y se copian aquí (no hay sincronización automática).
- Las CGCH_NN no se corrigen. No corregir georreferencia sin re-auditar. Esri satelital NO sirve de referencia (ver memoria `proyecto-taller-mapas-sernageomin`).
- Pages distingue mayúsculas: tras agregar assets, verificar con `git ls-files` (Windows no lo hace).
- Gran parte del trabajo reciente se hizo en el otro PC: `git pull --ff-only` antes de editar.

## Verificar
Servidor: config `geochile` (puerto 8794) en `.claude/launch.json`. Tras push, `curl` al sitio y comparar `VER`/`ASSET_V`.
