"""Valida datos/index.json y datos/<tipo>.json (salida de exportar_gdb_a_datos.py).

Uso: python -I -X utf8 tools/validar_datos.py [datos_dir]
Sale con código 1 si algo falla.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import datos_lib as L  # noqa: E402

LON, LAT = (-110.0, -60.0), (-60.0, -15.0)


def validar(datos_dir):
    errs = []
    idx = json.loads((datos_dir / "index.json").read_text(encoding="utf-8"))
    ncartas = len(idx["cartas"])
    if not idx["tipos"]:
        errs.append("index.json sin tipos")
    for tipo, t in idx["tipos"].items():
        ruta = datos_dir / pathlib.Path(t["archivo"]).name
        if not ruta.exists():
            errs.append(f"{tipo}: falta {ruta.name}")
            continue
        d = json.loads(ruta.read_text(encoding="utf-8"))
        n = d["n"]
        if n != t["n"]:
            errs.append(f"{tipo}: n del índice ({t['n']}) != n del archivo ({n})")
        for k in ("lon", "lat", "c"):
            if len(d[k]) != n:
                errs.append(f"{tipo}: columna {k} tiene {len(d[k])} filas, se esperaban {n}")
        esc = d["esc"]
        for i, (x, y) in enumerate(zip(d["lon"], d["lat"])):
            if not (LON[0] <= x / esc <= LON[1] and LAT[0] <= y / esc <= LAT[1]):
                errs.append(f"{tipo}: punto {i} fuera de rango ({x / esc}, {y / esc})")
                break
        if d["c"] and (min(d["c"]) < 0 or max(d["c"]) >= ncartas):
            errs.append(f"{tipo}: índice de carta fuera de rango")
        for campo, col in d.items():
            if campo in ("n", "esc", "lon", "lat", "c"):
                continue
            largo = len(col["v"]) if isinstance(col, dict) else len(col)
            if largo != n:
                errs.append(f"{tipo}.{campo}: {largo} filas, se esperaban {n}")
            if isinstance(col, dict) and col["v"] and max(col["v"]) >= len(col["d"]):
                errs.append(f"{tipo}.{campo}: índice fuera del diccionario")
        for f in t["filtros"]:
            if f["campo"] not in d:
                errs.append(f"{tipo}: filtro sobre campo inexistente {f['campo']}")
        for campo, _ in t["popup"]:
            if campo not in d:
                errs.append(f"{tipo}: popup sobre campo inexistente {campo}")
        if tipo == "geocronologia":
            ma = L.decodificar(d["edad_ma"])
            ep = L.decodificar(d["epoca"])
            for i, (m, e) in enumerate(zip(ma, ep)):
                if m is None:
                    continue
                if m < 0 or m > 4600:
                    errs.append(f"geocronologia: edad_ma imposible en fila {i}: {m}")
                    break
                if L.clasificar_edad(m)[2] != e:
                    errs.append(f"geocronologia: época inconsistente en fila {i}: {m} Ma -> {e}")
                    break
            unidades = L.decodificar(d["unidad_edad"]) if "unidad_edad" in d else []
            sin_resolver = sorted({u for u in unidades if u and u.startswith("DAT-")})
            if sin_resolver:
                errs.append(f"geocronologia: unidades de edad sin resolver: {sin_resolver}")
    return errs


if __name__ == "__main__":
    carpeta = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / "datos"
    errores = validar(carpeta)
    for e in errores:
        print("ERROR:", e)
    print("OK: datos validos" if not errores else f"{len(errores)} errores")
    sys.exit(1 if errores else 0)
