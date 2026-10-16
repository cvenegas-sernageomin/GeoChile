"""KMZ con las cartas geológicas EN RASTER (GroundOverlay) además de la grilla de hojas IGM 1:100.000.

Uso (desde la raíz del repo):
    python -I -X utf8 tools/generar_kmz_raster.py [--out DIR] [--publicar]

Genera:
  <out>/Cartas_<Región>.kmz      un KMZ por región con las cartas de geología básica como GroundOverlay (imágenes embebidas;
                                 JPEG si la carta es opaca, PNG de paleta con transparencia si tiene zonas enmascaradas)
  kmz/cartas_geologicas_raster.kmz   KMZ principal pequeño: grilla de hojas + un NetworkLink por región hacia su KMZ regional
Los KMZ regionales pesan 5–35 MB (150 MB en total): NO caben en el repo de Pages, van como assets de la Release «kmz» del repo
GeoChile (--publicar los sube; usa la credencial de git ya guardada). El KMZ principal los enlaza por URL, así Google Earth los
baja cuando se marcan; cada regional también se puede descargar y abrir sin conexión.
"""
import argparse
import io
import json
import pathlib
import re
import subprocess
import sys
import unicodedata
import urllib.request
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from PIL import Image  # noqa: E402

import generar_kmz_cobertura as K  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
RAIZ = pathlib.Path(__file__).resolve().parent.parent
REPO = "cvenegas-sernageomin/GeoChile"
TAG = "kmz"
URL_ASSET = f"https://github.com/{REPO}/releases/download/{TAG}/"
LADO_MAX = 2200
ORDEN_REGIONES = ["Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo", "Valparaíso", "Metropolitana", "O'Higgins",
                  "Maule", "Ñuble", "Biobío", "Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes"]


def ascii_(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def imagen(c):
    """-> (bytes, extensión). JPEG si es opaca; PNG de paleta con alfa si tiene transparencia."""
    im = Image.open(RAIZ / c["overlay"])
    w, h = im.size
    s = min(1, LADO_MAX / max(w, h))
    if s < 1:
        im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
    b = io.BytesIO()
    if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 250:
        im.quantize(colors=160, method=Image.FASTOCTREE).save(b, "PNG", optimize=True)
        return b.getvalue(), "png"
    im.convert("RGB").save(b, "JPEG", quality=72, optimize=True)
    return b.getvalue(), "jpg"


def region_de(c):
    r = c.get("region")
    return (r[0] if isinstance(r, list) else r) or "Otras"


def kml_regional(region, cartas, nombres):
    ov = []
    for i, c in enumerate(cartas):
        b = c["bounds"]
        info = escape(c.get("informe") or c["id"])
        d = (f'<b>{escape(c["titulo"])}</b><br>{escape(c.get("fuente") or "")}'
             + (f"<br>Año: {escape(str(c['anio']))}" if c.get("anio") else "")
             + (f"<br>Escala: {escape(c['escala'])}" if c.get("escala") else "")
             + (f"<br>Autores: {escape(c['autor'])}" if c.get("autor") else "")
             + f'<br>Informe: {info}<br><a href="{K.VISOR}">Ver en el Visor GeoChile</a>')
        ov.append(f'<GroundOverlay><name>{escape(c["titulo"])} ({info})</name><description><![CDATA[{d}]]></description>'
                  f'<drawOrder>{10 + i}</drawOrder><Icon><href>{nombres[c["id"]]}</href></Icon>'
                  f'<LatLonBox><north>{b["n"]}</north><south>{b["s"]}</south><east>{b["e"]}</east><west>{b["w"]}</west></LatLonBox></GroundOverlay>')
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f'<name>Cartas geológicas — {escape(region)}</name><description>Cartas geológicas en raster de SERNAGEOMIN, '
            f'región {escape(region)} ({len(cartas)} cartas). Visor: {K.VISOR}</description><Folder><name>{escape(region)}</name>'
            + "".join(ov) + "</Folder></Document></kml>")


