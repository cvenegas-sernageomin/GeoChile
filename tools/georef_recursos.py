"""Láminas «Mapa de Recursos Minerales» (PDF) -> overlays de Geología Económica para el visor GeoChile.

Uso (desde la raíz del repo):
    python -I -X utf8 tools/georef_recursos.py M85 [M82 ...] [--trabajo DIR] [--verificar]

Qué hace por lámina (ver HOJAS):
  1. saca la imagen de la lámina del PDF del paquete (zip de publicaciones-sernageomin\\Recursos Minerales);
  2. toma las 4 esquinas del marco interior (cruces de grados rotuladas, medidas con tools/medir_esquinas en pixeles) y las
     lleva por homografía a un rectángulo geográfico: el marco ES el cuadrángulo de grados redondos (MD_MAPAS) en el datum
     de la hoja (PSAD56), no una grilla UTM;
  3. convierte las esquinas PSAD56 -> WGS84 (PROJ 4248->4326, igual que las cartas del repo) y escribe overlays/rm_<M>.webp;
  4. la leyenda es la lámina completa con el mapa borrado y recortada al contenido (leyendas/rm_<M>.jpg).

Trampas verificadas:
  * el marco NO es un rectángulo en píxeles (los bordes difieren 4–7 px): usar las 4 esquinas, no una caja;
  * en MD_MAPAS los rótulos N/S de latitud vienen invertidos en algunas hojas (M85): ordenar, no confiar en el rótulo;
  * M81 trae la imagen girada (página /Rotate 90);
  * la tabla de atributos de los paquetes está en WGS84 (PROYECCION=WGS84H19) aunque la lámina imprima PSAD56: verificado con
    --verificar (los símbolos de yacimientos caen sobre los puntos de la tabla pasados PSAD56 -> pixel).
"""
import argparse
import json
import pathlib
import re
import sys
import tempfile
import warnings
import zipfile

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
warnings.filterwarnings("ignore")
import pymupdf  # noqa: E402
from pyproj import CRS, Transformer  # noqa: E402

import exportar_recursos_a_datos as R  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
RM_DIR = R.RM_DIR
PS_GEO = CRS.from_proj4("+proj=longlat +ellps=intl +towgs84=-270,183,-390,0,0,0,0 +no_defs")  # hoja PSAD56 <- tabla WGS84
A_WGS = Transformer.from_crs(4248, 4326, always_xy=True)                                       # PSAD56 -> WGS84 (como las cartas)
A_HOJA = Transformer.from_crs(4326, PS_GEO, always_xy=True)
CAP = 3000
CRLF = chr(13) + chr(10)

