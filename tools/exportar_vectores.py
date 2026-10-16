"""Unidades geológicas (polígonos) y fallas de las GDB -> JSON por carta para el visor GeoChile (repo geochile-vectores).

Uso (desde la raíz del repo):
    python -I -X utf8 tools/exportar_vectores.py [--gdb-dir DIR] [--catalogo CSV] [--out ..\\geochile-vectores] [--solo GB-100 ...]

Escribe, en --out:
    cartas/<id>.json   una carta: tabla de unidades (código, nombre, definición, ambiente, litología inferida, edad) +
                       polígonos [índice de unidad, tipo, coordenadas] + fallas [índice de tipo, nombre, obs., tipo, coordenadas]
    index.json         cartas (bounds, conteos, tamaño) y listas de valores de cada filtro con su número de polígonos
    ingesta.json       informe: cartas leídas, fallidas, % de unidades sin edad / sin litología, correcciones de datum

Reglas verificadas (memoria reference-georef-con-gdb-registro-contactos):
  * GB-83, GB-106, GB-115: la GDB viene sin el cambio PSAD56→WGS84 (~440 m): se suma;
  * GB-94: el cambio está aplicado DOS veces: se resta una vez (traslación constante: PROJ no cubre al sur de 43,4°S);
  * los dominios Esri se resuelven POR GDB.
Los polígonos se simplifican como COBERTURA (shapely.coverage_simplify): los bordes compartidos se simplifican igual y no
quedan huecos entre unidades vecinas.
"""
import argparse
import datetime
import json
import math
import pathlib
import re
import sys
import warnings
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import datos_lib as L  # noqa: E402
import exportar_gdb_a_datos as G  # noqa: E402
import litologia as LIT  # noqa: E402

warnings.filterwarnings("ignore")
import pyogrio  # noqa: E402
import shapely  # noqa: E402
from pyproj import Transformer  # noqa: E402

TOL = 0.0004            # grados (~40 m)
DEC = 5                 # decimales de las coordenadas (~1 m)
SIN_EDAD = "Sin edad"
# datum: carta -> "sumar" (GDB sin cambio de datum) | "restar" (cambio duplicado)
DATUM = {"GB-83": "sumar", "GB-106": "sumar", "GB-115": "sumar", "GB-94": "restar"}
_P2W = Transformer.from_crs(4248, 4326, always_xy=True)

# nombres de campo según la plantilla de la GDB (los shapefiles antiguos los truncan)
CAMPOS = {
    "codigo": ["CODIGO", "UNIDAD_GENERICA", "CODIGO_UNI"], "nombre": ["NOMBRE"], "definicion": ["DEFINICION"], "nota": ["NOTA"],
    "ambiente": ["SUBTIPO_DESC", "SUBTIPO_DE"],
    "ep_max": ["EPOCA_ESTRAT_MAX", "EPOCA_E_MAX", "EPOCA_E_MX"], "ep_min": ["EPOCA_ESTRAT_MIN", "EPOCA_E_MIN", "EPOCA_E_MN"],
    "pe_max": ["PERIODO_MAX", "PERIODO_MA"], "pe_min": ["PERIODO_MIN", "PERIODO_MI"],
    "g_max": ["GEOCHRON_AGE_MAX", "GEOCHRO_MX"], "g_min": ["GEOCHRON_AGE_MIN", "GEOCHRO_MN"],
}
CAMPOS_FALLA = {"tipo": ["SUBTIPO_DESC", "SUBTIPO_DE"], "falla": ["FALLA"], "nombre": ["NOMBRE"], "manteo": ["DIR_MANTEO"],
                "info": ["TP_INFORMACION", "TP_INFORMA", "TP_INFORMAC"]}

# ── edades: nombre de época/periodo -> intervalo (Ma, más viejo, más joven) ───────────────────────────────────────────
PERIODOS = {"cuaternario": (2.58, 0), "neogeno": (23.03, 2.58), "paleogeno": (66.0, 23.03), "cretacico": (145.0, 66.0),
            "jurasico": (201.4, 145.0), "triasico": (251.9, 201.4), "permico": (298.9, 251.9), "carbonifero": (358.9, 298.9),
            "devonico": (419.2, 358.9), "silurico": (443.8, 419.2), "ordovicico": (485.4, 443.8), "cambrico": (538.8, 485.4),
            "precambrico": (4600.0, 538.8)}
