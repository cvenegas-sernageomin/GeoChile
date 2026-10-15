# Visor GeoChile — notas para Claude

Visor Leaflet (ahora PWA instalable) de cartas geológicas y mapas de peligros.
Repo `cvenegas-sernageomin/GeoChile` (rama `main`) → https://cvenegas-sernageomin.github.io/GeoChile/
Ficha en memoria: `proyecto-geo-repo-maule-sernageomin`.

## Estructura
`index.html` + `viewer_legend.js` leen `capas.json` en vivo (`fetch(...,{cache:'no-cache'})`).
`overlays/*.webp` (mapa recortado), `leyendas/*.jpg`, `peligros/`, `tools/` (el hillshade se retiró el 2026-10-15; sigue en el historial de git) (pipeline Python).
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
- **Recursos Minerales (M81/82/84/85/86/89/104/105/168/169/195/305)**: `python -I -X utf8 tools/exportar_recursos_a_datos.py` (en vez del script de GDB: lee las GDB y suma encima estos paquetes de `..\publicaciones-sernageomin\Recursos Minerales`; necesita `pyodbc` + driver Access de Windows y `xlrd`). Posición desde el .shp/.TAB, atributos desde `Atributos.mdb`/.xls (la tabla M84 trae UTM_NORTE=UTM_ESTE: no usarla). Datum por paquete en `DATUM` del script: WGS84 según metadato en M81–M105 (**sin contrastar con la lámina** en M81/82/84/85/86), PSAD56 (towgs84 -270,183,-390) en M168/169/195/305. Dedup contra las GDB (<30 m + misma edad/nombre/medida). Los códigos de estructura SS/FD/FC/21 de Coquimbo no tienen leyenda: salen como «Estructura (cód. X)».
- **Láminas de Recursos Minerales como overlays** (`rm_M81/82/84/85/86/105/168/169/195/305`, Geología Aplicada → Geología Económica): `python -I -X utf8 tools/georef_recursos.py M85 ... --capas [--verificar]`. El marco de la lámina ES el cuadrángulo de grados redondos (PSAD56; SIRGAS en M105) y el mapa está en geográficas: homografía de las 4 esquinas, no una caja (los bordes difieren 4–7 px). `--verificar` dibuja los yacimientos de la tabla sobre el overlay y debe caer sobre los símbolos. **Datum**: la lámina imprime PSAD56 pero las tablas .mdb/.shp de M81–M86 están en WGS84 (cambio ya aplicado, −183 E/−355 N m); **M86: los yacimientos del shapefile traen el cambio aplicado DOS veces** (corrección `CORRECCION_XY` en exportar_recursos_a_datos.py, evidencia en el comentario). Los rótulos N/S de `MD_MAPAS` vienen invertidos en M85. Sin botón ⬇ PDF aún (PDFs de 6–20 MB en los zips; subirlos a la Release «informes» si se quiere).
- Pendiente: GDB de M316 (archivos .lock, no abre) y 9 cartas antiguas en shapefile (Atacama: M100, M101, M107, M108, M23, M27, M54, M59, M60); Geoquímica y Peligros sin extraer; M111 (Recursos Minerales) solo trae polígonos.
