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
    ap.add_argument("--rect", default=None,
                    help="neat-line manual x0,y0,x1,y1 (si la deteccion falla)")
    a = ap.parse_args()

    kmz = SRC / a.categoria / f"{a.id}.kmz"
    img, W, H, box = load_kmz(kmz)
    if a.rect:
        rect = tuple(int(v) for v in a.rect.split(","))
    else:
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
            legimg = Image.fromarray(leg)
            legimg.thumbnail((2400, 2400))  # cap para peso web (se lee con zoom)
            legimg.save(ROOT / leyenda, "JPEG", quality=85)
            print(f"leyenda ({side}) -> {leyenda}  {legimg.size[0]}x{legimg.size[1]}")
        else:
            print(f"AVISO: leyenda lado '{side}' vacia; revisar --side manual")

    entry = dict(id=a.id, categoria=a.categoria, titulo=a.id, fuente="", anio="",
                 escala="", autor="", informe="", bounds=bounds, overlay=ov,
                 leyenda=leyenda, opacidad=1.0, recortado=True)
    print("ENTRY " + json.dumps(entry, ensure_ascii=False))

if __name__ == "__main__":
    main()