EPOCAS = {"holoceno": (0.0117, 0), "pleistoceno": (2.58, 0.0117), "plioceno": (5.333, 2.58), "mioceno": (23.03, 5.333),
          "oligoceno": (33.9, 23.03), "eoceno": (56.0, 33.9), "paleoceno": (66.0, 56.0),
          "cretacico superior": (100.5, 66.0), "cretacico inferior": (145.0, 100.5),
          "jurasico superior": (161.5, 145.0), "jurasico medio": (174.7, 161.5), "jurasico inferior": (201.4, 174.7),
          "triasico superior": (237.0, 201.4), "triasico medio": (247.2, 237.0), "triasico inferior": (251.9, 247.2),
          "lopingiano": (259.5, 251.9), "guadalupiano": (273.0, 259.5), "cisuraliano": (298.9, 273.0),
          "pennsylvaniano": (323.2, 298.9), "pennsylvaniano superior": (307.0, 298.9), "pennsylvaniano inferior": (323.2, 307.0),
          "mississippiano": (358.9, 323.2), "mississippiano superior": (330.9, 323.2), "mississippiano medio": (346.7, 330.9),
          "mississippiano inferior": (358.9, 346.7),
          "devonico superior": (382.7, 358.9), "devonico medio": (393.3, 382.7), "devonico inferior": (419.2, 393.3),
          "carbonifero superior": (323.2, 298.9), "carbonifero inferior": (358.9, 323.2),
          "permico superior": (273.0, 251.9), "permico inferior": (298.9, 273.0)}
EPOCAS_ICS = [(e[3], e[0]) for e in L.ICS]       # (época, límite inferior Ma): ascendente


def _k(s):
    s = L._sin_tildes(str(s or "")).lower().strip()
    s = re.sub(r"\bsup\b\.?", "superior", s)
    s = re.sub(r"\binf\b\.?", "inferior", s)
    s = re.sub(r"\bmed\b\.?", "medio", s)
    return re.sub(r"\s+", " ", s)


def intervalo_texto(txt):
    """'Cretácico Sup-Paleoceno' / 'Mioceno' / 'Jurásico' -> (viejo, joven) en Ma o None."""
    k = _k(txt)
    if not k or k.startswith("t-"):
        return None
    for tabla in (EPOCAS, PERIODOS):
        if k in tabla:
            return tabla[k]
    partes = [p.strip() for p in re.split(r"\s*[-–/]\s*", k) if p.strip()]
    if len(partes) >= 2:
        ivs = []
        for i, p in enumerate(partes):
            iv = EPOCAS.get(p) or PERIODOS.get(p)
            if iv is None and i > 0 and partes[0].split(" ")[0] in PERIODOS:      # «Cretácico Sup-Inf»: hereda el periodo
                iv = EPOCAS.get(partes[0].split(" ")[0] + " " + p)
            if iv:
                ivs.append(iv)
        if ivs:
            return (max(a for a, _ in ivs), min(b for _, b in ivs))
    return None


def num_ma(v):
    if v is None:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", str(v))
    return float(m.group(0).replace(",", ".")) if m else None


def edad_unidad(ep_max, ep_min, pe_max, pe_min, g_max, g_min):
    """-> (viejo Ma, joven Ma, fuente). Edad geocronológica numérica si es coherente; si no, época; si no, periodo."""
    gmx, gmn = num_ma(g_max), num_ma(g_min)
    if gmx is not None and gmn is not None and 0 <= gmn <= gmx < 600:
        return gmx, gmn, "geocronológica"
    for a, b, fuente in ((ep_max, ep_min, "época"), (pe_max, pe_min, "periodo")):
        ia = intervalo_texto(a)
        ib = intervalo_texto(b) if b else None
        if ia or ib:
            ia, ib = ia or ib, ib or ia
            return max(ia[0], ib[0]), min(ia[1], ib[1]), fuente
    return None, None, None


def epocas_que_toca(viejo, joven):
    """Épocas ICS (las 22 del filtro de geocronología) con las que el intervalo se solapa."""
    out, ant = [], 0.0
    for nombre, lim in EPOCAS_ICS:
        if viejo > ant + 0.005 and joven < lim - 0.005:
            out.append(nombre)
        ant = lim
    if viejo > EPOCAS_ICS[-1][1] + 0.005:
        out.append("Precámbrico")
    return out


