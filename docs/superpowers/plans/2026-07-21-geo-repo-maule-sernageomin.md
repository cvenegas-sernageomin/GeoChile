# Geo_Repo_Maule_Sernageomin — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un visor web Leaflet de escritorio, publicado en GitHub Pages, que muestre la cartografía geológica del Maule como overlays raster recortados (mapa sin leyenda) + leyendas JPG aparte, más hillshade y académicos tal cual.

**Architecture:** Repo autocontenido. Un `index.html` (Leaflet) lee `capas.json` en vivo y pinta capas por categoría con toggle/opacidad/leyenda. Los overlays raster se generan reprocesando los KMZ existentes del repo viejo: cada KMZ ya trae `LatLonBox`+rotación (georreferenciación resuelta), así que la transformación `pixel↔geo` se reconstruye en forma cerrada; solo se detecta el neat-line para separar mapa de leyenda y se warpea el mapa a plate-carrée (Leaflet ignora rotación).

**Tech Stack:** Python 3.12 (`cv2`, `numpy`, `pyproj`, `Pillow`, `pymupdf`) para el reprocesamiento; Leaflet 1.9.4 + HTML/JS para el visor; GitHub Pages para hosting.

**Entorno crítico:** usar SIEMPRE `C:\Users\carlos.venegas\AppData\Local\Programs\Python\Python312\python.exe` con `-X utf8`. El `python` por defecto (3.14) NO tiene cv2/pyproj.

**Rutas base:**
- Proyecto nuevo: `C:\Users\carlos.venegas\Documents\Geo_Repo_Maule_Sernageomin\` (ya es repo git con el spec commiteado).
- KMZ fuente: `C:\Users\carlos.venegas\Documents\sernageomin_maule\repo\capas\<categoria>\<id>.kmz`.

---

## File Structure

- `index.html` — visor Leaflet (una sola página, sin build).
- `capas.json` — índice maestro que consume el visor (array de capas).
- `tools/lib_reproc.py` — biblioteca: transform pixel↔geo desde LatLonBox+rot, detección neat-line, warp plate-carrée, export.
- `tools/reprocesar.py` — CLI: KMZ → `overlays/<id>.webp` + `leyendas/<id>.jpg` + imprime entrada `capas.json`.
- `tools/copiar_pass_through.py` — convierte KMZ de hillshade/académicos a WebP sin recorte y genera sus entradas.
- `tools/validar_capas.py` — valida `capas.json` contra el esquema.
- `tools/test_lib_reproc.py` — tests de las funciones puras.
- `overlays/<id>.webp`, `leyendas/<id>.jpg`, `hillshade/<id>.webp`, `academicos/<id>.webp` (+ `_leyenda.jpg`).
- `README.md`.

---

## Task 1: Esqueleto del repo + esquema `capas.json` + validador (TDD)

**Files:**
- Create: `tools/validar_capas.py`
- Create: `tools/test_validar_capas.py`
- Create: `capas.json` (inicial: `[]`)
- Create: `.nojekyll`

- [ ] **Step 1: Crear carpetas y archivos base**

```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin"
mkdir -p tools overlays leyendas hillshade academicos
printf '[]' > capas.json
: > .nojekyll
```

- [ ] **Step 2: Escribir el test del validador (debe fallar)**

Create `tools/test_validar_capas.py`:
```python
import json, subprocess, sys, tempfile, os

PY = sys.executable
HERE = os.path.dirname(__file__)

def run(capas):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(capas, f)
        path = f.name
    r = subprocess.run([PY, os.path.join(HERE, "validar_capas.py"), path],
                       capture_output=True, text=True)
    os.unlink(path)
    return r.returncode, r.stdout + r.stderr

def test_valida_entrada_correcta():
    ok = [{"id": "geo_x", "categoria": "geologia", "titulo": "T",
           "bounds": {"n": -35.0, "s": -36.0, "e": -71.0, "w": -72.0},
           "overlay": "overlays/geo_x.webp", "leyenda": "leyendas/geo_x.jpg",
           "opacidad": 1.0, "recortado": True}]
    code, out = run(ok)
    assert code == 0, out

def test_rechaza_bounds_invalidos():
    # north <= south debe fallar
    bad = [{"id": "geo_x", "categoria": "geologia", "titulo": "T",
            "bounds": {"n": -36.0, "s": -35.0, "e": -71.0, "w": -72.0},
            "overlay": "overlays/geo_x.webp", "leyenda": None,
            "opacidad": 1.0, "recortado": False}]
    code, out = run(bad)
    assert code != 0
    assert "bounds" in out.lower()

def test_rechaza_categoria_desconocida():
    bad = [{"id": "x", "categoria": "otra", "titulo": "T",
            "bounds": {"n": -35.0, "s": -36.0, "e": -71.0, "w": -72.0},
            "overlay": "overlays/x.webp", "leyenda": None,
            "opacidad": 1.0, "recortado": False}]
    code, out = run(bad)
    assert code != 0
    assert "categoria" in out.lower()
```

- [ ] **Step 3: Correr el test para verificar que falla**

Run: `& "C:/Users/carlos.venegas/AppData/Local/Programs/Python/Python312/python.exe" -X utf8 -m pytest tools/test_validar_capas.py -v`
Expected: FAIL (validar_capas.py no existe).

- [ ] **Step 4: Escribir el validador**

Create `tools/validar_capas.py`:
```python
import json, sys

CATS = {"geologia", "aplicada", "historico", "academico", "hillshade"}
REQ = {"id", "categoria", "titulo", "bounds", "overlay", "leyenda", "opacidad", "recortado"}