# esquinas del marco interior [TL, TR, BR, BL] en pixeles de la imagen (tras girar), límites en grados PSAD56 (S/N, W/E)
HOJAS = {
    "M81": dict(pagina=18, esq=[(348, 529), (9201.5, 552), (9176.5, 7130), (327, 7103)],
                lim=dict(n=-26.0, s=-26.5, w=-70.75, e=-70.0), region="Atacama",
                titulo="Yacimientos metalíferos de las Hojas Chañaral y Diego de Almagro"),
    "M82": dict(pagina=21, esq=[(125.2, 183.3), (4034.8, 184.3), (4041.6, 4549.3), (129.3, 4547.1)],
                lim=dict(n=-26.5, s=-27.0, w=-70.5, e=-70.0), region="Atacama",
                titulo="Yacimientos metalíferos de la Hoja Quebrada Salitrosa"),
    "M84": dict(pagina=26, esq=[(132.7, 225.3), (3997.2, 216.7), (3997.6, 4601.4), (134.5, 4604.6)],
                lim=dict(n=-27.5, s=-28.0, w=-70.5, e=-70.0), region="Atacama",
                titulo="Yacimientos metalíferos de la Hoja Los Loros"),
    "M85": dict(pagina=17, esq=[(347.5, 442.8), (4220.0, 449.0), (4226.8, 4825.4), (353.3, 4825.4)],
                lim=dict(n=-27.5, s=-28.0, w=-70.0, e=-69.5), region="Atacama",
                titulo="Yacimientos metalíferos de la Hoja La Guardia"),
    "M86": dict(pagina=23, esq=[(136.0, 224.5), (4018.0, 220.3), (4010.0, 4606.5), (129.1, 4601.9)],
                lim=dict(n=-27.0, s=-27.5, w=-70.0, e=-69.5), region="Atacama",
                titulo="Yacimientos metalíferos de la Hoja Carrera Pinto"),
    # --- láminas vectoriales: el marco sale de las líneas del PDF (bordes ajustados cerca de la posición aproximada) ---
    "M105": dict(pagina=28, vec=dict(W=45.6, E=1220.0, N=73.0, S=1635.3), datum="WGS84",   # SIRGAS ~ WGS84: sin cambio de datum
                 lim=dict(n=-26.5, s=-27.0, w=-70.916667, e=-70.5), region="Atacama",
                 titulo="Yacimientos metalíferos de la Hoja Puerto Flamenco"),
    "M168": dict(pagina=30, vec=dict(W=151.2, E=1504.4, N=150.0, S=1724.5), datum="PSAD56",
                 lim=dict(n=-30.5, s=-31.0, w=-71.0, e=-70.5), region="Coquimbo",
                 titulo="Yacimientos metalíferos del área Monte Patria - El Maqui"),
    "M169": dict(pagina=33, vec=dict(W=95.5, E=1459.5, N=147.0, S=1718.0), datum="PSAD56",
                 lim=dict(n=-30.0, s=-30.5, w=-71.0, e=-70.5), region="Coquimbo",
                 titulo="Yacimientos metalíferos del área Vicuña - Pichasca"),
    "M195": dict(pagina=35, vec=dict(W=64.4, E=1432.7, N=97.1, S=1673.0), datum="PSAD56",
                 lim=dict(n=-29.5, s=-30.0, w=-71.5, e=-71.0), region="Coquimbo",
                 titulo="Yacimientos metalíferos del área La Serena - La Higuera"),
    "M305": dict(pagina=39, vec=dict(W=94.1, E=1462.3, N=95.8, S=1671.6), datum="PSAD56",
                 lim=dict(n=-29.5, s=-30.0, w=-71.0, e=-70.5), region="Coquimbo",
                 titulo="Yacimientos metalíferos del área Condoriaco - Rivadavia"),
}


def esquinas_vectoriales(p, vec, tol=4.0, minlen=100):
    """Esquinas [TL, TR, BR, BL] (puntos PDF, página ya girada) como intersección de los 4 bordes del marco, cada uno ajustado
    por mínimos cuadrados ponderados a los segmentos del dibujo cercanos a la posición aproximada (los bordes pueden ir
    ligeramente inclinados: el marco es el cuadrángulo de grados dibujado sobre la grilla UTM)."""
    Rm = p.rotation_matrix
    V, H = [], []
    for e in p.get_drawings():
        for it in e["items"]:
            if it[0] != "l":
                continue
            a, b = pymupdf.Point(it[1]) * Rm, pymupdf.Point(it[2]) * Rm
            if abs(a.x - b.x) < 1.0 and abs(a.y - b.y) > minlen:
                V.append(((a.x + b.x) / 2, (a.y + b.y) / 2, abs(a.y - b.y)))
            elif abs(a.y - b.y) < 1.0 and abs(a.x - b.x) > minlen:
                H.append(((a.x + b.x) / 2, (a.y + b.y) / 2, abs(a.x - b.x)))

    def ajustar(pts, pos, eje):
        # eje 'v': x = a*y + b ; eje 'h': y = a*x + b ; solo segmentos dentro de la extensión del marco (no paneles vecinos)
        if eje == "v":
            c = [(y, x, l) for x, y, l in pts if abs(x - pos) < tol and vec["N"] - 5 <= y <= vec["S"] + 5]
        else:
            c = [(x, y, l) for x, y, l in pts if abs(y - pos) < tol and vec["W"] - 5 <= x <= vec["E"] + 5]
        t = np.array([q[0] for q in c]); v = np.array([q[1] for q in c]); w = np.array([q[2] for q in c])
        if np.ptp(t) < 0.3 * (vec["S"] - vec["N"] if eje == "v" else vec["E"] - vec["W"]):
            return 0.0, float(np.average(v, weights=w)), len(t), float(w.sum())    # sin extensión para estimar inclinación
        ok = np.ones(len(t), bool)
        for _ in range(4):
            a, b = np.polyfit(t[ok], v[ok], 1, w=w[ok])
            res = np.abs(v - (a * t + b)); ok = res < max(1.2, 2.5 * np.median(res[ok]) + 0.2)
        return a, b, int(ok.sum()), float(w[ok].sum())

    Ws, Es, Ns, Ss = (ajustar(V, vec["W"], "v"), ajustar(V, vec["E"], "v"), ajustar(H, vec["N"], "h"), ajustar(H, vec["S"], "h"))

    def inter(vv, hh):
        av, bv, ah, bh = vv[0], vv[1], hh[0], hh[1]
        x = (av * bh + bv) / (1 - av * ah)
        return (float(x), float(ah * x + bh))
    return [inter(Ws, Ns), inter(Es, Ns), inter(Es, Ss), inter(Ws, Ss)], dict(W=Ws, E=Es, N=Ns, S=Ss)