# ── datum y geometría ────────────────────────────────────────────────────────────────────────────────────────────────
def traslacion_psad56(lat, lon):
    """Traslación constante PSAD56→WGS84 (grados) en el centro de la carta; al sur de 43,4°S PROJ devuelve identidad, así que
    allí se evalúa en 42,5°S."""
    lat = max(lat, -42.5)
    x, y = _P2W.transform(lon, lat)
    return x - lon, y - lat


def corregir_datum(gb, geoms):
    modo = None
    for clave, m in DATUM.items():
        if gb and re.search(r"(?<![\d])" + re.escape(clave.split("-")[1]) + r"(?![\d])", gb) and gb.startswith("GB-") \
                and (gb == clave or gb.startswith(clave + "-")):
            modo = m
    if not modo:
        return geoms, None
    b = shapely.total_bounds(geoms[~shapely.is_empty(geoms)])
    dx, dy = traslacion_psad56((b[1] + b[3]) / 2, (b[0] + b[2]) / 2)
    if modo == "restar":
        dx, dy = -dx, -dy
    return shapely.transform(geoms, lambda c: c + [dx, dy]), f"{modo} traslación ({dx * 111320 * math.cos(math.radians((b[1] + b[3]) / 2)):.0f} m E, {dy * 110574:.0f} m N)"


def a_lista(geom):
    """Geometría shapely -> (tipo, coordenadas redondeadas) en formato GeoJSON compacto."""
    g2 = shapely.set_precision(geom, 10 ** -DEC)
    if g2 is None or g2.is_empty:                       # polígono colapsado por el redondeo
        return -1, None
    gj = shapely.geometry.mapping(g2)

    def red(c):
        if not len(c):
            return []
        if isinstance(c[0], (int, float)):
            return [round(c[0], DEC), round(c[1], DEC)]
        return [red(x) for x in c]
    t = gj["type"]
    return {"Polygon": 0, "MultiPolygon": 1, "LineString": 2, "MultiLineString": 3}.get(t, -1), red(gj["coordinates"])


def ambiente_canon(txt):
    """«AMBIENTE VOLCANICO SEDIMENTARIO» / «Unidad Volcánica y Sedimentaria» -> una sola forma."""
    a = L._sin_tildes(txt or "").lower()
    if not a.strip():
        return None
    if "volcanic" in a and "sedimentar" in a:
        return "Volcánico-sedimentario"
    for raiz, nombre in (("subvolcanic", "Subvolcánico (hipabisal)"), ("plutonic", "Plutónico / intrusivo"), ("intrusiv", "Plutónico / intrusivo"),
                         ("volcanic", "Volcánico"), ("sedimentar", "Sedimentario"), ("metamorf", "Metamórfico"),
                         ("tectonic", "Tectónico"), ("antropic", "Antrópico")):
        if raiz in a:
            return nombre
    return re.sub(r"^(ambiente|ambente|unidad)\s+", "", txt.strip(), flags=re.I).capitalize()


# ── una carta ────────────────────────────────────────────────────────────────────────────────────────────────────────
def leer_capa(gdb, patron):
    for nombre, geom in pyogrio.list_layers(str(gdb)):
        if re.match(patron, nombre, re.I):
            return nombre
    return None


def resolver_columna(df, nombres, dominios, campo_dom, respaldo):
    cols = {c.upper(): c for c in df.columns}
    c = next((cols[n] for n in nombres if n in cols), None)
    if c is None:
        return [None] * len(df)
    dom = dominios.get(campo_dom.get(c))
    out = []
    for v in df[c].tolist():
        if G.nulo(v):
            out.append(None)
        else:
            r = L.resolver(v, dom, respaldo)
            out.append(None if G.nulo(r) else re.sub(r"\s+", " ", str(r)).strip())
    return out


