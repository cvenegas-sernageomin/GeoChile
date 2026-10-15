"""GDB Esri de SERNAGEOMIN -> datos puntuales para el visor GeoChile (datos/*.json).

Uso (desde la raíz del repo):
    python -I -X utf8 tools/exportar_gdb_a_datos.py [--gdb-dir DIR] [--catalogo CSV] [--out datos]

Resuelve los dominios Esri POR GDB (los códigos como DAT-UNIDAD-4 cambian de significado según la plantilla),
convierte todas las edades a Ma, clasifica la época desde la edad, reproyecta a WGS84 y escribe:
    datos/index.json       cartas + filtros de cada tipo
    datos/<tipo>.json      columnas por tipo (formato columnar, ver datos_lib.columna)
    datos/ingesta.json     informe: puntos por GDB, descartes, duplicados, GDB que no se pudieron leer
"""
import argparse
import csv
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

warnings.filterwarnings("ignore")
import pyogrio  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PROY = RAIZ.parent
GDB_DIR = PROY / "cartas-geologicas-sernageomin" / "_mapas_por_ingresar" / "gdb_extraidos"
CATALOGO = PROY / "publicaciones-sernageomin" / "catalogo.csv"
LON_RNG, LAT_RNG = (-110.0, -60.0), (-60.0, -15.0)

CAPAS = {
    "geocronologia": re.compile(r"^(GB_GEOCRONOLOGIA(_\d+)?|Dataciones|GC_(KAR|ARAR|OTRMETOD)_N)$", re.I),
    "fosiles": re.compile(r"^GB_FOSIL(_\d+)?$", re.I),
    "yacimientos": re.compile(r"^RM[MIN]_YACIMIENTO$", re.I),
    "estructuras": re.compile(r"^(GB_ESTRUCTURA|GB_MEDIDA_ESTRUCTURAL)$", re.I),
}
# Unidades de edad cuando la GDB no trae el dominio (o lo trae con textos contradictorios): significado
# estable en las 79 GDB con plantilla antigua. DAT-UNIDAD-4 NO está aquí: cambia de significado entre plantillas.
UNIDAD_GLOBAL = {"DAT-UNIDAD-1": "Ma", "DAT-UNIDAD-2": "a AP", "DAT-UNIDAD-3": "ka"}
SUBTIPO_YAC = {"RMM": "Metálico (RMM)", "RMN": "No metálico (RMN)", "RMI": "Industrial (RMI)"}

