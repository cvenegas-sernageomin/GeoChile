import json, sys

CATS = {"geologia", "aplicada", "historico", "academico", "hillshade"}
REQ = {"id", "categoria", "titulo", "bounds", "overlay", "leyenda", "opacidad", "recortado"}

def validar(capas):
    errores = []
    ids = set()
    if not isinstance(capas, list):
        return ["raiz debe ser una lista"]
    for i, c in enumerate(capas):
        pre = f"[{i}] "
        faltan = REQ - set(c)
        if faltan:
            errores.append(pre + "faltan campos: " + ", ".join(sorted(faltan)))
            continue
        if c["categoria"] not in CATS:
            errores.append(pre + f"categoria desconocida: {c['categoria']}")
        if c["id"] in ids:
            errores.append(pre + f"id duplicado: {c['id']}")
        ids.add(c["id"])
        b = c["bounds"]
        if not all(k in b for k in ("n", "s", "e", "w")):
            errores.append(pre + "bounds requiere n,s,e,w")
        else:
            if b["n"] <= b["s"]:
                errores.append(pre + "bounds: north debe ser > south")
            if b["e"] <= b["w"]:
                errores.append(pre + "bounds: east debe ser > west")
        if not (0.0 <= c["opacidad"] <= 1.0):
            errores.append(pre + "opacidad fuera de [0,1]")
        if c["leyenda"] is not None and not isinstance(c["leyenda"], str):
            errores.append(pre + "leyenda debe ser ruta string o null")
    return errores

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "capas.json"
    with open(path, encoding="utf-8") as f:
        capas = json.load(f)
    errs = validar(capas)
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    print(f"OK: {len(capas)} capas validas")

if __name__ == "__main__":
    main()
