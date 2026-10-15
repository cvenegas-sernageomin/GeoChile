"""Grillas KMZ de cobertura (hojas IGM 1:100.000): sin carta y sin GDB, en rojo.

Uso (desde la raíz del repo):  python -I -X utf8 tools/generar_kmz_cobertura.py
Escribe kmz/hojas_sin_carta.kmz y kmz/hojas_sin_gdb.kmz.
  sin carta = ningún mapa de GEOLOGÍA BÁSICA de capas.json cubre la hoja (misma regla que el popup del visor: el mapa cubre
              al menos la mitad de la hoja, o cae casi entero dentro de ella, y no es más de 4 veces mayor que la hoja);
  sin GDB   = la hoja no tiene enlace a geodatabase (grilla_igm100k.json `g` + `gdb` de los mapas que la cubren).
Rojo = falta; verde = tiene. Cada hoja lleva nombre, código IGM y mapas/GDB asociados.
"""
import json, pathlib, zipfile
from xml.sax.saxutils import escape

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "kmz"


def cubre(c, b):
    w, s, e, n = b
    A = (e - w) * (n - s)
    B = c["bounds"]
    iw, ih = min(e, B["e"]) - max(w, B["w"]), min(n, B["n"]) - max(s, B["s"])
    if iw <= 0 or ih <= 0:
        return False
    Ac = (B["e"] - B["w"]) * (B["n"] - B["s"])
    return Ac <= 4 * A and (iw * ih / A >= .5 or iw * ih / Ac >= .6)


def kml(nombre, descr, hojas, falta, leyenda_falta, leyenda_ok):
    estilos = (
        '<Style id="falta"><LineStyle><color>ff0000ff</color><width>1.5</width></LineStyle>'
        '<PolyStyle><color>800000ff</color></PolyStyle></Style>'
        '<Style id="ok"><LineStyle><color>ff2e7d32</color><width>1</width></LineStyle>'
        '<PolyStyle><color>2000c800</color></PolyStyle></Style>')
    cuerpo = []
    for h in hojas:
        f = falta(h)
        pol = " ".join(f"{x},{y},0" for x, y in h["p"])
        d = h.get("_d", "")
        cuerpo.append(
            f'<Placemark><name>{escape(h["c"] + (" " + h["nom"] if h.get("nom") else ""))}</name>'
            f'<description><![CDATA[{d}]]></description><styleUrl>#{"falta" if f else "ok"}</styleUrl>'
            f'<Polygon><outerBoundaryIs><LinearRing><coordinates>{pol}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>')
    nf = sum(1 for h in hojas if falta(h))
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f'<name>{escape(nombre)}</name><description>{escape(descr)} Rojo: {leyenda_falta} ({nf} de {len(hojas)}). '
            f'Verde: {leyenda_ok} ({len(hojas) - nf}).</description>{estilos}<Folder><name>{escape(nombre)}</name>'
            + "".join(cuerpo) + '</Folder></Document></kml>'), nf


def main():
    hojas = json.loads((RAIZ / "grilla_igm100k.json").read_text(encoding="utf-8"))
    capas = json.loads((RAIZ / "capas.json").read_text(encoding="utf-8"))
    geo = [c for c in capas if c["categoria"] == "geologia" and c.get("bounds")]
    todos = [c for c in capas if c.get("bounds") and c["categoria"] != "hillshade"]
    for h in hojas:
        h["_cartas"] = [c for c in geo if cubre(c, h["b"])]
        gdb = [(g[0], g[1], g[2]) for g in h["g"]]
        for c in todos:
            if c.get("gdb") and cubre(c, h["b"]) and not any(x[2] == c["gdb"] for x in gdb):
                gdb.append((c.get("gdb_codigo") or "", c["titulo"], c["gdb"]))
        h["_gdb"] = gdb
        cab = f'<b>Hoja {escape(h["c"])}</b> {escape(h.get("nom") or "")}<br>IGM 1:100.000<br>'
        cartas = "".join(f'• {escape(c["titulo"])} ({escape(c.get("informe") or c["id"])})<br>' for c in h["_cartas"]) or "Sin carta geológica en el visor.<br>"
        gd = "".join(f'• {escape(g[0])} {escape(g[1])}<br>' for g in h["_gdb"]) or "Sin geodatabase.<br>"
        h["_d"] = cab + "<b>Cartas:</b><br>" + cartas + "<b>GDB:</b><br>" + gd
    SALIDA.mkdir(exist_ok=True)
    for archivo, nombre, descr, falta, lf, lo in (
        ("hojas_sin_carta.kmz", "Hojas IGM 1:100.000 sin carta geológica",
         "Grilla de las 455 hojas; marca las que ningún mapa de geología básica del visor GeoChile cubre.",
         lambda h: not h["_cartas"], "sin carta", "con carta"),
        ("hojas_sin_gdb.kmz", "Hojas IGM 1:100.000 sin geodatabase",
         "Grilla de las 455 hojas; marca las que no tienen GDB (geodatabase) asociada en el Catálogo de Publicaciones.",
         lambda h: not h["_gdb"], "sin GDB", "con GDB")):
        txt, nf = kml(nombre, descr, hojas, falta, lf, lo)
        with zipfile.ZipFile(SALIDA / archivo, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("doc.kml", txt)
        print(archivo, f"{nf} rojas de {len(hojas)}")


if __name__ == "__main__":
    main()