def procesar(gdb, args, rep):
    import geopandas as gpd  # noqa: F401
    m, gb = G.codigo_carta(gdb)
    dominios, items = G.leer_dominios(gdb)
    respaldo = L.codigos_unicos(dominios)
    capas = {n: i for n, i in ((x[0], x) for x in pyogrio.list_layers(str(gdb)))}
    lu = leer_capa(gdb, r"^GB_UNIDAD_GEO(_P)?$")
    lf = leer_capa(gdb, r"^GB_FALLAS?(_L|_A)?$")
    if not lu:
        raise RuntimeError("sin GB_UNIDAD_GEO")

    def prep(layer):
        df = pyogrio.read_dataframe(str(gdb), layer=layer)
        df = df[df.geometry.notna() & ~df.geometry.is_empty]
        df = df.set_crs(31994) if df.crs is None else df
        df = df.to_crs(4326)
        fila = items[items["Name"] == layer]
        return df, (L.campos_con_dominio(fila.iloc[0]["Definition"]) if len(fila) else {})

    du, cdu = prep(lu)
    geoms = du.geometry.values
    geoms, fix = corregir_datum(gb, geoms)
    if fix:
        rep["datum"] = fix
    geoms = shapely.make_valid(geoms)
    try:
        geoms = shapely.coverage_simplify(geoms, TOL)
    except Exception:                                   # cobertura inválida (solapes): simplificar uno a uno
        rep["sin_cobertura"] = True
        geoms = shapely.simplify(geoms, TOL, preserve_topology=True)
    R = lambda n: resolver_columna(du, CAMPOS[n], dominios, cdu, respaldo)  # noqa: E731
    col = {n: R(n) for n in CAMPOS}
    unidades, idx, feats = [], {}, []
    for i, g in enumerate(geoms):
        if g is None or g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            if g is not None and g.geom_type == "GeometryCollection":
                polis = [x for x in g.geoms if x.geom_type in ("Polygon", "MultiPolygon")]
                if not polis:
                    continue
                g = shapely.union_all(polis)
            else:
                continue
        clave = tuple(col[n][i] for n in CAMPOS)
        if clave not in idx:
            v = dict(zip(CAMPOS, clave))
            viejo, joven, fuente = edad_unidad(v["ep_max"], v["ep_min"], v["pe_max"], v["pe_min"], v["g_max"], v["g_min"])
            cat, rocas = LIT.inferir(v["nombre"], v["definicion"], v["nota"], v["ambiente"])
            amb = ambiente_canon(v["ambiente"])
            idx[clave] = len(unidades)
            unidades.append({
                "c": v["codigo"], "n": v["nombre"], "d": v["definicion"], "a": amb, "lc": cat, "lr": rocas,
                "mx": None if viejo is None else round(viejo, 3), "mn": None if joven is None else round(joven, 3), "fe": fuente,
                "ep": epocas_que_toca(viejo, joven) if viejo is not None else [],
                "pe": v["pe_max"] if v["pe_max"] == v["pe_min"] or not v["pe_min"] else f'{v["pe_max"]}–{v["pe_min"]}',
                "em": v["ep_max"] if v["ep_max"] == v["ep_min"] or not v["ep_min"] else f'{v["ep_max"]} – {v["ep_min"]}',
            })
        t, c = a_lista(g)
        if t >= 0:
            feats.append([idx[clave], t, c])
    fallas, tipos = [], []
    if lf:
        df_f, cdf = prep(lf)
        gf, _ = corregir_datum(gb, df_f.geometry.values)
        gf = shapely.simplify(shapely.make_valid(gf), TOL * .5, preserve_topology=True)
        Rf = lambda n: resolver_columna(df_f, CAMPOS_FALLA[n], dominios, cdf, respaldo)  # noqa: E731
        cf = {n: Rf(n) for n in CAMPOS_FALLA}
        for i, g in enumerate(gf):
            if g is None or g.is_empty or g.geom_type not in ("LineString", "MultiLineString"):
                continue
            tip = cf["falla"][i] or cf["tipo"][i] or "Falla"
            tip = re.sub(r"\s+", " ", tip).strip().capitalize()
            if tip not in tipos:
                tipos.append(tip)
            info = (cf["info"][i] or "").lower()
            obs = 1 if "observ" in info else (2 if "infer" in info or "supues" in info or "cubiert" in info else 0)
            t, c = a_lista(g)
            if t >= 0:
                fallas.append([tipos.index(tip), cf["nombre"][i], obs, cf["manteo"][i], t, c])
    todos = [g for g in geoms if g is not None and not g.is_empty]
    b = shapely.total_bounds(todos)
    return {"m": m, "gb": gb, "bounds": [round(float(x), 4) for x in b], "u": unidades, "p": feats, "ft": tipos, "f": fallas}


def ident(m, gb):
    return re.sub(r"[^A-Za-z0-9_-]", "", f"{gb}_{m or ''}" if gb else (m or "X")).strip("_")


