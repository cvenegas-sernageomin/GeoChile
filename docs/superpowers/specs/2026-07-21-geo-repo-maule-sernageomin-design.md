# Geo_Repo_Maule_Sernageomin — Diseño

**Fecha:** 2026-07-21
**Autor:** Carlos Venegas (SERNAGEOMIN) + Claude
**Estado:** Diseño aprobado, pendiente revisión del spec escrito

## 1. Objetivo

Reemplazar el visor KMZ de Google Earth de la Región del Maule ([piloto SIG SERNAGEOMIN]) por un **visor web Leaflet de escritorio, simple y online**, publicado en GitHub Pages. El visor muestra la cartografía geológica del Maule como capas raster georreferenciadas, cada una con su **leyenda separada** (patrón de la PWA de remociones / mapas-peligros-overlays).

El repo KMZ viejo (`cvenegas-sernageomin/sernageomin-maule`) **queda intacto** como respaldo; este es un proyecto nuevo y autocontenido.

## 2. Alcance

### Dentro
- Visor web Leaflet de escritorio, un solo `index.html` que lee `capas.json` en vivo.
- Reprocesamiento de **todos los overlays raster** con leyenda horneada → recorte al neat-line (overlay) + leyenda aparte + warp a plate-carrée:
  - **Geología oficial (10):** `geo_F19_pichibelco`, `geo_F21`, `geo_F21_raster`, `geo_F22_rio_claro_IR110`, `geo_F28_carta64`, `geo_lagunamaule_LDMField_{NE,NW,SE,SW}`, `geo_tinguiririca_teno`.
  - **Aplicada (13):** `geof_bouguer_geof115`, `geof_residual_geof115`, `geoq_IR114_mataquito_sedimentosPEC`, `hidrogeoq_F19_cauquenes`, `lic_curico_2010`, `rem_F09_curico_2010`, `rem_F13_constitucion_2010`, `rem_duao_iloca_2010`, `rme15_yacimientos_rmi_maule`, `tsu_constitucion_2010`, `tsu_duao_iloca_2010`, `vol_peligros_cerro_azul_quizapu_GAMB23`, `vol_peligros_descabezado_quizapu_GAMB39`.
  - **Histórico (2):** `escobar_1977_chile`, `gfv_andes_35_38`.
- Capas **sin reprocesar**, copiadas/servidas tal cual:
  - **Hillshade Copernicus 30m (23 cartas):** `hs_F07`…`hs_F29`.
  - **Académicos (8):** `aca_*` KMZ — se dejan con su leyenda tal cual (sin recorte).

### Fuera (explícito)
- **Sismos** (USGS/CSN): NO se cargan ni referencian.
- **Fallas activas (CHAF v1):** NO se cargan ni referencian.
- **PWA / offline / sw.js / precache:** no. Visor web simple, online.
- **Optimización móvil:** no es objetivo (visor de escritorio).
- No se modifica el repo KMZ viejo.

## 3. Hosting y repo

- **Repo:** `cvenegas-sernageomin/Geo_Repo_Maule_Sernageomin` (público, GitHub Pages, `.nojekyll`).
- **Local:** `C:\Users\carlos.venegas\Documents\Geo_Repo_Maule_Sernageomin\`.
- **URL pública:** `https://cvenegas-sernageomin.github.io/Geo_Repo_Maule_Sernageomin/`.
- Publicación git+web (cuenta `cvenegas-sernageomin`, login por navegador; `gh` no está en PATH). Ver [publicar-pwa-github-pages].

## 4. Estructura del repo

```
index.html                 # visor Leaflet (lee capas.json en vivo)
.nojekyll
capas.json                 # índice maestro que consume el visor
overlays/<id>.webp         # mapa recortado al neat-line + warp plate-carrée (alpha)
leyendas/<id>.jpg          # leyenda recortada aparte (JPG)
hillshade/<id>.webp        # 23 cartas hillshade (portadas del repo viejo o re-export)
academicos/<id>.{webp,jpg} # académicos tal cual (overlay full-sheet, leyenda horneada)
georef/<id>.py             # script reproducible por mapa (reprocesados)
README.md
docs/superpowers/specs/…   # este diseño + plan
```

### Esquema de `capas.json`
Array de objetos, uno por capa:
```json
{
  "id": "geo_F19_pichibelco",
  "categoria": "geologia",            // geologia | aplicada | historico | academico | hillshade
  "titulo": "Geología Pichibelco-Cauquenes (CGCH GB-214)",
  "fuente": "SERNAGEOMIN CGCH GB-214",
  "anio": "…", "escala": "1:100.000", "autor": "…", "informe": "…",
  "bounds": { "n": -35.478, "s": -36.234, "e": -71.308, "w": -72.521 },  // WGS84, plate-carrée
  "overlay": "overlays/geo_F19_pichibelco.webp",
  "leyenda": "leyendas/geo_F19_pichibelco.jpg",   // null si no aplica (hillshade)
  "opacidad": 1.0,
  "recortado": true                   // false = full-sheet con leyenda horneada (académicos)
}
```
- El visor **no se toca** al sumar/actualizar mapas: solo se edita `capas.json` + assets.
- `bounds` en plate-carrée (rotación 0) → `L.imageOverlay(bounds=[[s,w],[n,e]])` cae exacto.

