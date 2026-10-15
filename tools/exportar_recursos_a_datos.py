"""Paquetes «Recursos Minerales» (shapefile + Atributos.mdb, MapInfo + .xls) -> datos puntuales del visor GeoChile.

Uso (desde la raíz del repo):
    python -I -X utf8 tools/exportar_recursos_a_datos.py [--rm-dir DIR] [--trabajo DIR] [--out datos]

Lee primero las GDB (como exportar_gdb_a_datos.py) y agrega encima los puntos de los paquetes de
publicaciones-sernageomin\\Recursos Minerales, para que regenerar sea determinista (no se suma dos veces):
    yacimientos (RMM_YACIMI / RMM_YACIM_N / RMN_RECURSOS / .xls), geocronología (GC_KAR_N, GC_ARAR_N, GC_OTRMETOD_N / .xls),
    estructuras (RMM_ESTRUCT / Puntos_Estructurales).

Trampas de estos paquetes (verificadas):
  * los .shp no traen .prj: el CRS se lee de la columna PROYECCION del .mdb («WGS84H19» -> EPSG:32719);
  * los paquetes de Coquimbo (M168, M169, M195, M305) están en PSAD56 UTM 19S (lo declaran los .TAB y el texto del PDF),
    con el towgs84 del propio MapInfo (-270,183,-390);
  * la tabla de atributos puede traer coordenadas malas (M84: UTM_NORTE = UTM_ESTE en RMM_ESTRUCT): la posición sale de
    la geometría del .shp/.TAB y la de la tabla solo se usa para contrastar (se informa en datos/ingesta.json);
  * las edades vienen como texto («64.40 +/- 2.7 Ma», "69+2 max", «145,80 +/- 1,1  Ma»).
"""
import argparse
import html
import math
import pathlib
import re
import shutil
import sys
import tempfile
import warnings
import zipfile
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import datos_lib as L  # noqa: E402
import exportar_gdb_a_datos as G  # noqa: E402

warnings.filterwarnings("ignore")
import pandas as pd  # noqa: E402
import pyodbc  # noqa: E402
import pyogrio  # noqa: E402
from pyproj import CRS, Transformer  # noqa: E402

PROY = G.PROY
RM_DIR = PROY / "publicaciones-sernageomin" / "Recursos Minerales"

# Datum de las coordenadas UTM 19S de cada paquete. WGS84 = lo que dice PROYECCION en el .mdb (metadato, sin contrastar con la
# lámina en M81/M82/M84/M85/M86); PSAD56 = declarado en los .TAB y en el texto del informe (M195, M305; M168/M169 por los .TAB).
DATUM = {m: "WGS84" for m in ("M81", "M82", "M84", "M85", "M86", "M89", "M104", "M105")}
DATUM.update({m: "PSAD56" for m in ("M168", "M169", "M195", "M305")})
_T = {
    "WGS84": Transformer.from_crs(32719, 4326, always_xy=True),
    "PSAD56": Transformer.from_crs(
        CRS.from_proj4("+proj=utm +zone=19 +south +ellps=intl +towgs84=-270,183,-390,0,0,0,0 +units=m +no_defs"),
        4326, always_xy=True),
}
# Correcciones de posición (metros UTM sumados a la geometría del .shp). M86: los yacimientos del shapefile vienen con el cambio de
# datum PSAD56->WGS84 aplicado DOS veces (las demás capas de M86, y todas las de M82/M84/M85, están bien). Evidencia: (1) los
# símbolos de la lámina caen +197 E / +368 N de los puntos (correlación de símbolos, 67 yacimientos; en M82/M84 el desfase es 0);
# (2) el rajo de El Venado Sur (imagen satelital Esri) está en la posición de la lámina, no en la del shapefile;
# (3) en M82/M84 el shapefile = listado impreso -(183, 355) m, por eso se suma esa misma traslación una vez.
CORRECCION_XY = {"M86": {"yacimientos": (183.0, 355.0)}}
EXTRAE = re.compile(r"\.(shp|dbf|shx|prj|tab|dat|map|id|ind|mdb|xls|txt)$", re.I)
TAMANOS = {"P": "Pequeño", "M": "Mediano", "G": "Grande", "MG": "Muy grande"}
NULOS = {"", "nan", "none", "<na>", "null"}