def validar(capas):
    errores = []
    ids = set()
    if not isinstance(capas, list):
        return ["raiz debe ser una lista"]
    for i, c in enumerate(capas):
        pre = f"[{i}] "
        faltan = REQ - set(c)
        if faltan:
            errores.append(pre + "faltan campos: " + ", ".join(sorted(faltan)))
            continue
        if c["categoria"] not in CATS:
            errores.append(pre + f"categoria desconocida: {c['categoria']}")
        if c["id"] in ids:
            errores.append(pre + f"id duplicado: {c['id']}")
        ids.add(c["id"])
        b = c["bounds"]
        if not all(k in b for k in ("n", "s", "e", "w")):
            errores.append(pre + "bounds requiere n,s,e,w")
        else:
            if b["n"] <= b["s"]:
                errores.append(pre + "bounds: north debe ser > south")
            if b["e"] <= b["w"]:
                errores.append(pre + "bounds: east debe ser > west")
        if not (0.0 <= c["opacidad"] <= 1.0):
            errores.append(pre + "opacidad fuera de [0,1]")
        if c["leyenda"] is not None and not isinstance(c["leyenda"], str):
            errores.append(pre + "leyenda debe ser ruta string o null")
    return errores

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "capas.json"
    with open(path, encoding="utf-8") as f:
        capas = json.load(f)
    errs = validar(capas)
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    print(f"OK: {len(capas)} capas validas")

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Correr el test para verificar que pasa**

Run: `& "C:/Users/carlos.venegas/AppData/Local/Programs/Python/Python312/python.exe" -X utf8 -m pytest tools/test_validar_capas.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add tools/validar_capas.py tools/test_validar_capas.py capas.json .nojekyll
git commit -m "feat: esqueleto repo + esquema capas.json + validador con tests"
```

---

## Task 2: `lib_reproc.py` — transform pixel↔geo desde LatLonBox+rotación (TDD)

**Files:**
- Create: `tools/lib_reproc.py`
- Create: `tools/test_lib_reproc.py`

Modelo (idéntico a `sernageomin_maule/to_latlonbox.py`): la imagen ocupa la caja `[W,E]×[S,N]` rotada `rot`° CCW sobre el centro, con longitudes escaladas por `cos(lat_centro)`. `pixel→geo`: pixel a lon/lat sin rotar en la caja, luego rotar sobre el centro. `geo→pixel`: inverso.

- [ ] **Step 1: Escribir los tests (deben fallar)**

Create `tools/test_lib_reproc.py`:
```python
import numpy as np
from lib_reproc import pixel_to_geo, geo_to_pixel, detect_neatline

BOX = dict(n=-35.0, s=-36.0, e=-71.0, w=-72.0, rot=0.5, lonc=-71.5, latc=-35.5)
W, H = 1000, 1000

def test_roundtrip_pixel_geo():
    for px, py in [(0, 0), (999, 0), (500, 500), (999, 999), (123, 456)]:
        lon, lat = pixel_to_geo(px, py, BOX, W, H)
        rx, ry = geo_to_pixel(lon, lat, BOX, W, H)
        assert abs(rx - px) < 1e-3, (px, py, rx)
        assert abs(ry - py) < 1e-3, (px, py, ry)

def test_centro_es_centro():
    lon, lat = pixel_to_geo((W - 1) / 2, (H - 1) / 2, BOX, W, H)
    assert abs(lon - BOX["lonc"]) < 1e-6
    assert abs(lat - BOX["latc"]) < 1e-6

def test_sin_rotacion_esquinas():
    box0 = dict(BOX, rot=0.0)
    lon, lat = pixel_to_geo(0, 0, box0, W, H)  # esquina superior-izq
    assert abs(lon - box0["w"]) < 1e-6
    assert abs(lat - box0["n"]) < 1e-6

def test_detect_neatline_recuadro():
    img = np.full((200, 300, 3), 255, np.uint8)
    # marco negro interior en x[20:280], y[15:185]
    img[15:186, 20:21] = 0; img[15:186, 279:280] = 0
    img[15:16, 20:280] = 0; img[185:186, 20:280] = 0
    x0, y0, x1, y1 = detect_neatline(img)
    assert abs(x0 - 20) <= 3 and abs(x1 - 279) <= 3
    assert abs(y0 - 15) <= 3 and abs(y1 - 185) <= 3
```

- [ ] **Step 2: Correr para verificar que fallan**

Run: `& "C:/Users/.../Python312/python.exe" -X utf8 -m pytest tools/test_lib_reproc.py -v`
Expected: FAIL (lib_reproc no existe).

- [ ] **Step 3: Escribir `lib_reproc.py` (transform + neat-line)**