def imagen_lamina(pdf, pagina):
    doc = pymupdf.open(str(pdf))
    p = doc[pagina - 1]
    xref = p.get_images(full=True)[0][0]
    pix = pymupdf.Pixmap(doc, xref)
    if pix.n - pix.alpha >= 4:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].copy()
    k = {90: -1, 270: 1, 180: 2}.get(p.rotation)
    return np.ascontiguousarray(np.rot90(img, k=k)) if k else img


def pdf_de(m, rm_dir, trabajo):
    z = next(rm_dir.glob(f"{m}_*.zip"))
    with zipfile.ZipFile(z) as zf:
        n = next(x for x in zf.namelist() if re.search(r"CGCH_RME_\d+Texto", x, re.I) and x.lower().endswith(".pdf")
                 and "/" not in x.replace("\\", "/"))
        destino = trabajo / f"{m}.pdf"
        if not destino.exists():
            destino.write_bytes(zf.read(n))
    return destino, z


def warp_marco(img, esq, lim):
    """Homografía de las 4 esquinas (pixeles) al rectángulo geográfico -> RGBA en plate-carrée (PSAD56 grados)."""
    dlon, dlat = lim["e"] - lim["w"], lim["n"] - lim["s"]
    ow = CAP
    oh = int(round(ow * dlat / dlon))
    src = np.array(esq, np.float32)
    dst = np.array([[0, 0], [ow - 1, 0], [ow - 1, oh - 1], [0, oh - 1]], np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    rgb = cv2.warpPerspective(img, M, (ow, oh), flags=cv2.INTER_AREA if img.shape[1] > 2 * ow else cv2.INTER_LINEAR,
                              borderValue=(255, 255, 255))
    return np.dstack([rgb, np.full((oh, ow), 255, np.uint8)]), M


def bounds_wgs84(lim, datum="PSAD56"):
    f = A_WGS.transform if datum == "PSAD56" else (lambda lo, la: (lo, la))
    pts = [f(lo, la) for lo, la in ((lim["w"], lim["n"]), (lim["e"], lim["n"]),
                                                  (lim["e"], lim["s"]), (lim["w"], lim["s"]))]
    return dict(n=round(max(p[1] for p in pts), 6), s=round(min(p[1] for p in pts), 6),
                e=round(max(p[0] for p in pts), 6), w=round(min(p[0] for p in pts), 6))


def leyenda_sin_mapa(img, esq, ancho=3000):
    """Lámina con el mapa en blanco y recortada al contenido restante (leyenda, listado, créditos)."""
    v = img.copy()
    cv2.fillPoly(v, [np.array(esq, np.int32)], (255, 255, 255))
    x0 = int(min(p[0] for p in esq)) - 160
    y0 = int(min(p[1] for p in esq)) - 160
    x1 = int(max(p[0] for p in esq)) + 160
    y1 = int(max(p[1] for p in esq)) + 160
    v[max(0, y0):y1, max(0, x0):x1] = 255          # rótulos de grados y bordes del marco
    nb = v.min(axis=2) < 225
    ys, xs = np.where(nb)
    v = v[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    f = min(1.0, ancho / v.shape[1])
    return cv2.resize(v, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else v


UTM_PS = CRS.from_proj4("+proj=utm +zone=19 +south +ellps=intl +units=m +no_defs")
GEO_PS = CRS.from_proj4("+proj=longlat +ellps=intl +no_defs")


def puntos_coquimbo(m, base):
    """Yacimientos de las hojas PSAD56 de Coquimbo (xls, UTM PSAD56): geográficas PSAD56 sin cambio de datum."""
    yac = {"M168": "Yacimientos_Montepatria.xls", "M169": "Yacimientos_Vicuña.xls",
           "M195": "Yacimientos_LaSerena_LaHiguera.xls", "M305": "Yacimientos_Condoriaco_Rivadavia.xls"}[m]
    t = Transformer.from_crs(UTM_PS, GEO_PS, always_xy=True)
    out = []
    for r in R.filas_xls(R.hallar(base, re.escape(yac))):
        x, y = R.num(r.get("Utm_Este")), R.num(r.get("Utm_Norte"))
        if x is not None and y is not None and 1e5 < x < 9e5:
            out.append(t.transform(x, y))
    return out


def puntos_hoja(m, base, datum_tabla="WGS84"):
    """(lon_psad56, lat_psad56) de los yacimientos de la tabla, para verificar sobre la lámina (que imprime PSAD56).
    datum_tabla: datum REAL de los números UTM de la tabla (WGS84 = convertida; PSAD56 = tal cual de la lámina)."""
    if m in ("M168", "M169", "M195", "M305"):
        return puntos_coquimbo(m, base)
    capa = "RMM_YACIM_N.shp" if m == "M105" else "RMM_YACIMI.shp"
    pos = R.geometrias_shp(base / "Geometria" / capa)
    if m == "M105":                                   # tabla en WGS84 ~ SIRGAS de la hoja: sin cambio de datum
        t84 = Transformer.from_crs(32719, 4326, always_xy=True)
        return [t84.transform(x, y) for x, y in pos.values()]
    dxy = R.CORRECCION_XY.get(m, {}).get("yacimientos", (0.0, 0.0))     # la misma corrección que usa 📍 Datos
    pos = {k: (x + dxy[0], y + dxy[1]) for k, (x, y) in pos.items()}
    t = (Transformer.from_crs(32719, PS_GEO, always_xy=True) if datum_tabla == "WGS84"
         else Transformer.from_crs(UTM_PS, GEO_PS, always_xy=True))
    return [t.transform(x, y) for x, y in pos.values()]


def verificar(m, ov, lim, base, out, datum_tabla="WGS84"):
    """Dibuja los yacimientos de la tabla sobre el overlay generado (círculos); guarda un mosaico de 4 recortes."""
    h, w = ov.shape[:2]
    vis = ov[:, :, :3].copy()
    pts = []
    for lo, la in puntos_hoja(m, base, datum_tabla):
        x = (lo - lim["w"]) / (lim["e"] - lim["w"]) * (w - 1)
        y = (lim["n"] - la) / (lim["n"] - lim["s"]) * (h - 1)
        if 0 <= x < w and 0 <= y < h:
            pts.append((int(x), int(y)))
            cv2.circle(vis, (int(x), int(y)), 14, (255, 0, 255), 2)
    r = 220
    sel = [min(pts, key=lambda p: p[0] + p[1]), min(pts, key=lambda p: -p[0] + p[1]),
           min(pts, key=lambda p: -p[0] - p[1]), min(pts, key=lambda p: p[0] - p[1])]
    tiles = []
    for x, y in sel:
        t = np.full((2 * r, 2 * r, 3), 255, np.uint8)
        a, b = max(0, x - r), max(0, y - r)
        s = vis[b:y + r, a:x + r]
        t[b - (y - r):b - (y - r) + s.shape[0], a - (x - r):a - (x - r) + s.shape[1]] = s
        tiles.append(t)
    cv2.imwrite(str(out), np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])[:, :, ::-1])
    return len(pts)


ZOOM = 2.6


def lamina_vectorial(pdf, cfg):
    """Renderiza el recorte del marco (y la lámina entera a escala menor) de una página vectorial; devuelve
    (img_recorte, esquinas_en_recorte, img_lamina_completa, esquinas_en_lamina)."""
    p = pymupdf.open(str(pdf))[cfg["pagina"] - 1]
    esq, ajustes = esquinas_vectoriales(p, cfg["vec"])
    xs, ys = [c[0] for c in esq], [c[1] for c in esq]
    pad = 12
    clip = pymupdf.Rect(min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    pix = p.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip, alpha=False)
    rec = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].copy()
    esq_rec = [((x - clip.x0) * ZOOM, (y - clip.y0) * ZOOM) for x, y in esq]
    zl = 1.0
    pix2 = p.get_pixmap(matrix=pymupdf.Matrix(zl, zl), alpha=False)
    lam = np.frombuffer(pix2.samples, np.uint8).reshape(pix2.h, pix2.w, pix2.n)[:, :, :3].copy()
    esq_lam = [(x * zl, y * zl) for x, y in esq]
    return rec, esq_rec, lam, esq_lam, ajustes


