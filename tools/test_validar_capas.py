import json, subprocess, sys, tempfile, os

PY = sys.executable
HERE = os.path.dirname(__file__)

def run(capas):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(capas, f)
        path = f.name
    r = subprocess.run([PY, os.path.join(HERE, "validar_capas.py"), path],
                       capture_output=True, text=True)
    os.unlink(path)
    return r.returncode, r.stdout + r.stderr

def test_valida_entrada_correcta():
    ok = [{"id": "geo_x", "categoria": "geologia", "titulo": "T",
           "bounds": {"n": -35.0, "s": -36.0, "e": -71.0, "w": -72.0},
           "overlay": "overlays/geo_x.webp", "leyenda": "leyendas/geo_x.jpg",
           "opacidad": 1.0, "recortado": True}]
    code, out = run(ok)
    assert code == 0, out

def test_rechaza_bounds_invalidos():
    bad = [{"id": "geo_x", "categoria": "geologia", "titulo": "T",
            "bounds": {"n": -36.0, "s": -35.0, "e": -71.0, "w": -72.0},
            "overlay": "overlays/geo_x.webp", "leyenda": None,
            "opacidad": 1.0, "recortado": False}]
    code, out = run(bad)
    assert code != 0
    assert "bounds" in out.lower()

def test_rechaza_categoria_desconocida():
    bad = [{"id": "x", "categoria": "otra", "titulo": "T",
            "bounds": {"n": -35.0, "s": -36.0, "e": -71.0, "w": -72.0},
            "overlay": "overlays/x.webp", "leyenda": None,
            "opacidad": 1.0, "recortado": False}]
    code, out = run(bad)
    assert code != 0
    assert "categoria" in out.lower()
