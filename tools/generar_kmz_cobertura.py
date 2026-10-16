"""KMZ de la grilla de hojas IGM 1:100.000 con lo que HAY: cartas en raster y geodatabases (GDB).

Uso (desde la raíz del repo):  python -I -X utf8 tools/generar_kmz_cobertura.py
Escribe kmz/cartas_geologicas_raster.kmz y kmz/hojas_con_gdb.kmz.
  con carta = algún mapa de GEOLOGÍA BÁSICA de capas.json cubre la hoja (misma regla que el popup del visor: el mapa cubre al
              menos la mitad de la hoja, o cae casi entero dentro de ella, y no es más de 4 veces mayor que la hoja);
  con GDB   = la hoja tiene enlace a una geodatabase (grilla_igm100k.json `g` + `gdb` de los mapas que la cubren).
Las hojas con carta/GDB van rellenas de color y con el detalle en el globo (cartas, enlaces de descarga de la GDB); las demás
quedan solo como contorno gris tenue, para ubicarse.
"""
import json, pathlib, re, zipfile
from xml.sax.saxutils import escape

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "kmz"
VISOR = "https://cvenegas-sernageomin.github.io/GeoChile/"


def cubre(c, b):
    w, s, e, n = b
    A = (e - w) * (n - s)
    B = c["bounds"]
    iw, ih = min(e, B["e"]) - max(w, B["w"]), min(n, B["n"]) - max(s, B["s"])
    if iw <= 0 or ih <= 0:
        return False
    Ac = (B["e"] - B["w"]) * (B["n"] - B["s"])
    return Ac <= 4 * A and (iw * ih / A >= .5 or iw * ih / Ac >= .6)


def seguro(url):
    return url if re.match(r"^https://(www\.sernageomin\.cl|cvenegas-sernageomin\.github\.io)/", url or "") else None


def kml(nombre, descr, hojas, tiene, color_ok, leyenda_ok):
    estilos = (
        f'<Style id="ok"><LineStyle><color>ff{color_ok[1]}</color><width>2</width></LineStyle>'
        f'<PolyStyle><color>99{color_ok[0]}</color></PolyStyle></Style>'
        '<Style id="no"><LineStyle><color>66999999</color><width>0.8</width></LineStyle>'
        '<PolyStyle><fill>0</fill></PolyStyle></Style>')
    cuerpo = []
    for h in hojas:
        ok = tiene(h)
        pol = " ".join(f"{x},{y},0" for x, y in h["p"])
        cuerpo.append(
            f'<Placemark><name>{escape(h["c"] + (" " + h["nom"] if h.get("nom") else ""))}</name>'
            f'<description><![CDATA[{h["_d"]}]]></description><styleUrl>#{"ok" if ok else "no"}</styleUrl>'
            f'<Polygon><outerBoundaryIs><LinearRing><coordinates>{pol}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>')
    n_ok = sum(1 for h in hojas if tiene(h))
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f'<name>{escape(nombre)}</name><description>{escape(descr)} {leyenda_ok}: {n_ok} de {len(hojas)} hojas. '
            f'Las hojas sin color solo muestran la grilla IGM 1:100.000.</description>{estilos}<Folder><name>{escape(nombre)}</name>'
            + "".join(cuerpo) + '</Folder></Document></kml>'), n_ok


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
        cartas = "".join(f'• {escape(c["titulo"])} ({escape(c.get("informe") or c["id"])})<br>' for c in h["_cartas"])
        gd = ""
        for g in h["_gdb"]:
            u = seguro(g[2])
            gd += f'• {escape(g[0])} {escape(g[1])}' + (f' — <a href="{escape(u)}">⬇ descargar GDB</a>' if u else "") + "<br>"
        pie = f'<br><a href="{VISOR}">Ver en el Visor GeoChile</a>'
        h["_d"] = cab + ("<b>Cartas en el visor:</b><br>" + cartas if cartas else "") + ("<b>Geodatabase (GDB):</b><br>" + gd if gd else "") \
            + ("" if (cartas or gd) else "Todavía sin carta ni GDB.<br>") + pie
    SALIDA.mkdir(exist_ok=True)
    for viejo in ("hojas_sin_carta.kmz", "hojas_sin_gdb.kmz"):      # nombres anteriores (marcaban lo que falta)
        (SALIDA / viejo).unlink(missing_ok=True)
    for archivo, nombre, descr, tiene, color, leg in (
        ("cartas_geologicas_raster.kmz", "Cartas geológicas disponibles (distribución raster)",
         "Grilla de las 455 hojas IGM 1:100.000: en verde, las hojas cubiertas por alguna carta geológica en raster del visor GeoChile.",
         lambda h: bool(h["_cartas"]), ("3c9e2e", "2e7d32"), "Hojas con carta"),
        ("hojas_con_gdb.kmz", "Ubicación de las geodatabases (GDB)",
         "Grilla de las 455 hojas IGM 1:100.000: en azul, las hojas con geodatabase (GDB) en el Catálogo de Publicaciones de SERNAGEOMIN, con enlace de descarga.",
         lambda h: bool(h["_gdb"]), ("c9742a", "a85a1a"), "Hojas con GDB")):
        txt, n = kml(nombre, descr, hojas, tiene, color, leg)
        with zipfile.ZipFile(SALIDA / archivo, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("doc.kml", txt)
        print(archivo, f"{n} de {len(hojas)} hojas")


if __name__ == "__main__":
    main()