def exportar(args):
    catalogo = G.cargar_catalogo(args.catalogo)
    out = args.out / "cartas"
    out.mkdir(parents=True, exist_ok=True)
    gdbs = sorted(p for p in args.gdb_dir.rglob("*.gdb") if p.is_dir())
    if args.solo:
        gdbs = [g for g in gdbs if any(s in str(g) for s in args.solo)]
    index = {"generado": datetime.datetime.now().isoformat(timespec="seconds"), "cartas": [], "filtros": {}}
    ingesta = {"cartas": {}, "fallidas": {}}
    cnt = {k: Counter() for k in ("epoca", "litologia", "roca", "ambiente", "falla")}
    tot = Counter()
    vistos = set()
    for gdb in gdbs:
        rep = {}
        try:
            d = procesar(gdb, args, rep)
        except Exception as e:
            ingesta["fallidas"][gdb.name] = str(e)[:200]
            continue
        cid = ident(d["m"], d["gb"])
        if cid in vistos:
            continue
        vistos.add(cid)
        cat = catalogo.get(d["m"] or "", {})
        ruta = out / f"{cid}.json"
        ruta.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        npol = len(d["p"])
        index["cartas"].append({"id": cid, "m": d["m"], "gb": d["gb"], "titulo": cat.get("titulo") or gdb.parent.name,
                                "region": G.L.normalizar_region(cat.get("region")), "bounds": d["bounds"], "np": npol,
                                "nf": len(d["f"]), "kb": round(ruta.stat().st_size / 1024)})
        for p in d["p"]:
            u = d["u"][p[0]]
            for e in u["ep"] or [SIN_EDAD]:
                cnt["epoca"][e] += 1
            cnt["litologia"][u["lc"]] += 1
            for r in u["lr"][:1]:
                cnt["roca"][r] += 1
            cnt["ambiente"][u["a"] or "Sin dato"] += 1
        for f in d["f"]:
            cnt["falla"][d["ft"][f[0]]] += 1
        sin_edad = sum(1 for p in d["p"] if d["u"][p[0]]["mx"] is None)
        sin_lito = sum(1 for p in d["p"] if d["u"][p[0]]["lc"] == LIT.SIN_LITO)
        tot.update(poligonos=npol, fallas=len(d["f"]), sin_edad=sin_edad, sin_litologia=sin_lito)
        ingesta["cartas"][cid] = dict(rep, poligonos=npol, fallas=len(d["f"]), sin_edad=sin_edad, sin_litologia=sin_lito, kb=index["cartas"][-1]["kb"])
        print(cid, npol, len(d["f"]), index["cartas"][-1]["kb"], "KB", rep.get("datum", ""))
    orden_ep = [e for e, _ in EPOCAS_ICS] + ["Precámbrico"]
    index["filtros"] = {
        "epoca": [[e, cnt["epoca"][e]] for e in orden_ep if cnt["epoca"][e]] + ([[SIN_EDAD, cnt["epoca"][SIN_EDAD]]] if cnt["epoca"][SIN_EDAD] else []),
        "litologia": [[k, n] for k, n in cnt["litologia"].most_common()],
        "roca": [[k, n] for k, n in cnt["roca"].most_common()],
        "ambiente": [[k, n] for k, n in cnt["ambiente"].most_common()],
        "falla": [[k, n] for k, n in cnt["falla"].most_common()],
    }
    index["totales"] = dict(tot)
    (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ingesta["totales"] = dict(tot, pct_sin_edad=round(100 * tot["sin_edad"] / max(tot["poligonos"], 1), 1),
                              pct_sin_litologia=round(100 * tot["sin_litologia"] / max(tot["poligonos"], 1), 1))
    (args.out / "ingesta.json").write_text(json.dumps(ingesta, ensure_ascii=False, indent=1), encoding="utf-8")
    return ingesta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdb-dir", type=pathlib.Path, default=G.GDB_DIR)
    ap.add_argument("--catalogo", type=pathlib.Path, default=G.CATALOGO)
    ap.add_argument("--out", type=pathlib.Path, default=G.PROY / "geochile-vectores")
    ap.add_argument("--solo", nargs="*", help="solo las GDB cuya ruta contiene alguno de estos textos (p. ej. GB-100)")
    args = ap.parse_args()
    ing = exportar(args)
    print(json.dumps(ing["totales"], ensure_ascii=False))
    for k, v in ing["fallidas"].items():
        print("  FALLÓ", k, v)


if __name__ == "__main__":
    main()
