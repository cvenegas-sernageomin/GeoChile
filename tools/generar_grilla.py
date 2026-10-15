"""Genera grilla_igm100k.json (hojas IGM 1:100.000 de todo Chile) desde INDICE_HOJAS_100.kmz.

Uso: python -I -X utf8 tools/generar_grilla.py [INDICE_HOJAS_100.kmz] [catalogo.json]
Cada hoja: c=codigo IGM, nom=nombre, b=[w,s,e,n], p=poligono simplificado, g=[[codigo,titulo,url],...]
Los enlaces GDB salen del Catalogo Digital de Publicaciones Geologicas (nombre de la hoja contenido en el
titulo, serie Geologia Basica). Se conservan aunque el enlace del portal este caido.
"""
import json, pathlib, re, sys, unicodedata, urllib.parse, zipfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PROY = RAIZ.parent
KMZ = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else PROY / "RAG-Cartas-SGB" / "INDICE_HOJAS_100.kmz"
CAT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else PROY / "publicaciones-sernageomin" / "catalogo.json"
STOP = set("de del la las los el y e a en geologia area areas carta cartas hoja hojas region regiones escala mapa".split())


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def toks(s):
    s = re.sub(r"\b(region|regiones)\b.*", "", norm(s))
    return {t for t in s.split() if t not in STOP and not t.isdigit() and len(t) > 2}


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    d2 = dx * dx + dy * dy or 1e-12
    mx, mi = -1, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / d2))
        d = ((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** .5
        if d > mx:
            mx, mi = d, i
    if mx <= eps:
        return [pts[0], pts[-1]]
    return rdp(pts[:mi + 1], eps)[:-1] + rdp(pts[mi:], eps)


def main():
    kml = zipfile.ZipFile(KMZ).read("doc.kml").decode("utf-8")
    cat = json.loads(CAT.read_text(encoding="utf-8"))
    gb = [x for x in cat if x["serie"].startswith("Geología Básica")]
    celdas = []
    for p in re.findall(r"<Placemark.*?</Placemark>", kml, re.S):
        f = dict(re.findall(r"<td>([A-Z_0-9a-z]+)</td>\s*<td>(.*?)</td>", p, re.S))
        pts = [tuple(map(float, c.split(",")[:2])) for c in re.search(r"<coordinates>(.*?)</coordinates>", p, re.S).group(1).split()]
        xs, ys = [a for a, _ in pts], [b for _, b in pts]
        nom = f.get("NOMBRE", "").strip()
        t = toks(nom)
        g = []
        if t:
            for x in gb:
                if t <= toks(x["titulo"]):
                    u = urllib.parse.quote(urllib.parse.unquote(x["url"]), safe=":/%")
                    g.append([x["codigo"], re.sub(r"^\d{4}\.\s*", "", x["titulo"])[:90], u])
        celdas.append({"c": f["CODIGO_IGM"].strip(), "nom": re.sub(r"(?<=\s)(De|Del|La|Las|Los|El|Y)(?=\s)", lambda m: m.group(1).lower(), nom.title()) if nom else "",
                       "b": [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)],
                       "p": [[round(a, 4), round(b, 4)] for a, b in rdp(pts, 0.004)], "g": g})
    celdas.sort(key=lambda c: (re.sub(r"\d+", "", c["c"]), int(re.sub(r"\D", "", c["c"]) or 0)))
    (RAIZ / "grilla_igm100k.json").write_text(json.dumps(celdas, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(celdas), "hojas;", sum(1 for c in celdas if c["g"]), "con enlace GDB;", (RAIZ / "grilla_igm100k.json").stat().st_size, "bytes")


main()