def nulo(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip().lower() in NULOS


def txt(v):
    return None if nulo(v) else re.sub(r"\s+", " ", str(v)).strip()


REGION_FIX = {"Bíobío": "Biobío", "Libertador General Bernardo OHiggins": "Libertador General Bernardo O'Higgins",
              "Aisén General Carlos Ibáñez del Campo": "Aisén del General Carlos Ibañez del Campo"}


def region_norm(v):
    """M104/M89 traen la región escrita a mano: entidades HTML («O&#039;Higgins»), «Bíobío», «OHiggins»."""
    v = txt(v)
    if not v:
        return None
    v = html.unescape(v)
    return "-".join(REGION_FIX.get(p, p) for p in v.split("-")) if "-" in v and "Chile-Argentina" not in v else REGION_FIX.get(v, v)


def num(v):
    """'378738,7' / 378738.7 / '40°SE' -> float (None si no hay número)."""
    if nulo(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(v))
    return float(m.group(0).replace(",", ".")) if m else None


# ── extracción y lectura ─────────────────────────────────────────────────────

def extraer(rm_dir, trabajo):
    """Extrae solo lo útil de cada zip a trabajo/<M>/ (ruta corta: MAX_PATH)."""
    paquetes = []
    for z in sorted(rm_dir.glob("*.zip")):
        m = re.match(r"(M\d+)", z.name).group(1)
        destino = trabajo / m
        if not destino.exists():
            with zipfile.ZipFile(z) as zf:
                for i in zf.infolist():
                    fn = i.filename.replace("\\", "/")
                    if i.is_dir() or not EXTRAE.search(fn) or "topograf" in fn.lower() or i.file_size > 60e6:
                        continue
                    t = destino / fn
                    t.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(i) as s, open(t, "wb") as o:
                        shutil.copyfileobj(s, o)
        paquetes.append(m)
    return paquetes


def tabla_access(mdb, tabla):
    c = pyodbc.connect(r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=" + str(mdb) + ";ReadOnly=1")
    try:
        cur = c.cursor()
        cur.execute(f"select * from [{tabla}]")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except pyodbc.Error:
        return None
    finally:
        c.close()


def geometrias_shp(shp):
    """{INT_ORIG: (x, y)} en el CRS de la hoja (UTM)."""
    if not shp.exists():
        return {}
    df = pyogrio.read_dataframe(str(shp))
    return {r["INT_ORIG"]: (g.x, g.y) for r, g in zip(df.drop(columns="geometry").to_dict("records"), df.geometry)
            if g is not None and not g.is_empty}


def a_wgs(m, x, y):
    return _T[DATUM[m]].transform(x, y)


# ── valores ──────────────────────────────────────────────────────────────────

def primero(r, *nombres):
    low = {k.lower(): v for k, v in r.items()}
    for n in nombres:
        v = txt(low.get(n.lower()))
        if v:
            return v
    return None


def unir(r, nombres, sep=", "):
    low = {k.lower(): v for k, v in r.items()}
    vals = []
    for n in nombres:
        v = txt(low.get(n.lower()))
        if v and v not in vals and v.lower() not in ("s/d", "s/i"):
            vals.append(v)
    return sep.join(vals) or None


_EDAD = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*(?:\+\s*/?\s*-|±|\+)?\s*(\d+(?:[.,]\d+)?)?")


def parsear_edad(v):
    """'64.40 +/- 2.7 Ma' / '145,80 +/- 1,1  Ma' / '69+2 max' / 109.0 -> (edad, error) en Ma (sin unidad = Ma)."""
    if nulo(v):
        return None, None
    if isinstance(v, (int, float)):
        return float(v), None
    m = _EDAD.search(str(v))
    if not m:
        return None, None
    e = float(m.group(1).replace(",", "."))
    er = float(m.group(2).replace(",", ".")) if m.group(2) else None
    return e, er


def metodo_de(*textos):
    t = " ".join(x for x in textos if x)
    return L.normalizar_metodo(t) if t.strip() else "Sin método"


# ── mapeo por tipo ───────────────────────────────────────────────────────────

def yacimiento(r, subtipo):
    d = {
        "nombre": primero(r, "NOMBRE", "Nombre"),
        "subtipo": subtipo,
        "sustancia": unir(r, ["MENA", "MENA_SUBORDINADA", "RECURSO", "RECURSO2", "Mena Principal", "Mena Subordinada"], " / "),
        "tipo_yacimiento": primero(r, "GENESIS"),
        "forma": unir(r, ["FORMA", "FORMA_1", "FORMA_2", "FORMA2", "FORMA3", "Forma"]),
        "mena": primero(r, "MINERALES_DE_MENA", "MINERALES", "Minerales de Mena"),
        "ganga": primero(r, "GANGA", "Minerales de Ganga"),
        "alteracion": primero(r, "MINERALES_ALTERACION", "ALTERACION", "Alteración"),
        "estado": unir(r, ["ESTADO", "ESTADO_2", "ESTADO2", "Estado"], " / "),
        "litologia_caja": unir(r, ["ROCA", "ROCA2", "ROCA3", "ROCA4", "TIPO_DE_ROCA", "TIPO_DE_ROCA_1", "TIPO_DE_ROCA2",
                                   "TIPO_DE_ROCA1", "TIPO_DE_ROCA3", "TP_ROCA", "TP_ROCA1", "Roca de caja"]),
        "unidad": unir(r, ["UNIDAD_GEOLOGICA", "UNIDAD_GEOLOGICA2", "UNIDAD1", "Unidad"], " / "),
        "distrito": primero(r, "DISTRITO"),
        "produccion": primero(r, "PRODUCCION", "Producción"),
        "reservas": primero(r, "RESERVAS"),
        "labores": unir(r, ["LABORES", "LABORES_1", "Labores"]),
        "ambiente": primero(r, "AMBIENTE", "AMBIENTE_GEOLOGICO", "Ambiente"),
        "uso": primero(r, "USO"), "mercado": primero(r, "MERCADO"),
        "textura": primero(r, "TEXTURAS", "Textura"),
        "ley": unir(r, ["LEY_DE_COBRE__MAX", "LEY_DE_COBRE__MIN", "LEY_DE_ORO__MIN", "LEY_DE_PLATA__MIN"], " · "),
        "referencia": unir(r, ["REFERENCIA", "REFERENCIA1", "REFERENCIA2", "REFERENCIA3", "REFERENCIA4", "REFERENCIA5",
                               "REFERENCIA6", "Referencias"]),
        "cota": num(primero(r, "COTA", "Altura")),
    }
    t = primero(r, "TAMANO", "Tamaño")
    d["tamano"] = TAMANOS.get(t, t) if t else None
    emax, emin = primero(r, "EDAD_ESTRAT___MAX", "EDAD_MAX", "Edad"), primero(r, "EDAD_ESTRAT___MIN", "EDAD_MIN")
    d["edad_yac"] = emax if not emin or emin == emax else f"{emax or '?'} a {emin}"
    rumbo, manteo = primero(r, "RUMBO", "Rumbo"), primero(r, "MANTEO", "Manteo")
    if rumbo or manteo:
        d["orientacion"] = "Rumbo " + (rumbo or "s/d") + (f" · Manteo {manteo}" if manteo else "")
    d["observacion"] = None
    return d


def dataciones_access(r, tabla):
    e, er = parsear_edad(r.get("EDAD"))
    metodo = {"GC_KAR_N": "K-Ar", "GC_ARAR_N": "Ar-Ar"}.get(tabla.upper(), "Otro método (sin especificar)")
    return {"metodo": metodo, "edad": e, "error": er, "unidad_edad": "Ma",
            "material": primero(r, "MATERIAL_DATADO"), "tipo_muestra": primero(r, "TIPO_DE_MUESTRA"),
            "litologia": primero(r, "TIPO_DE_ROCA"), "unidad": primero(r, "UNIDAD"), "muestra": primero(r, "MUESTRA"),
            "referencia": primero(r, "REFERENCIA"),
            "observacion": primero(r, "PROYECTO")}


def completar_geocron(d):
    ma, f, _ = L.edad_a_ma(d["edad"], "Ma", d["metodo"])
    d["edad_ma"] = None if ma is None else float(f"{ma:.6g}")
    d["error_ma"] = None if d["error"] is None else float(f"{d['error']:.4g}")
    era, per, ep = L.clasificar_edad(ma)
    d["epoca"], d["periodo"], d["era"] = ep, per, era
    if d["edad"] is not None:
        d["edad_txt"] = f"{d['edad']:g}" + (f" ± {d['error']:g}" if d["error"] is not None else "") + " Ma"


def estructura_access(r):
    return {"tipo": primero(r, "TYPE"), "azimut": num(r.get("RUMBO")), "buzamiento": num(r.get("MANTEO")),
            "dir_buz": primero(r, "DIRECCION"), "rake": num(r.get("RAKE"))}


# ── paquetes ─────────────────────────────────────────────────────────────────

def paquete_access(m, base, rep, salida):
    """M81..M89, M104, M105: shapefile (posición) + Atributos.mdb (atributos), unidos por INT_ORIG."""
    mdb = base / "Atributos.mdb"
    geo = base / "Geometria"
    plan = [("yacimientos", "RMM_YACIMI", "Metálico (RMM)"), ("yacimientos", "RMM_YACIM_N", "Metálico (RMM)"),
            ("yacimientos", "RMN_RECURSOS", "No metálico (RMN)"),
            ("geocronologia", "GC_KAR_N", None), ("geocronologia", "GC_ARAR_N", None), ("geocronologia", "GC_OTRMETOD_N", None),
            ("estructuras", "RMM_ESTRUCT", None)]
    for tipo, tabla, subtipo in plan:
        filas = tabla_access(mdb, tabla)
        if not filas:
            continue
        pos = geometrias_shp(geo / f"{tabla}.shp")
        for r in filas:
            xy = pos.get(r["INT_ORIG"])
            ex, ny = num(r.get("UTM_ESTE")), num(r.get("UTM_NORTE"))
            if xy is None:
                rep[f"{m}:{tabla}:sin_geometria"] += 1
                continue
            if ex is not None and ny is not None and abs(ex - xy[0]) < 2000:   # contraste con la tabla (M84 la trae mala)
                if abs(ex - xy[0]) > 5 or abs(ny - xy[1]) > 5:
                    rep[f"{m}:{tabla}:tabla_difiere_del_shp"] += 1
            elif ex is not None and abs(ex - xy[0]) >= 2000:
                rep[f"{m}:{tabla}:tabla_con_coordenadas_malas"] += 1
            dxy = CORRECCION_XY.get(m, {}).get(tipo)
            if dxy:
                xy = (xy[0] + dxy[0], xy[1] + dxy[1])
                rep[f"{m}:{tipo}:posicion_corregida"] += 1
            lon, lat = a_wgs(m, *xy)
            if tipo == "yacimientos":
                d = yacimiento(r, subtipo)
            elif tipo == "geocronologia":
                d = dataciones_access(r, tabla)
                completar_geocron(d)
            else:
                d = estructura_access(r)
            d["region"] = region_norm(primero(r, "REGION"))
            d["lon"], d["lat"] = lon, lat
            salida[tipo].append(d)
            rep[f"{m}:{tipo}"] += 1


def leer_tab(p, encoding=None):
    df = pyogrio.read_dataframe(str(p), encoding=encoding) if encoding else pyogrio.read_dataframe(str(p))
    return df.drop(columns="geometry").to_dict("records"), list(df.geometry)


def xls(p):
    return pd.read_excel(p, sheet_name=0)


def filas_xls(p):
    df = xls(p)
    df.columns = [str(c).strip() for c in df.columns]
    return df.to_dict("records")


def hallar(base, *patrones):
    for pat in patrones:
        for q in base.rglob("*"):
            if q.is_file() and re.fullmatch(pat, q.name, re.I):
                return q
    return None


def paquete_coquimbo(m, base, rep, salida):
    """M168, M169, M195, M305: tablas .xls / .TAB de MapInfo, PSAD56 UTM 19S."""
    yac = {"M168": "Yacimientos_Montepatria.xls", "M169": "Yacimientos_Vicuña.xls",
           "M195": "Yacimientos_LaSerena_LaHiguera.xls", "M305": "Yacimientos_Condoriaco_Rivadavia.xls"}[m]
    p = hallar(base, re.escape(yac))
    for r in filas_xls(p):
        x, y = num(r.get("Utm_Este")), num(r.get("Utm_Norte"))
        if x is None or y is None or not (1e5 < x < 9e5):
            rep[f"{m}:yacimientos:sin_coordenadas"] += 1
            continue
        d = yacimiento(r, "Metálico (RMM)")
        d["region"] = "Coquimbo"
        d["lon"], d["lat"] = a_wgs(m, x, y)
        salida["yacimientos"].append(d)
        rep[f"{m}:yacimientos"] += 1
    # dataciones
    if m == "M168":
        reg, geoms = leer_tab(hallar(base, r"Dataciones_Montepatria09\.TAB"), "latin-1")
        for r, g in zip(reg, geoms):
            k = {c[:6].upper(): v for c, v in r.items()}
            mat = txt(r.get("MATERIAL"))
            e, er = parsear_edad(r.get("EDAD_MA"))
            met = metodo_de(mat)
            d = {"metodo": met, "edad": e, "error": er, "unidad_edad": "Ma",
                 "material": re.sub(r"^\s*\d+\s*", "", re.sub(r"K-?Ar", "", mat or "", flags=re.I)).strip() or None,
                 "litologia": k.get("LITOLO"), "muestra": txt(r.get("MUESTRA")),
                 "observacion": txt(k.get("OBSERV")), "region": "Coquimbo"}
            completar_geocron(d)
            d["lon"], d["lat"] = a_wgs(m, g.x, g.y)
            salida["geocronologia"].append(d)
            rep[f"{m}:geocronologia"] += 1
        for r in filas_xls(hallar(base, r"Dataciones_Yacimientos_Montepatria\.xls")):
            x, y = num(r.get("ESTE")), num(r.get("NORTE"))
            e, er = parsear_edad(r.get("EDAD_MA"))
            if x is None or y is None:
                continue
            d = {"metodo": metodo_de(txt(r.get("TIPO"))), "edad": e, "error": er, "unidad_edad": "Ma",
                 "material": txt(r.get("MATERIAL")), "litologia": txt(r.get("LITOLOGIA")), "muestra": txt(r.get("MUESTRA")),
                 "region": "Coquimbo"}
            completar_geocron(d)
            d["lon"], d["lat"] = a_wgs(m, x, y)
            salida["geocronologia"].append(d)
            rep[f"{m}:geocronologia"] += 1
    else:
        arch = {"M169": "Dat_Vicuña.xls", "M195": "Dataciones_La Serena.xls", "M305": "Dataciones_Condoriaco.xls"}[m]
        for r in filas_xls(hallar(base, re.escape(arch))):
            if m == "M169":
                x, y, (e, er), met = num(r.get("ESTE")), num(r.get("NORTE")), parsear_edad(r.get("EDAD")), r.get("METODO")
                mat, lit, mu, ref = txt(r.get("MATERIAL_D")), txt(r.get("LITOLOGIA")), txt(r.get("MUESTRA")), txt(r.get("REFERENCIA"))
                un, obs = None, unir(r, ["LOCALIDAD", "PROYECTO"], " · ")
            else:
                x, y = num(r.get("UTM E")), num(r.get("UTM N"))
                e, er = num(r.get("Edad")), num(r.get("Error"))
                met, mat, lit = r.get("Método"), txt(r.get("Mineral")), txt(r.get("Litología"))
                mu, ref, un, obs = txt(r.get("Código")), txt(r.get("Autor")), txt(r.get("Unidad")), None
            if x is None or y is None or not (1e5 < x < 9e5):
                rep[f"{m}:geocronologia:sin_coordenadas"] += 1
                continue
            d = {"metodo": metodo_de(txt(met)), "edad": e, "error": er, "unidad_edad": "Ma", "material": mat,
                 "litologia": lit, "unidad": un, "muestra": mu, "referencia": ref, "observacion": obs, "region": "Coquimbo"}
            completar_geocron(d)
            d["lon"], d["lat"] = a_wgs(m, x, y)
            salida["geocronologia"].append(d)
            rep[f"{m}:geocronologia"] += 1
    # estructuras
    arch = {"M168": "Puntos_Estructurales_Montepatria.TAB", "M169": "Puntos_Estructurales_Vicuña.TAB",
            "M195": "Puntos_Estructurales.TAB", "M305": "Puntos_Estructurales.TAB"}[m]
    reg, geoms = leer_tab(hallar(base, re.escape(arch)))
    for r, g in zip(reg, geoms):
        low = {k.lower(): v for k, v in r.items()}
        if m == "M168":
            d = {"tipo": f"Estructura (cód. {int(low['tipo'])})", "azimut": num(low["rumbo"]), "buzamiento": num(low["manteo"])}
        elif m == "M169":
            d = {"tipo": txt(low["tipo_estru"]), "azimut": num(low["ru360"]), "buzamiento": num(low["structur_3"]),
                 "dir_buz": txt(low["structur_4"])}
        else:
            bz = num(low.get("manteo")) or num(low.get("buzamiento"))
            d = {"tipo": f"Estructura (cód. {txt(low['cd_estructura'])})", "azimut": num(low["rumbo"]), "buzamiento": bz,
                 "dir_buz": txt(low.get("dir_manteo") or low.get("dir_manteo")), "rake": num(low.get("rakenum"))}
        d["region"] = "Coquimbo"
        d["lon"], d["lat"] = a_wgs(m, g.x, g.y)
        salida["estructuras"].append(d)
        rep[f"{m}:estructuras"] += 1


# ── integración con lo ya exportado de las GDB ───────────────────────────────

def clave_cerca(r):
    return (round(r["lon"] * 4000), round(r["lat"] * 4000))   # celdas de ~28 m


def duplicado(tipo, r, indice):
    """Mismo punto que uno ya cargado (de una GDB u otro paquete): <~30 m y misma muestra/nombre/edad."""
    cx, cy = clave_cerca(r)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for o in indice.get((cx + dx, cy + dy), ()):
                if abs(o["lon"] - r["lon"]) > 3.5e-4 or abs(o["lat"] - r["lat"]) > 3.5e-4:
                    continue
                if tipo == "geocronologia":
                    if o.get("edad_ma") is not None and r.get("edad_ma") is not None and abs(o["edad_ma"] - r["edad_ma"]) < 0.06:
                        return True
                elif tipo == "yacimientos":
                    a, b = (o.get("nombre") or "").lower(), (r.get("nombre") or "").lower()
                    if a == b and a not in ("", "s/n") or (abs(o["lon"] - r["lon"]) < 1e-4 and abs(o["lat"] - r["lat"]) < 1e-4):
                        return True
                elif tipo == "estructuras":
                    if o.get("azimut") == r.get("azimut") and o.get("buzamiento") == r.get("buzamiento"):
                        return True
    return False


def agregar_recursos(tablas, cartas, ingesta, args):
    catalogo = G.cargar_catalogo(args.catalogo)
    trabajo = args.trabajo
    trabajo.mkdir(parents=True, exist_ok=True)
    paquetes = extraer(args.rm_dir, trabajo)
    ingesta["recursos"] = {"datum": {m: DATUM[m] for m in paquetes if m in DATUM}, "paquetes": {}}
    indices = {t: {} for t in tablas}
    for t, filas in tablas.items():
        for r in filas:
            indices[t].setdefault(clave_cerca(r), []).append(r)
    for m in paquetes:
        base = trabajo / m
        rep = Counter()
        salida = {"yacimientos": [], "geocronologia": [], "estructuras": []}
        if (base / "Atributos.mdb").exists():
            paquete_access(m, base, rep, salida)
        elif m in ("M168", "M169", "M195", "M305"):
            paquete_coquimbo(m, base, rep, salida)
        else:
            continue
        if not any(salida.values()):
            ingesta["recursos"]["paquetes"][m] = {"sin_puntos": True, **dict(rep)}
            continue
        cat = catalogo.get(m, {})
        region = cat.get("region")
        region = None if region in (None, "-", "") else region
        ci = len(cartas)
        cartas.append({"m": m, "gb": None, "titulo": cat.get("titulo") or m, "anio": cat.get("ano"),
                       "autor": cat.get("autor"), "escala": cat.get("escala"), "region": region})
        for tipo, filas in salida.items():
            for r in filas:
                lon, lat = r["lon"], r["lat"]
                if not (G.LON_RNG[0] <= lon <= G.LON_RNG[1] and G.LAT_RNG[0] <= lat <= G.LAT_RNG[1]):
                    rep["fuera_de_rango"] += 1
                    continue
                if duplicado(tipo, r, indices[tipo]):
                    rep[f"duplicados_{tipo}"] += 1
                    continue
                r["region"] = r.get("region") or region
                r["_c"] = ci
                tablas[tipo].append(r)
                indices[tipo].setdefault(clave_cerca(r), []).append(r)
                rep[f"cargados_{tipo}"] += 1
        ingesta["recursos"]["paquetes"][m] = dict(rep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdb-dir", type=pathlib.Path, default=G.GDB_DIR)
    ap.add_argument("--catalogo", type=pathlib.Path, default=G.CATALOGO)
    ap.add_argument("--rm-dir", type=pathlib.Path, default=RM_DIR)
    ap.add_argument("--trabajo", type=pathlib.Path, default=pathlib.Path(tempfile.gettempdir()) / "geochile_rm")
    ap.add_argument("--out", type=pathlib.Path, default=G.RAIZ / "datos")
    args = ap.parse_args()
    tablas, cartas, ingesta = G.exportar(args)
    agregar_recursos(tablas, cartas, ingesta, args)
    G.POPUP["yacimientos"] += [("produccion", "Producción"), ("reservas", "Reservas"), ("labores", "Labores"),
                               ("ambiente", "Ambiente"), ("textura", "Textura"), ("ley", "Ley"),
                               ("orientacion", "Orientación"), ("uso", "Uso"), ("mercado", "Mercado"),
                               ("cota", "Cota (m)"), ("referencia", "Referencia")]
    G.FILTROS["yacimientos"] += [("distrito", "texto", "Distrito")]
    G.escribir(tablas, cartas, ingesta, args.out)
    print(__import__("json").dumps(ingesta["totales"], ensure_ascii=False))
    for m, rep in ingesta["recursos"]["paquetes"].items():
        print(m, rep)


if __name__ == "__main__":
    main()