# campo de salida -> alias de campo en las GDB (el primero con valor gana; no distingue mayúsculas)
ALIAS = {
    "geocronologia": {
        "metodo_txt": ["SUBTIPO_DESC", "SUBTIPO_DE", "METODO"],
        "edad": ["EDAD", "EDAD1"], "error": ["ERROR"],
        "unidad_edad": ["UNIDAD_MEDIDA", "UNIDAD_MED"],
        "material": ["MATERIAL_DAT", "MATERIAL", "MATER"],
        "tipo_muestra": ["TIPO_MUESTRA", "TIPO_MUEST"],
        "litologia": ["LITOLOGIA", "LITO"],
        "unidad": ["UNIDAD_GEOLOGICA", "UNIDAD"],
        "muestra": ["NOMBRE_MUESTRA", "SIGLA_MUESTRA", "NOMBRE_MU", "NOMBRE_MUE", "MUESTRA", "ID_MUESTRA"],
        "referencia": ["REFERENCIA", "REFERE", "REF"],
        "observacion": ["OBSERVACION", "COMENTARIO"],
        "certificado": ["URL_CERTIFICADO"],
    },
    "fosiles": {
        "taxon": ["TAXON", "ESPECIE"],
        "tipo": ["TP_FOSIL", "SUBTIPO_DESC"],
        "localidad": ["LOCALIDAD"],
        "periodo_txt": ["PERIODO_MAX", "PERIODO_MIN"],
        "epoca_txt": ["EPOCA_MAX", "EPOCA"],
        "edad_estrat": ["EDAD_MAX", "EDAD"],
        "unidad": ["UNIDAD_GEOLOGICA", "UNIDADGENERICA"],
        "ambiente": ["AMBIENTE"],
        "muestra": ["SIGLA_MUESTRA", "NOMBRE_MUESTRA", "MUESTRA", "ID_MUESTRA"],
        "referencia": ["REFERENCIA"],
        "informe_url": ["URL_INFORME"],
        "observacion": ["OBSERVACION"],
    },
    "yacimientos": {
        "nombre": ["NOMBRE"],
        "sustancia": ["RECURSO_PRINCIPAL", "RECURSOS", "ASOCIACION_RECURSO", "ASS_MENA"],
        "tipo_yacimiento": ["TIPO_YACIMIENTO", "MODELO_YACIMIENTO", "PROCESO_GENETICO"],
        "forma": ["FORMA_YACIMIENTO", "FORMA"],
        "tamano": ["TAMANO_YACI"],
        "mena": ["MINERALES_MENA"], "ganga": ["MINERALES_GANGA"], "alteracion": ["MINERALES_ALTERACION"],
        "estado": ["ESTADO"],
        "edad_yac": ["EDAD_YACIMIENTO"],
        "litologia_caja": ["LITOLOGIA_CAJA"],
        "unidad": ["UNIDAD_GEOLOGICA"],
        "distrito": ["DISTRITO"],
        "observacion": ["OBSERVACIONES"],
    },
    "estructuras": {
        "tipo": ["TIPO", "TP_MEDIDA_ESTRUCT"],
        "azimut": ["AZIMUTH", "AZIMUT"],
        "buzamiento": ["BUZAMIENTO", "MANTEO", "MANTEO_BUZAMIENTO"],
        "dir_buz": ["DIR_BUZAMIENTO", "DIR_MANTEO"],
        "rake": ["RAKE"],
        "observacion": ["OBSERVACION"],
    },
}
NUMERICOS = {"edad", "error", "azimut", "buzamiento", "rake"}

# Filtros que la interfaz genera: (campo, control, etiqueta)
FILTROS = {
    "geocronologia": [("metodo", "multi", "Método"), ("epoca", "multi", "Época"), ("edad_ma", "rango", "Edad (Ma)"),
                      ("material", "multi", "Material"), ("region", "multi", "Región"),
                      ("litologia", "texto", "Litología"), ("unidad", "texto", "Unidad"), ("muestra", "texto", "Muestra")],
    "fosiles": [("periodo", "multi", "Periodo"), ("epoca", "multi", "Época"), ("region", "multi", "Región"),
                ("taxon", "texto", "Taxón"), ("unidad", "texto", "Unidad"), ("localidad", "texto", "Localidad")],
    "yacimientos": [("subtipo", "multi", "Tipo de recurso"), ("estado", "multi", "Estado"), ("region", "multi", "Región"),
                    ("sustancia", "texto", "Sustancia"), ("nombre", "texto", "Nombre"), ("mena", "texto", "Minerales de mena")],
    "estructuras": [("tipo", "multi", "Tipo"), ("region", "multi", "Región"), ("buzamiento", "rango", "Buzamiento (°)"),
                    ("azimut", "rango", "Azimut (°)")],
}
POPUP = {
    "geocronologia": [("metodo", "Método"), ("edad_txt", "Edad"), ("epoca", "Época"), ("material", "Material"),
                      ("litologia", "Litología"), ("unidad", "Unidad"), ("tipo_muestra", "Tipo de muestra"),
                      ("muestra", "Muestra"), ("referencia", "Referencia"), ("observacion", "Observación")],
    "fosiles": [("taxon", "Taxón"), ("tipo", "Tipo"), ("periodo", "Periodo"), ("epoca", "Época"),
                ("edad_estrat", "Edad"), ("unidad", "Unidad"), ("localidad", "Localidad"), ("ambiente", "Ambiente"),
                ("muestra", "Muestra"), ("referencia", "Referencia")],
    "yacimientos": [("nombre", "Nombre"), ("subtipo", "Recurso"), ("sustancia", "Sustancia"),
                    ("tipo_yacimiento", "Tipo / modelo"), ("forma", "Forma"), ("tamano", "Tamaño"), ("estado", "Estado"),
                    ("edad_yac", "Edad"), ("mena", "Mena"), ("ganga", "Ganga"), ("alteracion", "Alteración"),
                    ("litologia_caja", "Roca de caja"), ("unidad", "Unidad"), ("distrito", "Distrito"),
                    ("observacion", "Observaciones")],
    "estructuras": [("tipo", "Tipo"), ("azimut", "Azimut"), ("buzamiento", "Buzamiento"), ("dir_buz", "Dirección"),
                    ("rake", "Rake"), ("observacion", "Observación")],
}
TITULO = {"geocronologia": "Geocronología (dataciones)", "fosiles": "Fósiles", "yacimientos": "Yacimientos minerales",
          "estructuras": "Mediciones estructurales"}
