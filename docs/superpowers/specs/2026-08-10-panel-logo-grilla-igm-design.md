# Panel colapsable + logo + grilla IGM — Diseño

**Fecha:** 2026-08-10
**Estado:** Aprobado

## 1. Objetivo

Tres mejoras de UI al visor publicado (`Geo_Repo_Maule_Sernageomin`), replicando parte de la experiencia del KMZ viejo dentro del visor web:
1. Panel lateral colapsable/desplegable.
2. Banner SERNAGEOMIN en el header del panel.
3. Grilla de las 23 cartas IGM 1:100.000 (F07–F29) visible sobre el mapa, con selector para centrar/zoom a una carta.

## 2. Alcance

### Dentro
- Botón `‹›` en el header del panel que colapsa el panel a ~32px de ancho (solo el botón visible) y lo restaura a 320px. Llama `map.invalidateSize()` al cambiar para que Leaflet reajuste el tile.
- Banner `assets/banner_sernageomin.jpg` (copiado del repo KMZ viejo, `sernageomin_maule/repo/quads/banner_sernageomin.jpg`) en el header del panel, junto al título.
- 23 rectángulos (`L.rectangle`) con las cartas F07–F29, coordenadas extraídas de `maule_indice.kmz` (fuente oficial ya publicada), embebidas como array estático `GRID_IGM` en `index.html`. Etiqueta de código de carta centrada en cada rectángulo (`L.marker` con `divIcon`, o `L.tooltip` permanente).
- Checkbox propio "🔲 Grilla IGM" en el panel, **fuera** de las categorías de `capas.json` (no es un asset raster, es geometría fija). Apagado por defecto.
- `<select>` con las 23 cartas junto al checkbox. Al elegir: `map.fitBounds()` al bbox de la carta + resalte temporal (cambio de color ~1.5s, revierte) del rectángulo correspondiente. Si la grilla estaba apagada, se enciende automáticamente.

### Fuera
- No se toca `capas.json` ni el pipeline de `tools/` — la grilla es geometría estática, no pasa por el pipeline de reprocesamiento.
- El selector de carta **no filtra** el panel de capas por categoría — solo navega el mapa (decisión confirmada: el modelo de datos actual es por categoría, no por carta, y mapear cada una de las 55 capas a su(s) carta(s) queda fuera de este alcance).
- No se agregan más capas ni cambios al pipeline de reprocesamiento.

## 3. Archivos

- Modificar: `index.html` (header del panel, CSS de colapso, grilla + selector, lógica).
- Crear: `assets/banner_sernageomin.jpg` (copiado del repo viejo).
- Sin cambios: `capas.json`, `viewer_legend.js`, `tools/`.

## 4. Datos de la grilla

Las 23 cartas (código, bounds WGS84 n/s/e/w) se extraen una sola vez de
`sernageomin_maule/repo/maule_indice.kmz` (`doc.kml`, polígonos por carta) y se transcriben
como constante estática en `index.html`. No se generan en runtime ni se leen de un archivo
externo (son 23 valores fijos, viven mejor inline que como fetch adicional).

## 5. Criterios de aceptación

- El panel colapsa/expande sin romper el layout del mapa (Leaflet se redibuja bien).
- El banner se ve en el header, capas.json sigue funcionando igual que antes.
- Activar "Grilla IGM" dibuja los 23 rectángulos con su etiqueta F07–F29 sobre el mapa.
- Elegir una carta en el `<select>` centra/hace zoom ahí y resalta el rectángulo brevemente.
- Nada de esto rompe las capas existentes (55 entradas de `capas.json` siguen cargando y funcionando igual).
