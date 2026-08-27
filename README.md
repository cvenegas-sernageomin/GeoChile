# Visor GeoChile

Visor web de cartografía geológica de Chile (SERNAGEOMIN) — antes "Geo_Repo_Maule_Sernageomin".
Overlays raster recortados (mapa) + leyendas aparte, hillshade y trabajos académicos,
sobre base satelital/topográfica. Visor de escritorio, sin instalación.

**Publicado:** https://cvenegas-sernageomin.github.io/GeoChile/

Reemplaza al antiguo atlas KMZ para Google Earth (`sernageomin-maule`), que se mantiene
como respaldo.

## Contenido

- **Geología (12)** — cartas oficiales (incl. GB-123, GB-135/136, M204 a nivel nacional), Laguna del Maule, Tinguiririca-Teno.
- **Aplicada (13)** — geofísica, geoquímica, remociones, tsunami, licuefacción, volcanes, recursos minerales.
- **Histórico (2)** — mapas académicos/históricos de referencia regional.
- **Académicos (8)** — trabajos universitarios, hoja completa con su leyenda original.
- **Hillshade (23)** — relieve sombreado Copernicus GLO-30, una por carta 1:100.000 (F07–F29).

No incluye sismos ni fallas activas (fuera de alcance de este visor).

## Estructura

- `index.html` + `viewer_legend.js` — visor Leaflet (lee `capas.json` en vivo).
- `capas.json` — índice de capas (id, categoría, título, fuente, bounds, rutas de overlay/leyenda).
- `overlays/`, `leyendas/`, `hillshade/`, `academicos/` — assets WebP/JPG.
- `tools/` — pipeline de reprocesamiento (Python 3.12: cv2, pyproj, Pillow, pymupdf).

## Agregar o actualizar un mapa

1. Ubicar el KMZ fuente en `sernageomin_maule\repo\capas\<categoria>\<id>.kmz` (trae su
   propio `LatLonBox`+rotación, ya georreferenciado).
2. `python tools/reprocesar.py <categoria> <id>` (usar Python 3.12, con `-X utf8`) — detecta
   el neat-line, recorta el mapa, separa la leyenda y genera `overlays/<id>.webp` +
   `leyendas/<id>.jpg`. Si el detector automático falla o el resultado no separa bien mapa
   y leyenda, usar `--rect x0,y0,x1,y1` (manual), `--side right|below|left|above`, o
   `--no-legend` (hojas sin leyenda separable).
3. Copiar la línea `ENTRY {...}` que imprime el comando y agregarla a `capas.json`
   (completar `titulo`, `fuente`, `anio`, `escala`, `autor`, `informe`).
4. `python tools/validar_capas.py capas.json` → debe imprimir `OK: N capas validas`.
5. Commit + push. El visor **no se toca**: lee `capas.json` en vivo.

Para capas de paso directo sin recorte (como hillshade/académicos), usar
`tools/copiar_pass_through.py <categoria> <destino_dir>` en vez de `reprocesar.py`.

## Entorno

Python 3.12 con `cv2`, `numpy`, `pyproj`, `Pillow`, `pymupdf`. En este equipo:
`C:\Users\carlos.venegas\AppData\Local\Programs\Python\Python312\python.exe -X utf8`
(el `python` por defecto no tiene estas dependencias).
