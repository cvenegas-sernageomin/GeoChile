"""Funciones puras para convertir las GDB de SERNAGEOMIN en datos puntuales para el visor.

Sin dependencias de GDAL: todo lo que se puede probar sin abrir una GDB vive aquí
(conversión de edades, época geológica, método, resolución de dominios, codificación columnar).
"""
import math
import re
import xml.etree.ElementTree as ET

# Límites inferiores (Ma) de cada intervalo — ICS 2023. (hasta_Ma, era, periodo, época)
ICS = [
    (0.0117, "Cenozoico", "Cuaternario", "Holoceno"),
    (2.58, "Cenozoico", "Cuaternario", "Pleistoceno"),
    (5.333, "Cenozoico", "Neógeno", "Plioceno"),
    (23.03, "Cenozoico", "Neógeno", "Mioceno"),
    (33.9, "Cenozoico", "Paleógeno", "Oligoceno"),
    (56.0, "Cenozoico", "Paleógeno", "Eoceno"),
    (66.0, "Cenozoico", "Paleógeno", "Paleoceno"),
    (100.5, "Mesozoico", "Cretácico", "Cretácico Superior"),
    (145.0, "Mesozoico", "Cretácico", "Cretácico Inferior"),
    (161.5, "Mesozoico", "Jurásico", "Jurásico Superior"),
    (174.7, "Mesozoico", "Jurásico", "Jurásico Medio"),
    (201.4, "Mesozoico", "Jurásico", "Jurásico Inferior"),
    (237.0, "Mesozoico", "Triásico", "Triásico Superior"),
    (247.2, "Mesozoico", "Triásico", "Triásico Medio"),
    (251.9, "Mesozoico", "Triásico", "Triásico Inferior"),
    (298.9, "Paleozoico", "Pérmico", "Pérmico"),
    (358.9, "Paleozoico", "Carbonífero", "Carbonífero"),
    (419.2, "Paleozoico", "Devónico", "Devónico"),
    (443.8, "Paleozoico", "Silúrico", "Silúrico"),
    (485.4, "Paleozoico", "Ordovícico", "Ordovícico"),
    (538.8, "Paleozoico", "Cámbrico", "Cámbrico"),
]


def clasificar_edad(ma):
    """edad en Ma -> (era, periodo, época). El límite inferior pertenece al intervalo más joven."""
    if ma is None or (isinstance(ma, float) and math.isnan(ma)) or ma < 0:
        return (None, None, None)
    for hasta, era, per, ep in ICS:
        if ma < hasta:
            return (era, per, ep)
    return ("Precámbrico", "Precámbrico", "Precámbrico")