def procesar(m, args):
    cfg = HOJAS[m]
    pdf, zip_ = pdf_de(m, args.rm_dir, args.trabajo)
    if "vec" in cfg:
        img, esq, lam, esq_lam, ajustes = lamina_vectorial(pdf, cfg)
        cfg = dict(cfg, esq=esq)
        print(m, "esquinas (pt):", [tuple(round(v, 1) for v in c) for c in esq_lam],
              "ajustes:", {k: (round(v[0], 5), round(v[1], 2), v[2]) for k, v in ajustes.items()})
    else:
        img = imagen_lamina(pdf, cfg["pagina"])
        lam, esq_lam = img, cfg["esq"]
    ov, _ = warp_marco(img, cfg["esq"], cfg["lim"])
    (RAIZ / "overlays").mkdir(exist_ok=True)
    (RAIZ / "leyendas").mkdir(exist_ok=True)
    sid = f"rm_{m}"
    cv2.imwrite(str(RAIZ / "overlays" / f"{sid}.webp"), ov[:, :, [2, 1, 0, 3]], [cv2.IMWRITE_WEBP_QUALITY, 88])
    ley = leyenda_sin_mapa(lam, esq_lam)
    cv2.imwrite(str(RAIZ / "leyendas" / f"{sid}.jpg"), ley[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 82])
    b = bounds_wgs84(cfg["lim"], cfg.get("datum", "PSAD56"))
    print(m, "overlay", ov.shape[1], "x", ov.shape[0], "bounds", b)
    if args.verificar:
        base = args.trabajo / "datos" / m
        if not base.exists():
            R.extraer(args.rm_dir, args.trabajo / "datos")
        n = verificar(m, ov, cfg["lim"], base, args.trabajo / f"{m}_verif.png", args.datum_tabla)
        print("  verificación:", n, "yacimientos ->", args.trabajo / f"{m}_verif.png")
    return dict(id=sid, bounds=b, region=cfg["region"], titulo=cfg["titulo"], hoja=m)


