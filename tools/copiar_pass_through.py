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