## 5. Pipeline de reprocesamiento (por mapa raster)

Calcado de [mapas-peligros-overlays] variante A (PDF SERNAGEOMIN con grilla UTM) + [georef-kmz-sernageomin], adaptando cada `georef_*.py` que ya existe en `Documents\sernageomin_maule\`:

1. **Fuente:** reusar el georef existente / render PyMuPDF del PDF/GeoTIFF original.
2. **Detectar neat-line** (marco interior) y **recortar SOLO el mapa** (no confundir con mapas secundarios en la misma hoja).
3. **Warp a plate-carrée** (UTM/geo → WGS84 lineal, `pyproj` + `cv2.remap`, alpha=0 fuera del marco), rotación 0 → exacto para Leaflet. Export `overlays/<id>.webp` (alpha, cap ~3000px).
4. **Recortar la leyenda** del sheet → `leyendas/<id>.jpg`. Si varias hojas comparten leyenda (ej. Laguna del Maule cuartos, Valpo-style), un solo JPG referenciado por varias entradas.
5. **Registrar** entrada en `capas.json` con `bounds` WGS84 + rutas.
6. **Verificar** (`verify()` error < 100 m; 1–2 puntos conocidos dentro del footprint).

**Entorno (GOTCHA):** usar `C:\Users\carlos.venegas\AppData\Local\Programs\Python\Python312\python.exe` (tiene cv2/pyproj/fitz/PIL), siempre `-X utf8`. El `python` 3.14 por defecto NO sirve.

**EPSG:** Maule cruza husos en 72°00'O → 19S (EPSG:32719) al este, 18S (EPSG:32718) al oeste; verificar datum impreso (algunos PSAD56, no WGS84/SIRGAS).

## 6. Visor (`index.html`)

- **Leaflet 1.9.4** (CDN o vendorizado single-file, según patrón [build-html-offline]).
- **Bases:** Esri Satelital, Esri Topo, OpenTopoMap (switcher).
- **Panel de capas** lateral (escritorio) agrupado por categoría con `<details>`:
  `🗺️ Geología · ⚠️ Aplicada · 📜 Histórico · 🎓 Académicos · 🏔️ Hillshade`.
  Cada capa raster: checkbox toggle + **slider de opacidad** + botón **"ⓘ Ver leyenda"**.
- **Overlays:** `L.imageOverlay(bounds=[[s,w],[n,e]], {opacity, pane})`. Panes por categoría para z-order estable (hillshade abajo, geología/aplicada encima).
- **Modal de leyenda:** muestra `leyendas/<id>.jpg` con **zoom/pan propio (Pointer Events)** reutilizado del patrón v57 de remociones (rueda + arrastre en escritorio).
- **Estado inicial:** todas las capas apagadas; mapa centrado en el bbox del Maule.
- **(Opcional)** estado en URL (`?capa=<id>`) para compartir un mapa concreto.

## 7. Reparto Opus / subagentes

- **Opus:** monta `index.html`, define `capas.json`, copia hillshade + académicos, y hace **2 pilotos** end-to-end (`geo_F19_pichibelco` + `geo_F21_raster`), verificados en Pages.
- **Subagentes Sonnet:** reprocesan mecánicamente los ~23 mapas raster restantes (variante A ya definida, bounds/fuente resueltos por Opus). **Encolar en el mismo subagente** los que tocan el repo, para no chocar commits (ver [delegar-tareas-repetitivas-subagentes]).

## 8. Formatos de salida

- Overlay: **WebP con alpha** (mejor peso).
- Leyenda: **JPG** (pedido explícito del usuario).
- Hillshade: WebP (portada del repo viejo o re-export).

## 9. Criterios de aceptación

- Visor abre en escritorio, muestra las 5 categorías; cada capa se enciende/apaga, opacidad ajustable, leyenda visible con zoom.
- Los 25 mapas raster reprocesados caen **alineados** sobre la base satelital (verificación por punto conocido).
- Hillshade (23) y académicos (8) presentes y funcionales.
- Sin sismos ni fallas.
- Publicado y accesible en la URL de Pages.

## 10. Riesgos / notas

- Algún `georef_*.py` viejo podría no traer recorte de neat-line → adaptarlo (o recortar desde el PNG full-sheet ya warpeado si no hay fuente limpia).
- `geo_F21` vs `geo_F21_raster`: uno es la versión raster, otro vectorial San Clemente — confirmar cuál se reprocesa como overlay (probablemente el raster; el vectorial podría convertirse a GeoJSON en fase posterior, fuera de alcance ahora).
- Académicos con leyenda horneada quedan `recortado:false` (full-sheet) — decisión consciente.

## Referencias
- Memoria proyecto viejo: `~/.claude/memories/project_sernageomin_maule_sig.md`
- Georref PDF→KMZ: `Documents\sernageomin_maule\README_GEOREF.md` + [georef-kmz-sernageomin]
- Pipeline overlays web: [mapas-peligros-overlays]
- Integración Leaflet + modal leyenda zoom: [catastro-remociones] (v51/v57)