INFORME = {"M81": "RME-03", "M82": "RME-04", "M84": "RME-02", "M85": "RME-05", "M86": "RME-01", "M105": "RME-34",
           "M168": "RME-28", "M169": "RME-29", "M195": "RME-32", "M305": "RME-33"}


def actualizar_capas(resultados, args):
    """Agrega/reemplaza las entradas rm_<M> en capas.json (categoría aplicada, tema Geología Económica)."""
    ruta = RAIZ / "capas.json"
    raw = ruta.read_text(encoding="utf-8")
    capas = json.loads(raw)
    cat = R.G.cargar_catalogo(R.G.CATALOGO)
    for r in resultados:
        c = cat.get(r["hoja"], {})
        e = {"id": r["id"], "categoria": "aplicada",
             "titulo": r["titulo"], "fuente": "SERNAGEOMIN — Mapa de Recursos Minerales de Chile, N°%s" % INFORME[r["hoja"]].split("-")[1].lstrip("0"),
             "anio": c.get("ano") or "", "escala": c.get("escala") or "1:100.000", "autor": c.get("autor") or "",
             "informe": INFORME[r["hoja"]], "bounds": r["bounds"], "overlay": f"overlays/{r['id']}.webp",
             "leyenda": f"leyendas/{r['id']}.jpg", "opacidad": 1.0, "recortado": True, "pdf": None,
             "region": r["region"], "tema": "Mapas de Geología Económica"}
        i = next((k for k, x in enumerate(capas) if x["id"] == r["id"]), None)
        if i is None:
            capas.append(e)
        else:
            capas[i] = e
    out = json.dumps(capas, ensure_ascii=False, indent=2)
    if CRLF in raw:
        out = out.replace("\n", CRLF)
    ruta.write_text(out, encoding="utf-8", newline="")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hojas", nargs="+")
    ap.add_argument("--rm-dir", type=pathlib.Path, default=RM_DIR)
    ap.add_argument("--trabajo", type=pathlib.Path, default=pathlib.Path(tempfile.gettempdir()) / "geochile_rm_georef")
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--capas", action="store_true", help="agrega/actualiza las entradas en capas.json")
    ap.add_argument("--datum-tabla", default="WGS84", choices=["WGS84", "PSAD56"],
                    help="datum que se supone a los UTM de la tabla al dibujar los puntos de verificación")
    args = ap.parse_args()
    args.trabajo.mkdir(parents=True, exist_ok=True)
    res = [procesar(m, args) for m in args.hojas]
    if args.capas:
        actualizar_capas(res, args)
        print("capas.json actualizado:", [r["id"] for r in res])
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
