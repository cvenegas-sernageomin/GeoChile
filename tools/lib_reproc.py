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
    """Caja envolvente del neat-line del mapa: los EXTREMOS de las lineas negras
    casi-completas. Las hojas SERNAGEOMIN tienen neat-line simple + tablas internas
    (p.ej. la columna cronoestratigrafica pegada al mapa), asi que NO se asume
    "marco doble / interior" (eso recortaba el mapa a una franja). Devuelve
    (x0,y0,x1,y1). Lanza ValueError si el rect es implausible (pasar --rect manual).

    Nota: asume que el unico elemento con lineas negras casi-completas es el marco
    del mapa (la leyenda/marginalia no supera el umbral 0.35). Si una hoja trae un
    borde que abarca toda la lamina (mapa+leyenda), los extremos daran la lamina
    completa -> usar --rect manual."""
    H, W = img.shape[:2]
    R, G, B = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    black = (R < 70) & (G < 70) & (B < 70)
    rows = sorted(_group(np.where(black.sum(1) > 0.35 * W)[0], 8))
    cols = sorted(_group(np.where(black.sum(0) > 0.35 * H)[0], 8))
    if len(cols) < 2 or len(rows) < 2:
        raise ValueError("no se detecto neat-line (marco negro insuficiente)")
    x0, y0, x1, y1 = cols[0], rows[0], cols[-1], rows[-1]
    if (x1 - x0) < 0.15 * W or (y1 - y0) < 0.15 * H:
        raise ValueError(f"neat-line sospechoso: rect {x1-x0}x{y1-y0} en img {W}x{H}; "
                         f"revisar la hoja y pasar --rect x0,y0,x1,y1 manual")
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