Create `tools/lib_reproc.py`:
```python
"""Reprocesa overlays raster del Maule: reconstruye pixel<->geo desde
LatLonBox+rotacion (ya presente en cada KMZ), detecta el neat-line para separar
mapa de leyenda, y warpea el mapa a plate-carree (Leaflet ignora rotacion)."""
import math, zipfile, re
import numpy as np, cv2
from PIL import Image


def box_from_latlonbox(north, south, east, west, rot_deg):
    """Devuelve el dict BOX con centro precalculado."""
    lonc = (east + west) / 2.0
    latc = (north + south) / 2.0
    return dict(n=north, s=south, e=east, w=west, rot=rot_deg, lonc=lonc, latc=latc)


def pixel_to_geo(px, py, box, W, H):
    """(px,py) en [0..W-1]x[0..H-1] -> (lon,lat). Rotacion CCW sobre el centro."""
    lonc, latc = box["lonc"], box["latc"]
    cosl = math.cos(math.radians(latc))
    # lon/lat sin rotar dentro de la caja [W,E]x[S,N]
    lon0 = box["w"] + (px / (W - 1)) * (box["e"] - box["w"])
    lat0 = box["n"] - (py / (H - 1)) * (box["n"] - box["s"])
    xm = (lon0 - lonc) * cosl
    ym = (lat0 - latc)
    rho = math.radians(box["rot"])
    c, s = math.cos(rho), math.sin(rho)
    xr = xm * c - ym * s
    yr = xm * s + ym * c
    return lonc + xr / cosl, latc + yr


def geo_to_pixel(lon, lat, box, W, H):
    """Inverso de pixel_to_geo."""
    lonc, latc = box["lonc"], box["latc"]
    cosl = math.cos(math.radians(latc))
    xr = (lon - lonc) * cosl
    yr = (lat - latc)
    rho = math.radians(box["rot"])
    c, s = math.cos(rho), math.sin(rho)
    # rotacion inversa (-rho)
    xm = xr * c + yr * s
    ym = -xr * s + yr * c
    lon0 = lonc + xm / cosl
    lat0 = latc + ym
    px = (lon0 - box["w"]) / (box["e"] - box["w"]) * (W - 1)
    py = (box["n"] - lat0) / (box["n"] - box["s"]) * (H - 1)
    return px, py


def _group(idx, gap):
    if len(idx) == 0:
        return []
    g = []; s = idx[0]; pv = idx[0]
    for i in idx[1:]:
        if i - pv > gap:
            g.append((s + pv) // 2); s = i
        pv = i
    g.append((s + pv) // 2)
    return g


def detect_neatline(img):
    """Detecta el marco negro interior. Devuelve (x0,y0,x1,y1) en pixeles.
    Si hay marco doble, toma el interior; si es simple, el unico detectado."""
    H, W = img.shape[:2]
    R, G, B = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    black = (R < 70) & (G < 70) & (B < 70)
    rows = sorted(_group(np.where(black.sum(1) > 0.35 * W)[0], 8))
    cols = sorted(_group(np.where(black.sum(0) > 0.35 * H)[0], 8))
    if len(cols) < 2 or len(rows) < 2:
        raise ValueError("no se detecto neat-line (marco negro insuficiente)")
    if len(cols) >= 4 and len(rows) >= 4:
        x0, x1, y0, y1 = cols[1], cols[-2], rows[1], rows[-2]   # marco doble -> interior
    else:
        x0, x1, y0, y1 = cols[0], cols[-1], rows[0], rows[-1]   # marco simple
    return x0, y0, x1, y1


def load_kmz(kmz_path):
    """Devuelve (img_rgb, W, H, box). Lee el PNG y la LatLonBox del doc.kml."""
    z = zipfile.ZipFile(kmz_path)
    kml = z.read("doc.kml").decode("utf-8")
    png = next(n for n in z.namelist() if n.lower().endswith((".png", ".jpg", ".jpeg")))
    data = z.read(png); z.close()
    import io
    img = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    m = re.search(r"<north>(.*?)</north>.*?<south>(.*?)</south>.*?"
                  r"<east>(.*?)</east>.*?<west>(.*?)</west>", kml, re.S)
    rotm = re.search(r"<rotation>(.*?)</rotation>", kml, re.S)
    if not m:
        raise ValueError(f"{kmz_path}: sin LatLonBox")
    N, S, E, Wc = map(float, m.groups())
    rot = float(rotm.group(1)) if rotm else 0.0
    box = box_from_latlonbox(N, S, E, Wc, rot)
    H, W = img.shape[:2]
    return img, W, H, box


def warp_map(img, rect, box, cap=3000):
    """Warpea SOLO el rectangulo del mapa a plate-carree. rect=(x0,y0,x1,y1).
    Devuelve (rgba, bounds_dict). bounds en WGS84, rotacion 0."""
    x0, y0, x1, y1 = rect
    H, W = img.shape[:2]
    corners = [pixel_to_geo(x0, y0, box, W, H), pixel_to_geo(x1, y0, box, W, H),
               pixel_to_geo(x1, y1, box, W, H), pixel_to_geo(x0, y1, box, W, H)]
    lons = [p[0] for p in corners]; lats = [p[1] for p in corners]
    west, east = min(lons), max(lons)
    south, north = min(lats), max(lats)
    OW = min(x1 - x0, cap)
    OH = int(round(OW * (north - south) / (east - west)))
    lon_g = west + (np.arange(OW) / (OW - 1)) * (east - west)
    lat_g = north - (np.arange(OH) / (OH - 1)) * (north - south)
    LON, LAT = np.meshgrid(lon_g, lat_g)
    # geo -> pixel vectorizado
    lonc, latc = box["lonc"], box["latc"]
    cosl = math.cos(math.radians(latc))
    rho = math.radians(box["rot"]); c, s = math.cos(rho), math.sin(rho)
    xr = (LON - lonc) * cosl; yr = (LAT - latc)
    xm = xr * c + yr * s; ym = -xr * s + yr * c
    lon0 = lonc + xm / cosl; lat0 = latc + ym
    mx = ((lon0 - box["w"]) / (box["e"] - box["w"]) * (W - 1)).astype(np.float32)
    my = ((box["n"] - lat0) / (box["n"] - box["s"]) * (H - 1)).astype(np.float32)
    warped = cv2.remap(img, mx, my, cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    inside = (mx >= x0) & (mx <= x1) & (my >= y0) & (my <= y1)
    rgba = np.dstack([warped, (inside * 255).astype(np.uint8)])
    bounds = dict(n=round(north, 6), s=round(south, 6), e=round(east, 6), w=round(west, 6))
    return rgba, bounds


def detect_legend_side(img, rect):
    """Heuristica: lado del neat-line con mas contenido no-blanco fuera del marco.
    Devuelve 'right' | 'below' | 'left' | 'above'."""
    x0, y0, x1, y1 = rect
    H, W = img.shape[:2]
    nonwhite = (img.min(axis=2) < 235)
    areas = {
        "right": nonwhite[y0:y1, x1:W].sum() if x1 < W - 5 else 0,
        "below": nonwhite[y1:H, x0:x1].sum() if y1 < H - 5 else 0,
        "left":  nonwhite[y0:y1, 0:x0].sum() if x0 > 5 else 0,
        "above": nonwhite[0:y0, x0:x1].sum() if y0 > 5 else 0,
    }
    return max(areas, key=areas.get)


def crop_legend(img, rect, side):
    """Recorta la franja de leyenda segun el lado."""
    x0, y0, x1, y1 = rect
    H, W = img.shape[:2]
    pad = 6
    if side == "right":
        return img[0:H, min(x1 + pad, W):W]
    if side == "below":
        return img[min(y1 + pad, H):H, 0:W]
    if side == "left":
        return img[0:H, 0:max(x0 - pad, 0)]
    return img[0:max(y0 - pad, 0), 0:W]
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `& "C:/Users/.../Python312/python.exe" -X utf8 -m pytest tools/test_lib_reproc.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/lib_reproc.py tools/test_lib_reproc.py
git commit -m "feat: lib_reproc transform pixel<->geo + neat-line + warp (tests)"
```

---

## Task 3: CLI `reprocesar.py` + piloto F19

**Files:**
- Create: `tools/reprocesar.py`

- [ ] **Step 1: Escribir el CLI**

Create `tools/reprocesar.py`:
```python
"""Reprocesa un KMZ del Maule a overlay web + leyenda JPG.
Uso: python reprocesar.py <categoria> <id> [--side right|below|left|above] [--no-legend]
Lee el KMZ de sernageomin_maule\\repo\\capas\\<categoria>\\<id>.kmz.
Escribe overlays/<id>.webp, leyendas/<id>.jpg e imprime la entrada capas.json."""
import sys, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image
from lib_reproc import load_kmz, detect_neatline, warp_map, detect_legend_side, crop_legend