COLOR_POR = {"geocronologia": "metodo", "fosiles": "periodo", "yacimientos": "subtipo", "estructuras": "tipo"}
ORDEN_EPOCAS = [e[3] for e in L.ICS] + ["Precámbrico"]


def nulo(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in ("", "nan", "None", "<NA>")


def cargar_catalogo(ruta):
    out = {}
    if not ruta.exists():
        return out
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            out[r["codigo"].strip()] = r
    return out


def codigo_carta(gdb):
    """('M25', 'GB-91') desde la ruta de la GDB; ninguno si no hay."""
    m = g = None
    for nombre in (gdb.parent.name, gdb.name):
        mm = re.search(r"(?<![A-Za-z])(M\d{1,3})(?!\d)", nombre)
        if mm and not m:
            m = mm.group(1)
        gg = re.search(r"(GB-[\w-]+?)(?:_|$)", nombre)
        if gg and not g:
            g = gg.group(1)
    return m, g


def leer_dominios(gdb):
    """Una lectura de GDB_Items -> (dominios {nombre:{codigo:texto}}, GDB_Items df)."""
    items = pyogrio.read_dataframe(str(gdb), layer="GDB_Items", read_geometry=False)
    cv = items[items["Type"] == "{8C368B12-A12E-4C7E-9638-C9C64E69E98F}"]["Definition"]
    return L.parsear_dominios(cv), items


def a_numero(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def procesar_capa(gdb, capa, tipo, dominios, respaldo, items, rep):
    import geopandas as gpd  # noqa: F401  (lo exige pyogrio.read_dataframe con geometría)
    df = pyogrio.read_dataframe(str(gdb), layer=capa)
    if len(df) == 0:
        return []
    campo_dom = {}
    fila = items[items["Name"] == capa]
    if len(fila):
        campo_dom = L.campos_con_dominio(fila.iloc[0]["Definition"])
    # coordenadas WGS84
    if df.crs is not None:
        g = df.to_crs(4326).geometry
    else:
        rep["sin_crs"] += 1
        df = df.set_crs(31994)
        g = df.to_crs(4326).geometry
    cols = {c.lower(): c for c in df.columns if c != df.geometry.name}
    recs = df.drop(columns=df.geometry.name).to_dict("records")
    alias = ALIAS[tipo]
    filas = []
    for i in range(len(df)):
        geom = g.iloc[i]
        if geom is None or geom.is_empty:
            rep["sin_geometria"] += 1
            continue
        lon, lat = geom.x, geom.y
        if not (LON_RNG[0] <= lon <= LON_RNG[1] and LAT_RNG[0] <= lat <= LAT_RNG[1]):
            rep["fuera_de_rango"] += 1
            continue
        reg = {"lon": lon, "lat": lat}
        for out_name, nombres in alias.items():
            val = None
            for n in nombres:
                c = cols.get(n.lower())
                if c is None:
                    continue
                v = recs[i][c]
                if nulo(v):
                    continue
                if out_name not in NUMERICOS:
                    v = L.resolver(v, dominios.get(campo_dom.get(c)), respaldo)
                    if v is not None:
                        v = str(v).strip()
                val = v
                break
            reg[out_name] = val
        filas.append(reg)
    return filas


def completar(tipo, r, capa):
    """Campos derivados por tipo."""
    if tipo == "geocronologia":
        r["metodo"] = L.normalizar_metodo(r.pop("metodo_txt"))
        r["edad"], r["error"] = a_numero(r["edad"]), a_numero(r["error"])
        if r["unidad_edad"] in UNIDAD_GLOBAL:
            r["unidad_edad"] = UNIDAD_GLOBAL[r["unidad_edad"]]
        ma, f, inferida = L.edad_a_ma(r["edad"], r["unidad_edad"], r["metodo"])
        r["edad_ma"] = None if ma is None else float(f"{ma:.6g}")
        r["error_ma"] = None if (r["error"] is None or f is None) else float(f"{r['error'] * f:.4g}")
        r["_inferida"] = inferida
        era, per, ep = L.clasificar_edad(ma)
        r["epoca"], r["periodo"], r["era"] = ep, per, era
        if r["edad"] is not None:
            e = f"{r['edad']:g}" + (f" ± {r['error']:g}" if r["error"] is not None else "")
            r["edad_txt"] = f"{e} {r['unidad_edad'] or ''}".strip() + (f"  (= {r['edad_ma']:g} Ma)" if f not in (None, 1.0) else "")
    elif tipo == "fosiles":
        per, ep = L.periodo_epoca_de_texto(r.get("epoca_txt"), r.get("edad_estrat"), r.get("periodo_txt"))
        r["periodo"] = per or r.get("periodo_txt")
        r["epoca"] = ep or r.get("epoca_txt")
    elif tipo == "yacimientos":
        r["subtipo"] = SUBTIPO_YAC.get(capa[:3].upper(), capa)
    elif tipo == "estructuras":
        for k in ("azimut", "buzamiento", "rake"):
            r[k] = a_numero(r.get(k))


def clave_dup(r):
    return tuple((k, r[k]) for k in sorted(r) if not k.startswith("_"))


def exportar(args):
    catalogo = cargar_catalogo(args.catalogo)
    gdbs = sorted(p for p in args.gdb_dir.rglob("*.gdb") if p.is_dir())
    tablas = {t: [] for t in CAPAS}
    cartas, idx_carta = [], {}
    ingesta = {"generado": datetime.datetime.now().isoformat(timespec="seconds"), "gdb": {}, "fallidas": {}}
    for gdb in gdbs:
        m, gb = codigo_carta(gdb)
        clave = (m, gb, gdb.parent.name)
        rep = Counter()
        try:
            capas = pyogrio.list_layers(str(gdb))
            dominios, items = leer_dominios(gdb)
            respaldo = L.codigos_unicos(dominios)
        except Exception as e:  # GDB bloqueada, corrupta o sin tablas de sistema
            ingesta["fallidas"][str(gdb.relative_to(args.gdb_dir))] = str(e)[:200]
            continue
        if clave not in idx_carta:
            cat = catalogo.get(m or "", {})
            idx_carta[clave] = len(cartas)
            cartas.append({"m": m, "gb": gb, "titulo": cat.get("titulo") or gdb.parent.name, "anio": cat.get("ano"),
                           "autor": cat.get("autor"), "escala": cat.get("escala"), "region": cat.get("region")})
        ci = idx_carta[clave]
        region = cartas[ci]["region"]
        vistos = {t: set() for t in CAPAS}
        for nombre, geom in capas:
            for tipo, patron in CAPAS.items():
                if not patron.match(nombre) or "Point" not in str(geom):
                    continue
                try:
                    filas = procesar_capa(gdb, nombre, tipo, dominios, respaldo, items, rep)
                except Exception as e:
                    ingesta["fallidas"][f"{gdb.name}::{nombre}"] = str(e)[:200]
                    continue
                for r in filas:
                    completar(tipo, r, nombre)
                    r["region"], r["_c"] = region, ci
                    k = clave_dup(r)
                    if k in vistos[tipo]:
                        rep[f"duplicados_{tipo}"] += 1
                        continue
                    vistos[tipo].add(k)
                    if r.get("_inferida"):
                        rep["edad_unidad_inferida"] += 1
                    tablas[tipo].append(r)
                    rep[tipo] += 1
        ingesta["gdb"][str(gdb.relative_to(args.gdb_dir))] = dict(rep)
    return tablas, cartas, ingesta


def escribir(tablas, cartas, ingesta, out):
    out.mkdir(exist_ok=True)
    index = {"generado": ingesta["generado"], "cartas": cartas, "tipos": {}}
    for tipo, filas in tablas.items():
        if not filas:
            continue
        campos = sorted({k for r in filas for k in r if not k.startswith("_") and k not in ("lon", "lat")})
        data = {"n": len(filas), "esc": 100000,
                "lon": [round(r["lon"] * 1e5) for r in filas], "lat": [round(r["lat"] * 1e5) for r in filas],
                "c": [r["_c"] for r in filas]}
        for c in campos:
            col = L.columna([r.get(c) for r in filas])
            if isinstance(col, list) and all(v is None for v in col):
                continue
            data[c] = col
        (out / f"{tipo}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        filtros = []
        for campo, control, etiqueta in FILTROS[tipo]:
            if campo not in data:
                continue
            f = {"campo": campo, "control": control, "etiqueta": etiqueta}
            vals = L.decodificar(data[campo])
            if control == "multi":
                cnt = Counter(v for v in vals if v is not None)
                orden = (lambda kv: (ORDEN_EPOCAS.index(kv[0]) if kv[0] in ORDEN_EPOCAS else 99, kv[0])) \
                    if campo == "epoca" else (lambda kv: (-kv[1], kv[0]))
                f["valores"] = [[k, n] for k, n in sorted(cnt.items(), key=orden)]
            elif control == "rango":
                nums = [v for v in vals if v is not None]
                if not nums:
                    continue
                f["min"], f["max"] = min(nums), max(nums)
            filtros.append(f)
        index["tipos"][tipo] = {"archivo": f"datos/{tipo}.json", "n": len(filas), "titulo": TITULO[tipo],
                                "filtros": filtros, "popup": [list(p) for p in POPUP[tipo] if p[0] in data],
                                "color_por": COLOR_POR[tipo], "bytes": (out / f"{tipo}.json").stat().st_size}
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ingesta["totales"] = {t: len(f) for t, f in tablas.items()}
    (out / "ingesta.json").write_text(json.dumps(ingesta, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdb-dir", type=pathlib.Path, default=GDB_DIR)
    ap.add_argument("--catalogo", type=pathlib.Path, default=CATALOGO)
    ap.add_argument("--out", type=pathlib.Path, default=RAIZ / "datos")
    args = ap.parse_args()
    tablas, cartas, ingesta = exportar(args)
    escribir(tablas, cartas, ingesta, args.out)
    print(json.dumps(ingesta["totales"], ensure_ascii=False))
    print(f"{len(ingesta['gdb'])} GDB leídas, {len(ingesta['fallidas'])} fallidas")
    for k, v in ingesta["fallidas"].items():
        print("  FALLÓ", k, v[:120])


if __name__ == "__main__":
    main()