def construir(out):
    capas = [c for c in json.loads((RAIZ / "capas.json").read_text(encoding="utf-8"))
             if c["categoria"] == "geologia" and c.get("bounds")]
    grupos = {}
    for c in capas:
        grupos.setdefault(region_de(c), []).append(c)
    out.mkdir(parents=True, exist_ok=True)
    regionales = []
    for region in sorted(grupos, key=lambda r: ORDEN_REGIONES.index(r) if r in ORDEN_REGIONES else 99):
        cartas = sorted(grupos[region], key=lambda c: (-c["bounds"]["n"], c["bounds"]["w"]))
        nombres, archivos = {}, {}
        for c in cartas:
            data, ext = imagen(c)
            nombres[c["id"]] = f"imagenes/{c['id']}.{ext}"
            archivos[nombres[c["id"]]] = data
        ruta = out / f"Cartas_{ascii_(region)}.kmz"
        with zipfile.ZipFile(ruta, "w", zipfile.ZIP_STORED) as z:       # JPEG/PNG ya van comprimidos
            z.writestr("doc.kml", kml_regional(region, cartas, nombres))
            for n, d in archivos.items():
                z.writestr(n, d)
        mb = ruta.stat().st_size / 1e6
        regionales.append((region, ruta, len(cartas), mb))
        print(f"{ruta.name}: {len(cartas)} cartas, {mb:.1f} MB")
    return regionales


def kmz_principal(regionales):
    """Grilla de hojas (con carta en verde) + un NetworkLink por región."""
    hojas = K.preparar()
    base, n_ok = K.kml_cuerpo("Grilla de hojas IGM 1:100.000", hojas, lambda h: bool(h["_cartas"]), ("3c9e2e", "2e7d32"))
    links = "".join(
        f'<NetworkLink><name>{escape(r)} — {n} cartas ({mb:.0f} MB)</name><visibility>0</visibility>'
        f'<description>Marca esta casilla para cargar las cartas en raster de {escape(r)} (necesita conexión; también puedes '
        f'descargar el archivo Cartas_{ascii_(r)}.kmz desde el portal y abrirlo sin conexión).</description>'
        f'<Link><href>{URL_ASSET}{ruta.name}</href><refreshMode>onInterval</refreshMode><refreshInterval>86400</refreshInterval></Link></NetworkLink>'
        for r, ruta, n, mb in regionales)
    kml = ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
           '<name>Cartas geológicas disponibles (distribución raster)</name>'
           f'<description>Grilla de las 455 hojas IGM 1:100.000 ({n_ok} con carta en verde) y, por región, las cartas geológicas '
           f'en raster. Marca una región para cargarlas. Visor: {K.VISOR}</description>'
           f'<Folder><name>Cartas en raster por región</name><open>1</open>{links}</Folder>{base}</Document></kml>')
    ruta = RAIZ / "kmz" / "cartas_geologicas_raster.kmz"
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
    print(ruta.name, f"{ruta.stat().st_size / 1024:.0f} KB")


# ── publicación en la Release «kmz» ──────────────────────────────────────────────────────────────────────────────
def token():
    r = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", capture_output=True, text=True)
    return next((l.split("=", 1)[1] for l in r.stdout.splitlines() if l.startswith("password=")), None)


def api(tok, metodo, url, datos=None, ctype="application/json"):
    req = urllib.request.Request(url, method=metodo, data=datos,
                                 headers={"Authorization": f"token {tok}", "Accept": "application/vnd.github+json", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req) as r:
            t = r.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        if e.code == 404 and metodo == "GET":
            return None
        raise


def publicar(regionales):
    tok = token()
    if not tok:
        raise SystemExit("sin credencial de GitHub")
    rel = api(tok, "GET", f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}")
    if rel is None:
        rel = api(tok, "POST", f"https://api.github.com/repos/{REPO}/releases", json.dumps({
            "tag_name": TAG, "name": "KMZ de cartas en raster",
            "body": "KMZ regionales con las cartas geológicas en raster (Google Earth). Los enlaza kmz/cartas_geologicas_raster.kmz."}).encode())
    existentes = {a["name"]: a["id"] for a in rel.get("assets", [])}
    for region, ruta, n, mb in regionales:
        if ruta.name in existentes:
            api(tok, "DELETE", f"https://api.github.com/repos/{REPO}/releases/assets/{existentes[ruta.name]}")
        print("subiendo", ruta.name, f"{mb:.1f} MB …")
        api(tok, "POST", f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets?name={ruta.name}",
            ruta.read_bytes(), "application/vnd.google-earth.kmz")
    print("publicado:", f"https://github.com/{REPO}/releases/tag/{TAG}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("_kmz_regionales"))
    ap.add_argument("--publicar", action="store_true")
    a = ap.parse_args()
    reg = construir(a.out)
    kmz_principal(reg)
    if a.publicar:
        publicar(reg)


if __name__ == "__main__":
    main()