def edad_a_ma(valor, unidad, metodo=None):
    """(edad en Ma | None, factor usado, inferida). `unidad` es el texto del dominio ('Ma ± 2σ', 'a C14 AP'...)."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return (None, None, False)
    u = (unidad or "").strip().lower()
    if u.startswith("ga"):
        f, inf = 1000.0, False
    elif u.startswith("ka"):
        f, inf = 1e-3, False
    elif u.startswith("ma"):
        f, inf = 1.0, False
    elif u and ("ap" in u or "c14" in u or u.startswith("a ") or u == "a"):
        f, inf = 1e-6, False
    elif metodo == "14C" or float(valor) > 4600:  # sin unidad: >4.600 «Ma» es más viejo que la Tierra -> son años
        f, inf = 1e-6, True
    else:
        f, inf = 1.0, True
    return (float(valor) * f, f, inf)


_METODOS = [
    (r"u\s*-?\s*pb|uranio|urano|u-th-pb|shrimp|la-icp", "U-Pb"),
    (r"ar\s*-?\s*ar|arg[oó]n\s*-\s*arg[oó]n|40\s*ar|39\s*ar|arg[oó]n\s*40", "Ar-Ar"),
    (r"k\s*-?\s*ar|potasio", "K-Ar"),
    (r"14c|c14|carbono|radiocarbon", "14C"),
    (r"traza|fisi[oó]n|fission|\baft\b|\bzft\b", "Trazas de fisión"),
    (r"\(?u-?th\)?/he|u-th|helio", "(U-Th)/He"),
    (r"sm\s*-?\s*nd", "Sm-Nd"),
    (r"rb\s*-?\s*sr", "Rb-Sr"),
    (r"re\s*-?\s*os", "Re-Os"),
    (r"be\s*-?\s*10|10be", "Be10"),
    (r"al\s*-?\s*26|26al", "Al26"),
    (r"ne\s*-?\s*21|21ne", "Ne21"),
    (r"pb/alpha|alpha|pb-alpha", "Pb/Alpha"),
]


def normalizar_metodo(texto):
    t = (texto or "").strip()
    if not t or t.lower() in ("none", "nan", "null", "<null>"):
        return "Sin método"
    tl = t.lower()
    for pat, nombre in _METODOS:
        if re.search(pat, tl):
            return nombre
    return t


# ── Dominios Esri (tablas de sistema de la GDB) ────────────────────────────

def parsear_dominios(items_defs):
    """items_defs: iterable de textos XML (Definition) de dominios de valores codificados.
    Devuelve {nombre_dominio: {codigo: texto}}."""
    out = {}
    for xml in items_defs:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            continue
        nombre = root.findtext("DomainName")
        if not nombre:
            continue
        out[nombre] = {cv.findtext("Code"): cv.findtext("Name") for cv in root.iter("CodedValue")
                       if cv.findtext("Code") is not None}
    return out


def campos_con_dominio(definition_xml):
    """XML de la definición de una clase de entidad -> {campo: nombre_dominio}."""
    try:
        root = ET.fromstring(definition_xml)
    except ET.ParseError:
        return {}
    res = {}
    for f in root.iter("GPFieldInfoEx"):
        dn = f.findtext("DomainName")
        if dn:
            res[f.findtext("Name")] = dn
    return res


_CODIGO = re.compile(r"^[A-Za-z]+(?:[-_][A-Za-z0-9]+)*-\d+$")


def codigos_unicos(dominios):
    """Respaldo para campos sin dominio asignado: código -> texto, solo si el código tiene un único
    significado dentro de la GDB y no es un número suelto ('0', '1' significan cosas distintas en cada dominio)."""
    nombres = {}
    for dom in dominios.values():
        for c, n in dom.items():
            if c and _CODIGO.match(c):
                nombres.setdefault(c, set()).add(n)
    return {c: next(iter(ns)) for c, ns in nombres.items() if len(ns) == 1}


def resolver(valor, dominio, respaldo=None):
    """Traduce un código (o lista 'a,b' de códigos) con el dominio del campo; si el campo no tiene dominio
    o el código no está, prueba `respaldo` (ver codigos_unicos). Sin nada que traducir devuelve el valor."""
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    s = str(valor).strip()
    if dominio:
        if s in dominio:
            return dominio[s]
        partes = [p.strip() for p in re.split(r"[;,]", s) if p.strip()]
        if len(partes) > 1 and all(p in dominio for p in partes):
            return "; ".join(dominio[p] for p in partes)
    if respaldo:
        if s in respaldo:
            return respaldo[s]
        partes = [p.strip() for p in re.split(r"[;,]", s) if p.strip()]
        if len(partes) > 1 and all(p in respaldo for p in partes):
            return "; ".join(respaldo[p] for p in partes)
    return valor


# ── Codificación columnar ──────────────────────────────────────────────────

def columna(valores):
    """Lista de valores -> columna compacta. Texto: {'d': diccionario, 'v': índices (-1 = nulo)}; números: lista."""
    if all(v is None or isinstance(v, (int, float)) for v in valores):
        return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else v for v in valores]
    dic, idx, out = {}, [], []
    for v in valores:
        if v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() == "":
            out.append(-1)
            continue
        s = str(v).strip()
        if s not in dic:
            dic[s] = len(dic)
            idx.append(s)
        out.append(dic[s])
    return {"d": idx, "v": out}


def decodificar(col):
    if isinstance(col, dict):
        d = col["d"]
        return [None if i < 0 else d[i] for i in col["v"]]
    return list(col)


_EPOCAS_TXT = [("holoceno", "Cuaternario", "Holoceno"), ("pleistoceno", "Cuaternario", "Pleistoceno"),
               ("plioceno", "Neógeno", "Plioceno"), ("mioceno", "Neógeno", "Mioceno"),
               ("oligoceno", "Paleógeno", "Oligoceno"), ("eoceno", "Paleógeno", "Eoceno"),
               ("paleoceno", "Paleógeno", "Paleoceno")]
_PERIODOS_TXT = ["cuaternario", "neógeno", "paleógeno", "cretácico", "jurásico", "triásico", "pérmico",
                 "carbonífero", "devónico", "silúrico", "ordovícico", "cámbrico"]


def periodo_epoca_de_texto(*textos):
    """Busca época/periodo en textos de dominio ('Serravalliano (Mioceno Medio alto)') -> (periodo, época) o (None, None).
    La época se prueba antes que el periodo; 'Paleoceno' no confunde con 'Eoceno' porque se mira por palabra."""
    txt = " ".join(t for t in textos if t).lower()
    txt = txt.replace("cretacico", "cretácico").replace("jurasico", "jurásico").replace("triasico", "triásico")              .replace("permico", "pérmico").replace("carbonifero", "carbonífero").replace("devonico", "devónico")              .replace("siluric", "silúric").replace("ordovicic", "ordovícic").replace("cambric", "cámbric")              .replace("neogeno", "neógeno").replace("paleogeno", "paleógeno")
    palabras = set(re.findall(r"[a-záéíóúñ]+", txt))
    for clave, per, ep in _EPOCAS_TXT:
        if clave in palabras:
            return (per, ep)
    for p in _PERIODOS_TXT:
        if p in palabras:
            return (p.capitalize(), None)
    return (None, None)


# ── Normalización de textos para los filtros ───────────────────────────────

import html as _html
import unicodedata as _ud
from collections import Counter as _Counter

REGION_CANON = [   # (fragmento sin tildes y en minúsculas, nombre corto) — el primero que calce gana
    ("arica", "Arica y Parinacota"), ("tarapac", "Tarapacá"), ("antofagasta", "Antofagasta"), ("atacama", "Atacama"),
    ("coquimbo", "Coquimbo"), ("valpara", "Valparaíso"), ("metropolitana", "Metropolitana"), ("libertador", "O'Higgins"),
    ("higgins", "O'Higgins"), ("maule", "Maule"), ("nuble", "Ñuble"), ("biobio", "Biobío"), ("bobio", "Biobío"),
    ("araucan", "La Araucanía"), ("rios", "Los Ríos"), ("lagos", "Los Lagos"), ("aisen", "Aysén"), ("aysen", "Aysén"),
    ("magallanes", "Magallanes"),
]
FRONTERA = "Área fronteriza Chile-Argentina"
ESTADO_CANON = {
    "paralizado": "Paralizado", "paralizada": "Paralizado", "paralizado (abandonado)": "Paralizado",
    "paralizado temporalmente": "Paralizado temporalmente", "inactiva": "Inactivo", "inactivo": "Inactivo",
    "en explotacion": "En explotación", "explotacion": "En explotación", "en produccion": "En explotación",
    "activa": "En explotación", "activo": "En explotación", "explotacion intermitente": "Explotación intermitente",
    "explotacion artesanal": "Explotación artesanal", "al pirquen": "Al pirquén",
    "exploracion": "Exploración", "en exploracion": "Exploración", "prospecto": "Prospecto",
    "agotada": "Agotado", "agotado": "Agotado", "abandonada": "Abandonado", "abandonado": "Abandonado",
    "sin informacion": "Sin información", "desarrollo": "En desarrollo", "en desarrollo": "En desarrollo",
    "sin desarrollo": "Sin desarrollo", "produccion detenida": "Producción detenida",
}


def _sin_tildes(s):
    return "".join(c for c in _ud.normalize("NFD", s) if _ud.category(c) != "Mn")


def _llave(s):
    return "".join(c for c in _sin_tildes(s).lower() if c.isalnum()).replace("zircon", "circon")


def _llave_sin_letras_raras(s):
    """Clave que ignora las letras acentuadas Y los huecos que dejó una letra perdida («Anf bola», «org nico»)."""
    return "".join(c for c in s.lower() if c.isascii() and c.isalnum())


def canonicalizar(valores):
    """Lista de textos -> {texto: forma canónica}. Une mayúsculas/minúsculas, tildes faltantes y letras perdidas
    por codificación; la forma elegida es la acentuada más frecuente y siempre empieza con mayúscula."""
    cnt = _Counter(v for v in valores if v)
    padre = {v: v for v in cnt}

    def raiz(v):
        while padre[v] != v:
            padre[v] = padre[padre[v]]
            v = padre[v]
        return v
    for fn in (_llave, _llave_sin_letras_raras):
        vistos = {}
        for v in cnt:
            k = fn(v)
            if not k:
                continue
            if k in vistos:
                padre[raiz(v)] = raiz(vistos[k])
            else:
                vistos[k] = v
    grupos = {}
    for v in cnt:
        grupos.setdefault(raiz(v), []).append(v)
    out = {}
    for g in grupos.values():
        def puntaje(v):
            return (any(not c.isascii() and c != "�" for c in v), "�" not in v and "  " not in v, cnt[v])
        mejor = max(g, key=puntaje)
        mejor = mejor[:1].upper() + mejor[1:]
        for v in g:
            out[v] = mejor
    return out


def normalizar_estado(v):
    if not v:
        return None
    s = _html.unescape(str(v)).strip()
    if any(c.isdigit() for c in s):                 # «20% Mn», «700 g/t Ag»: no son estados
        return None
    k = _sin_tildes(s).lower()
    if k in ESTADO_CANON:
        return ESTADO_CANON[k]
    partes = [ESTADO_CANON.get(p.strip(), None) for p in k.replace(",", "/").split("/")]
    if partes and all(partes):                      # «Paralizado / Exploración» -> primera forma
        return partes[0]
    return s[:1].upper() + s[1:]


def normalizar_region(v):
    """Región(es) con entidades HTML deshechas y nombre corto; varias regiones separadas por «|»."""
    if not v:
        return None
    s = _html.unescape(str(v)).strip()
    if "fronteriz" in _sin_tildes(s).lower():
        return FRONTERA
    # separar solo en guiones que unen regiones (todo guion entre nombres de región); los nombres cortos no llevan guion
    partes = []
    for p in s.replace(" y la ", "-").split("-"):
        k = _sin_tildes(p).lower().strip()
        for frag, nombre in REGION_CANON:
            if frag in k:
                if nombre not in partes:
                    partes.append(nombre)
                break
    return "|".join(partes) if partes else s


ERA_PERIODO = {ep: (era, per) for _, era, per, ep in ICS}
ERA_PERIODO["Precámbrico"] = ("Precámbrico", "Precámbrico")
