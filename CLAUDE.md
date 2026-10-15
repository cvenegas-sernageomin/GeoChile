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

## Datos puntuales de las GDB (📍 Datos)
`datos.js` + `datos/` (geocronología, fósiles, yacimientos, estructuras). El panel y sus filtros se generan solos desde `datos/index.json`.
- Regenerar: `python -I -X utf8 tools/exportar_gdb_a_datos.py` (lee `..\cartas-geologicas-sernageomin\_mapas_por_ingresar\gdb_extraidos`, catálogo en `..\publicaciones-sernageomin\catalogo.csv`), luego `python -I -X utf8 tools/validar_datos.py` y `python -I -X utf8 tools/test_datos_lib.py`. Revisar `datos/ingesta.json` (GDB fallidas, duplicados, edades con unidad inferida).
- Tras regenerar: subir **`DATA_V`** en `datos.js` (y el `?v=` de `datos.js` en `index.html` y `sw.js`) — `datos/*.json` se sirven con caché primero (`geochile-datos`). Al cambiar `sw.js`/shell subir también `VER`.
- Los dominios Esri se resuelven **por GDB** (leyendo `GDB_Items`): un código como `DAT-UNIDAD-4` significa «a C14 AP» en unas plantillas y «Ga» en otras. Nunca unir dominios de varias GDB.
- La edad se normaliza a Ma (`edad_ma`) y la época se calcula desde ella (límites ICS en `tools/datos_lib.py`); no se usan los códigos `T-EPOCA` de las GDB.
- Pendiente: GDB de M316 (archivos .lock, no abre) y 9 cartas antiguas en shapefile (Atacama: M100, M101, M107, M108, M23, M27, M54, M59, M60); series que no son Geología Básica (Geoquímica, Recursos Minerales, Peligros) sin extraer.
