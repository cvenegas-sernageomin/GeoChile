"""Litología inferida del texto (nombre + definición) de una unidad geológica.

La GDB de SERNAGEOMIN NO trae un campo de litología en `GB_UNIDAD_GEO_P`: está escrita en el nombre y la definición
(«Granodioritas…», «Andesitas…», «Depósitos aluviales…»). Este módulo la reconoce con un diccionario controlado de raíces de
nombres de roca y la agrupa en categorías. Es una INFERENCIA: la interfaz la rotula como tal.
"""
import re
import unicodedata

SIN_LITO = "Sin litología reconocida"

# (categoría, [(roca mostrada, raíz sin tildes en minúsculas)…]) — el orden dentro de una categoría es el de prioridad
DICC = [
    ("Plutónicas", [("Granodiorita", "granodiorit"), ("Tonalita", "tonalit"), ("Monzogranito", "monzogranit"),
                    ("Monzodiorita", "monzodiorit"), ("Monzonita", "monzonit"), ("Sienita", "sienit"), ("Diorita", "diorit"),
                    ("Gabro", "gabro"), ("Granito", "granit"), ("Leucogranito", "leucogranit"), ("Peridotita", "peridotit"),
                    ("Ultramáfica", "ultramafic")]),
    ("Subvolcánicas", [("Pórfido", "porfid"), ("Dique", "dique"), ("Hipabisal", "hipabisal")]),
    ("Volcánicas", [("Ignimbrita", "ignimbrit"), ("Andesita", "andesit"), ("Dacita", "dacit"), ("Riolita", "riolit"),
                    ("Basalto", "basalt"), ("Traquita", "traquit"), ("Toba", "toba"), ("Lava", "lava"), ("Piroclástica", "piroclast"),
                    ("Ceniza", "ceniza"), ("Escoria", "escoria")]),
    ("Sedimentarias clásticas", [("Conglomerado", "conglomerad"), ("Brecha", "brecha"), ("Arenisca", "arenisca"), ("Limolita", "limolit"),
                                 ("Lutita", "lutit"), ("Fangolita", "fangolit"), ("Grauvaca", "grauvac"), ("Arenita", "arenita"),
                                 ("Yeso", "yeso"), ("Evaporita", "evaporit"), ("Diatomita", "diatomit")]),
    ("Carbonáticas", [("Caliza", "caliza"), ("Calcarenita", "calcarenit"), ("Dolomita", "dolomit"), ("Calcárea", "calcare")]),
    ("Metamórficas", [("Esquisto", "esquisto"), ("Gneis", "gneis"), ("Filita", "filita"), ("Pizarra", "pizarra"), ("Cuarcita", "cuarcit"),
                      ("Mármol", "marmol"), ("Anfibolita", "anfibolit"), ("Migmatita", "migmatit"), ("Metarenisca", "metarenisca"),
                      ("Metapelita", "metapelit"), ("Milonita", "milonit"), ("Metamórfica", "metamorf")]),
    ("Depósitos no consolidados", [("Depósitos", "deposito"), ("Gravas", "gravas"), ("Arenas", "arenas"), ("Ripios", "ripios"),
                                   ("Limos", "limos"), ("Morrena", "morrena"), ("Dunas", "duna"), ("Aluvial", "aluvial"),
                                   ("Coluvial", "coluvial"), ("Glaciar", "glaciar"), ("Lahar", "lahar"), ("Sedimentos", "sedimentos")]),
]


def _sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def _patron(raiz):
    return re.compile(r"(?<![a-z])" + re.escape(raiz))


_PAT = [(cat, [(roca, _patron(raiz)) for roca, raiz in rocas]) for cat, rocas in DICC]


AMBIENTE_A_CAT = {"plutonic": "Plutónicas", "intrusiv": "Plutónicas", "subvolcanic": "Subvolcánicas", "volcanic": "Volcánicas",
                   "sedimentar": "Sedimentarias clásticas", "metamorf": "Metamórficas"}


def inferir(nombre, definicion=None, nota=None, ambiente=None):
    """-> (categoría, [rocas]) con hasta 3 rocas por orden de aparición en el nombre y la definición.
    El NOMBRE manda: «Granodioritas de X» no se vuelve volcánica porque la definición mencione una toba."""
    for texto in (nombre, " ".join(t for t in (definicion, nota) if t)):
        t = _sin_tildes(texto or "")
        if not t.strip():
            continue
        hallazgos = []   # (posición, categoría, roca)
        for cat, rocas in _PAT:
            for roca, pat in rocas:
                m = pat.search(t)
                if m:
                    hallazgos.append((m.start(), cat, roca))
        if hallazgos:
            hallazgos.sort()
            cat = hallazgos[0][1]
            rocas, vistas = [], set()
            for _, c, r in hallazgos:
                if r not in vistas:
                    vistas.add(r)
                    rocas.append(r)
            return cat, rocas[:3]
    a = _sin_tildes(ambiente or "")      # sin roca en el texto («Plutón Chivato»): al menos la familia que da el ambiente
    for raiz, cat in AMBIENTE_A_CAT.items():
        if raiz in a and "volcanico sedimentario" not in a:
            return cat, []
    return SIN_LITO, []