SRC = Path(r"C:\Users\carlos.venegas\Documents\sernageomin_maule\repo\capas")
ROOT = Path(__file__).resolve().parent.parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("categoria")
    ap.add_argument("id")
    ap.add_argument("--side", default=None)
    ap.add_argument("--no-legend", action="store_true")
    a = ap.parse_args()

    kmz = SRC / a.categoria / f"{a.id}.kmz"
    img, W, H, box = load_kmz(kmz)
    rect = detect_neatline(img)
    print(f"neat-line px: {rect}  img {W}x{H}  rot={box['rot']:.4f}")

    rgba, bounds = warp_map(img, rect, box)
    (ROOT / "overlays").mkdir(exist_ok=True)
    ov = f"overlays/{a.id}.webp"
    Image.fromarray(rgba).save(ROOT / ov, "WEBP", quality=88, method=6)
    print(f"overlay -> {ov}  {rgba.shape[1]}x{rgba.shape[0]}  bounds={bounds}")

    leyenda = None
    if not a.no_legend:
        side = a.side or detect_legend_side(img, rect)
        leg = crop_legend(img, rect, side)
        if leg.size and min(leg.shape[:2]) > 10:
            (ROOT / "leyendas").mkdir(exist_ok=True)
            leyenda = f"leyendas/{a.id}.jpg"
            Image.fromarray(leg).save(ROOT / leyenda, "JPEG", quality=85)
            print(f"leyenda ({side}) -> {leyenda}  {leg.shape[1]}x{leg.shape[0]}")
        else:
            print(f"AVISO: leyenda lado '{side}' vacia; revisar --side manual")

    entry = dict(id=a.id, categoria=a.categoria, titulo=a.id, fuente="", anio="",
                 escala="", autor="", informe="", bounds=bounds, overlay=ov,
                 leyenda=leyenda, opacidad=1.0, recortado=True)
    print("ENTRY " + json.dumps(entry, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr el piloto F19 y verificar salida**

Run:
```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin/tools"
& "C:/Users/.../Python312/python.exe" -X utf8 reprocesar.py geologia geo_F19_pichibelco
```
Expected: imprime `neat-line px`, `overlay -> overlays/geo_F19_pichibelco.webp` con bounds cercanos a N≈-35.48 S≈-36.23 E≈-71.31 W≈-72.52 (comparar con la LatLonBox original), `leyenda (...)`, y una línea `ENTRY {...}`. Los archivos `.webp` y `.jpg` existen.

- [ ] **Step 3: Verificar alineación por punto conocido**

Cauquenes está en ~(-72.32, -35.97). Confirmar que cae dentro del bounds impreso:
Run: `& "C:/Users/.../Python312/python.exe" -X utf8 -c "b=__import__('json').load(open('../capas.json')); print('ver ENTRY manual')"`
Verificación manual: `-72.52 <= -72.32 <= -71.31` y `-36.23 <= -35.97 <= -35.48` → dentro. OK.

- [ ] **Step 4: Inspección visual del overlay y la leyenda**

Abrir `overlays/geo_F19_pichibelco.webp` y `leyendas/geo_F19_pichibelco.jpg` con el visor de imágenes (o `Image.open(...).show()`). Confirmar: el overlay NO contiene la leyenda; la leyenda NO contiene el mapa. Si el lado de la leyenda salió mal, re-correr con `--side right|below`.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin"
git add tools/reprocesar.py overlays/geo_F19_pichibelco.webp leyendas/geo_F19_pichibelco.jpg
git commit -m "feat: CLI reprocesar + piloto F19 (overlay recortado + leyenda JPG)"
```

---

## Task 4: Visor `index.html` (Leaflet) — esqueleto que lee `capas.json`

**Files:**
- Create: `index.html`

- [ ] **Step 1: Escribir el visor completo**

Create `index.html`:
```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<title>Geo Repo Maule — SERNAGEOMIN</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html,body{margin:0;height:100%;font-family:'Segoe UI',Arial,sans-serif}
  #app{display:flex;height:100%}
  #panel{width:320px;min-width:320px;background:#f4f7fa;border-right:1px solid #d5dee7;
         overflow-y:auto;padding:12px}
  #panel h1{font-size:16px;color:#1a5276;margin:4px 0 12px}
  #map{flex:1}
  details{background:#fff;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:8px}
  summary{cursor:pointer;padding:8px 10px;font-weight:600;color:#1a5276}
  .capa{padding:6px 10px;border-top:1px solid #eef2f6}
  .capa label{display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer}
  .capa .ctl{display:none;margin-top:6px;gap:8px;align-items:center}
  .capa.on .ctl{display:flex}
  .capa input[type=range]{flex:1}
  .capa button{font-size:12px;border:1px solid #cbd5e1;background:#fff;border-radius:6px;
               padding:2px 8px;cursor:pointer}
  #legmodal{position:fixed;inset:0;background:rgba(0,0,0,.7);display:none;
            align-items:center;justify-content:center;z-index:2000}
  #legmodal.open{display:flex}
  #legwrap{background:#fff;border-radius:8px;max-width:92vw;max-height:92vh;overflow:hidden;
           position:relative}
  #legwrap img{display:block;transform-origin:0 0;touch-action:none;user-select:none;max-width:none}
  #legclose{position:absolute;top:6px;right:8px;z-index:5;background:#fff;border:1px solid #cbd5e1;
            border-radius:6px;padding:2px 8px;cursor:pointer}
</style>
</head>
<body>
<div id="app">
  <div id="panel"><h1>Geología Región del Maule</h1><div id="capas"></div></div>
  <div id="map"></div>
</div>
<div id="legmodal"><div id="legwrap"><button id="legclose">✕ Cerrar</button><img id="legimg"/></div></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const CATS = [["geologia","🗺️ Geología"],["aplicada","⚠️ Aplicada"],
  ["historico","📜 Histórico"],["academico","🎓 Académicos"],["hillshade","🏔️ Hillshade"]];
const map = L.map('map',{center:[-35.7,-71.6],zoom:8});
const bases = {
  "Satelital": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Esri'}),
  "Topográfico": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Esri'}),
  "OpenTopoMap": L.tileLayer('https://a.tile.opentopomap.org/{z}/{x}/{y}.png',{maxZoom:17,attribution:'OpenTopoMap'})
};
bases["Satelital"].addTo(map);
L.control.layers(bases,null,{position:'topright'}).addTo(map);
CATS.forEach(([c],i)=>map.createPane('pane_'+c).style.zIndex = 300 + i*10);

const overlays = {}; // id -> L.imageOverlay

function crearCapa(cont, c){
  const div=document.createElement('div'); div.className='capa';
  const b=c.bounds, bounds=[[b.s,b.w],[b.n,b.e]];
  div.innerHTML =
    `<label><input type="checkbox"> ${c.titulo}</label>
     <div class="ctl">
       <input type="range" min="0" max="1" step="0.05" value="${c.opacidad}">
       ${c.leyenda?'<button class="leg">ⓘ Leyenda</button>':''}
     </div>`;
  const chk=div.querySelector('input[type=checkbox]');
  const rng=div.querySelector('input[type=range]');
  chk.addEventListener('change',()=>{
    if(chk.checked){
      if(!overlays[c.id]) overlays[c.id]=L.imageOverlay(c.overlay,bounds,
        {opacity:+rng.value,pane:'pane_'+c.categoria});
      overlays[c.id].addTo(map); div.classList.add('on');
    }else if(overlays[c.id]){ overlays[c.id].remove(); div.classList.remove('on'); }
  });
  rng.addEventListener('input',()=>{ if(overlays[c.id]) overlays[c.id].setOpacity(+rng.value); });
  const legBtn=div.querySelector('.leg');
  if(legBtn) legBtn.addEventListener('click',()=>abrirLeyenda(c.leyenda));
  cont.appendChild(div);
}

fetch('capas.json').then(r=>r.json()).then(capas=>{
  const cont=document.getElementById('capas');
  CATS.forEach(([cat,label])=>{
    const grupo=capas.filter(c=>c.categoria===cat);
    if(!grupo.length) return;
    const d=document.createElement('details');
    d.innerHTML=`<summary>${label} (${grupo.length})</summary>`;
    grupo.forEach(c=>crearCapa(d,c));
    cont.appendChild(d);
  });
});
</script>
<script src="viewer_legend.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verificar en el navegador con la capa piloto**

Asegurarse de que `capas.json` tenga la entrada de F19 (agregarla desde la línea `ENTRY` del Task 3 si aún no está). Abrir el visor con el navegador MCP:
- `preview_start` con `{url:"file:///C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin/index.html"}` (o servir con `python -m http.server` desde la carpeta y navegar a `http://localhost:8000/`).
- `read_page` → confirmar que aparece el grupo "🗺️ Geología (1)" con el checkbox de F19.
- `read_console_messages onlyErrors:true` → sin errores de fetch/Leaflet.

Nota: por CORS, `fetch('capas.json')` desde `file://` puede fallar en algunos navegadores → usar `python -m http.server 8000` en la carpeta del repo y navegar a `http://localhost:8000/`.

- [ ] **Step 3: Encender la capa y confirmar alineación**

Con `computer` hacer click en el checkbox de F19; `computer {action:"screenshot"}` → el overlay del mapa geológico cae sobre Cauquenes alineado con la imagen satelital. Mover el slider de opacidad y confirmar que cambia.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: visor Leaflet lee capas.json (categorias, toggle, opacidad)"
```

---

## Task 5: Modal de leyenda con zoom/pan (`viewer_legend.js`)

**Files:**
- Create: `viewer_legend.js`

- [ ] **Step 1: Escribir el modal con zoom/pan (Pointer Events + rueda)**

Create `viewer_legend.js`:
```javascript
// Modal de leyenda con zoom (rueda + doble click) y pan (arrastre). Escritorio.
(function(){
  const modal=document.getElementById('legmodal');
  const img=document.getElementById('legimg');
  const close=document.getElementById('legclose');
  let scale=1, tx=0, ty=0, dragging=false, lx=0, ly=0;
  function apply(){ img.style.transform=`translate(${tx}px,${ty}px) scale(${scale})`; }
  window.abrirLeyenda=function(src){
    img.src=src; scale=1; tx=0; ty=0; apply(); modal.classList.add('open');
  };
  function cerrar(){ modal.classList.remove('open'); img.src=''; }
  close.addEventListener('click',cerrar);
  modal.addEventListener('click',e=>{ if(e.target===modal) cerrar(); });
  img.addEventListener('wheel',e=>{
    e.preventDefault();
    const f=e.deltaY<0?1.15:1/1.15;
    scale=Math.min(8,Math.max(0.2,scale*f)); apply();
  },{passive:false});
  img.addEventListener('dblclick',e=>{ e.preventDefault(); scale=scale>1?1:2; tx=0; ty=0; apply(); });
  img.addEventListener('pointerdown',e=>{ dragging=true; lx=e.clientX; ly=e.clientY;
    try{img.setPointerCapture(e.pointerId);}catch(_){} });
  img.addEventListener('pointermove',e=>{ if(!dragging) return;
    tx+=e.clientX-lx; ty+=e.clientY-ly; lx=e.clientX; ly=e.clientY; apply(); });
  img.addEventListener('pointerup',()=>{ dragging=false; });
  img.addEventListener('pointercancel',()=>{ dragging=false; });
})();
```

- [ ] **Step 2: Verificar el modal en el navegador**

Recargar el visor (servido por `http.server`). Encender F19, click en "ⓘ Leyenda" → `computer {action:"screenshot"}` confirma que el modal abre con la leyenda. Probar rueda (zoom) y arrastre (pan) con `computer` scroll/drag; click en "✕ Cerrar" cierra.

- [ ] **Step 3: Commit**

```bash
git add viewer_legend.js
git commit -m "feat: modal de leyenda con zoom/pan (rueda + arrastre)"
```

---

## Task 6: Segundo piloto (F21_raster) + poblar `capas.json`

**Files:**
- Modify: `capas.json`

- [ ] **Step 1: Reprocesar F21_raster**

Run:
```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin/tools"
& "C:/Users/.../Python312/python.exe" -X utf8 reprocesar.py geologia geo_F21_raster
```
Expected: overlay + leyenda generados; línea `ENTRY {...}`.

- [ ] **Step 2: Agregar ambas entradas a `capas.json` con metadata real**

Editar `capas.json` para que sea un array con las 2 entradas (F19 y F21_raster), completando `titulo`, `fuente`, `anio`, `escala`, `autor` desde la memoria del proyecto (`~/.claude/memories/project_sernageomin_maule_sig.md`, sección "Productos publicados"). Ejemplo F19:
```json
{
  "id": "geo_F19_pichibelco", "categoria": "geologia",
  "titulo": "Geología Pichibelco-Cauquenes (CGCH GB-214)",
  "fuente": "SERNAGEOMIN — CGCH GB-214", "anio": "", "escala": "1:100.000",
  "autor": "", "informe": "GB-214",
  "bounds": { "n": -35.478, "s": -36.234, "e": -71.308, "w": -72.521 },
  "overlay": "overlays/geo_F19_pichibelco.webp",
  "leyenda": "leyendas/geo_F19_pichibelco.jpg",
  "opacidad": 1.0, "recortado": true
}
```
(usar el `bounds` real impreso por `reprocesar.py`, no estos aproximados).

- [ ] **Step 3: Validar `capas.json`**

Run: `& "C:/Users/.../Python312/python.exe" -X utf8 tools/validar_capas.py capas.json`
Expected: `OK: 2 capas validas`.

- [ ] **Step 4: Verificar ambas capas en el visor**

Recargar el visor; el grupo Geología muestra "(2)"; encender ambas, confirmar alineación por screenshot.

- [ ] **Step 5: Commit**

```bash
git add capas.json overlays/geo_F21_raster.webp leyendas/geo_F21_raster.jpg
git commit -m "feat: segundo piloto F21_raster + capas.json con 2 capas validadas"
```

---

## Task 7: Pass-through de hillshade (23) + académicos (8)

**Files:**
- Create: `tools/copiar_pass_through.py`

Hillshade y académicos NO se recortan. Se convierte su PNG a WebP (peso) y se registran con el `bounds` derivado de su LatLonBox (rotación tratada como 0 para el bounds — aceptable: hillshade es relieve, académicos ya traen leyenda horneada y su encaje aproximado es suficiente). `recortado:false`, `leyenda:null` (hillshade) o `leyenda:null` con leyenda horneada dentro del overlay (académicos).

- [ ] **Step 1: Escribir el conversor pass-through**

Create `tools/copiar_pass_through.py`:
```python
"""Convierte KMZ de hillshade/academicos a WebP sin recorte y genera entradas capas.json.
Uso: python copiar_pass_through.py <categoria> <destino_dir>
Registra bounds desde LatLonBox (rot->bounds tal cual: north/south/east/west)."""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image
from lib_reproc import load_kmz

SRC = Path(r"C:\Users\carlos.venegas\Documents\sernageomin_maule\repo\capas")
ROOT = Path(__file__).resolve().parent.parent

def main():
    categoria = sys.argv[1]           # "hillshade" | "academico"
    dest = sys.argv[2]                # "hillshade" | "academicos"
    outdir = ROOT / dest; outdir.mkdir(exist_ok=True)
    entradas = []
    for kmz in sorted((SRC / categoria).glob("*.kmz")):
        cid = kmz.stem
        img, W, H, box = load_kmz(kmz)
        Image.fromarray(img).save(outdir / f"{cid}.webp", "WEBP", quality=85, method=6)
        entradas.append(dict(
            id=cid, categoria=categoria, titulo=cid, fuente="", anio="", escala="",
            autor="", informe="",
            bounds=dict(n=box["n"], s=box["s"], e=box["e"], w=box["w"]),
            overlay=f"{dest}/{cid}.webp", leyenda=None,
            opacidad=1.0 if categoria == "academico" else 0.6, recortado=False))
        print(f"{cid} -> {dest}/{cid}.webp  bounds n={box['n']:.4f} s={box['s']:.4f}")
    print("ENTRIES " + json.dumps(entradas, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr para hillshade y académicos**

Run:
```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin/tools"
& "C:/Users/.../Python312/python.exe" -X utf8 copiar_pass_through.py hillshade hillshade
& "C:/Users/.../Python312/python.exe" -X utf8 copiar_pass_through.py academico academicos
```
Expected: 23 `.webp` en `hillshade/`, 8 en `academicos/`, dos líneas `ENTRIES [...]`.

- [ ] **Step 3: Fusionar las entradas en `capas.json` y validar**

Agregar las 31 entradas (de las líneas `ENTRIES`) al array `capas.json` (completar `titulo` legible de académicos desde la memoria; hillshade `titulo` = "Hillshade "+carta, ej. "Hillshade F07").
Run: `& "C:/Users/.../Python312/python.exe" -X utf8 tools/validar_capas.py capas.json`
Expected: `OK: 33 capas validas` (2 pilotos + 31).

- [ ] **Step 4: Verificar en el visor**

Recargar; aparecen grupos Académicos (8) y Hillshade (23). Encender un hillshade (opacidad 0.6) y un académico; confirmar por screenshot que caen sobre el Maule.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin"
git add tools/copiar_pass_through.py hillshade/ academicos/ capas.json
git commit -m "feat: pass-through hillshade (23) + academicos (8) a WebP + capas.json"
```

---

## Task 8: Reprocesar los 22 mapas raster restantes (delegable a subagentes)

Para cada mapa: correr `reprocesar.py`, verificar overlay/leyenda visualmente, agregar la entrada a `capas.json` con metadata real, validar. **Estos mapas son mecánicos y aptos para subagentes Sonnet** (ver `feedback-delegar-tareas-repetitivas-subagentes`): encolar todos en el MISMO subagente para no chocar commits al repo. Tabla de trabajo (el `--side` se confirma visualmente; empezar sin `--side` y dejar que `detect_legend_side` decida):

| # | categoria | id | notas |
|---|---|---|---|
| 1 | geologia | geo_F22_rio_claro_IR110 | IR-110 |
| 2 | geologia | geo_F28_carta64 | CG N°64 |
| 3 | geologia | geo_lagunamaule_LDMField_NE | Boletín 63; leyenda puede ir dentro |
| 4 | geologia | geo_lagunamaule_LDMField_NW | comparte leyenda con los cuartos LM |
| 5 | geologia | geo_lagunamaule_LDMField_SE | |
| 6 | geologia | geo_lagunamaule_LDMField_SW | |
| 7 | geologia | geo_tinguiririca_teno | IR-89 |
| 8 | aplicada | geof_bouguer_geof115 | UTM 18S (oeste 72°O); leyenda propia |
| 9 | aplicada | geof_residual_geof115 | UTM 18S |
| 10 | aplicada | geoq_IR114_mataquito_sedimentosPEC | figura PEC |
| 11 | aplicada | hidrogeoq_F19_cauquenes | IR-84 |
| 12 | aplicada | lic_curico_2010 | licuefacción |
| 13 | aplicada | rem_F09_curico_2010 | remociones |
| 14 | aplicada | rem_F13_constitucion_2010 | remociones |
| 15 | aplicada | rem_duao_iloca_2010 | remociones |
| 16 | aplicada | rme15_yacimientos_rmi_maule | regional grande; leyenda propia |
| 17 | aplicada | tsu_constitucion_2010 | tsunami |
| 18 | aplicada | tsu_duao_iloca_2010 | tsunami |
| 19 | aplicada | vol_peligros_cerro_azul_quizapu_GAMB23 | volcanes |
| 20 | aplicada | vol_peligros_descabezado_quizapu_GAMB39 | volcanes |
| 21 | historico | escobar_1977_chile | histórico; se muestra completo |
| 22 | historico | gfv_andes_35_38 | histórico |

- [ ] **Step 1: Procesar cada mapa (repetir por fila)**

Para la fila N:
```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin/tools"
& "C:/Users/.../Python312/python.exe" -X utf8 reprocesar.py <categoria> <id>
```
- Si la leyenda sale vacía o mal recortada, re-correr con `--side right|below|left|above`.
- Si el mapa trae la leyenda **inserta dentro** del neat-line (ej. algún cuarto Laguna del Maule), correr con `--no-legend` y `leyenda:null` (queda horneada en el overlay, fiel al impreso).

- [ ] **Step 2: Inspección visual por mapa**

Abrir `overlays/<id>.webp` y `leyendas/<id>.jpg`. Confirmar overlay sin leyenda y leyenda sin mapa. Repetir Step 1 con `--side` si hace falta.

- [ ] **Step 3: Agregar entrada a `capas.json`**

Copiar la línea `ENTRY {...}` y completar `titulo/fuente/anio/escala/autor` desde la memoria (`project_sernageomin_maule_sig.md`, sección "Productos publicados"). Añadir al array.

- [ ] **Step 4: Validar tras cada lote**

Run: `& "C:/Users/.../Python312/python.exe" -X utf8 tools/validar_capas.py capas.json`
Expected: `OK: N capas validas` (33 → 55 al terminar las 22).

- [ ] **Step 5: Commit por lote (cada 4-5 mapas)**

```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin"
git add overlays/ leyendas/ capas.json
git commit -m "feat: reprocesa mapas raster <rango> (overlay + leyenda JPG)"
```

- [ ] **Step 6: Verificación final en el visor**

Recargar el visor; encender una muestra de cada categoría (geología, aplicada, histórico) y confirmar por screenshot que caen alineados sobre el satelital. `read_console_messages onlyErrors:true` sin errores.

---

## Task 9: README + publicación en GitHub Pages

**Files:**
- Create: `README.md`

- [ ] **Step 1: Escribir el README**

Create `README.md`:
```markdown
# Geo_Repo_Maule_Sernageomin

Visor web de la cartografía geológica de la Región del Maule (SERNAGEOMIN).
Overlays raster recortados (mapa) + leyendas aparte, hillshade y trabajos académicos,
sobre base satelital/topográfica. Escritorio.

**Publicado:** https://cvenegas-sernageomin.github.io/Geo_Repo_Maule_Sernageomin/

## Estructura
- `index.html` + `viewer_legend.js` — visor Leaflet (lee `capas.json` en vivo).
- `capas.json` — índice de capas.
- `overlays/`, `leyendas/`, `hillshade/`, `academicos/` — assets.
- `tools/` — pipeline de reprocesamiento (Python 3.12: cv2, pyproj, Pillow).

## Agregar/actualizar un mapa
1. `python tools/reprocesar.py <categoria> <id>` (Python 3.12, `-X utf8`).
2. Verificar overlay/leyenda; agregar la entrada a `capas.json`.
3. `python tools/validar_capas.py capas.json` → commit + push.
El visor NO se toca (lee `capas.json` en vivo).
```

- [ ] **Step 2: Crear el repo en GitHub y publicar**

Seguir el patrón de `reference-publicar-pwa-github-pages` (cuenta `cvenegas-sernageomin`, login por navegador; `gh` no está en PATH):
```bash
cd "C:/Users/carlos.venegas/Documents/Geo_Repo_Maule_Sernageomin"
git add README.md && git commit -m "docs: README"
git branch -M main
git remote add origin https://github.com/cvenegas-sernageomin/Geo_Repo_Maule_Sernageomin.git
git push -u origin main
```
Crear el repo vacío en github.com primero (público) y activar Pages sobre `main` / root. Confirmar con el usuario antes del push (acción de publicación).

- [ ] **Step 3: Verificar el sitio publicado**

Navegar a `https://cvenegas-sernageomin.github.io/Geo_Repo_Maule_Sernageomin/` (esperar ~40s de deploy). `read_page` → panel de capas visible; encender una capa de cada categoría; `read_console_messages onlyErrors:true` sin errores 404 de assets.

- [ ] **Step 4: Commit final / tag**

```bash
git tag v1 && git push origin v1
```

---

## Self-Review — cobertura del spec

- **Visor web escritorio, online, sin PWA** → Task 4/5 (index.html + viewer_legend.js, sin sw.js). ✅
- **Repo autocontenido en GitHub Pages** → Task 1 (scaffold), Task 9 (publicación). ✅
- **Reprocesar 24 raster (recorte overlay WebP + leyenda JPG + plate-carrée)** → Task 2/3 (lib+CLI), Task 6 (F21_raster), Task 8 (22 restantes). F19 en Task 3. Total 24. ✅
- **Hillshade (23) + académicos (8) tal cual** → Task 7. ✅
- **Fuera: sismos, fallas, móvil** → no aparecen en ningún task. ✅
- **`capas.json` que el visor lee en vivo** → Task 1 (esquema/validador), consumido en Task 4. ✅
- **Formatos: overlay WebP, leyenda JPG** → Task 3 (`.save(...,"WEBP")` / `"JPEG"`). ✅
- **Entorno Python312 + -X utf8** → indicado en cada comando. ✅
- **Delegación a subagentes** → Task 8 marcado como delegable, encolar en el mismo subagente. ✅

Consistencia de tipos: `capas.json` usa siempre los mismos campos (`id, categoria, titulo, fuente, anio, escala, autor, informe, bounds{n,s,e,w}, overlay, leyenda, opacidad, recortado`); `validar_capas.py`, `reprocesar.py`, `copiar_pass_through.py` e `index.html` los referencian idénticos. `pixel_to_geo`/`geo_to_pixel`/`detect_neatline`/`warp_map`/`load_kmz`/`detect_legend_side`/`crop_legend` definidos en Task 2 y usados con las mismas firmas en Task 3/7.
```
