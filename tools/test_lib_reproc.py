import numpy as np
from lib_reproc import pixel_to_geo, geo_to_pixel, detect_neatline

BOX = dict(n=-35.0, s=-36.0, e=-71.0, w=-72.0, rot=0.5, lonc=-71.5, latc=-35.5)
W, H = 1000, 1000

def test_roundtrip_pixel_geo():
    for px, py in [(0, 0), (999, 0), (500, 500), (999, 999), (123, 456)]:
        lon, lat = pixel_to_geo(px, py, BOX, W, H)
        rx, ry = geo_to_pixel(lon, lat, BOX, W, H)
        assert abs(rx - px) < 1e-3, (px, py, rx)
        assert abs(ry - py) < 1e-3, (px, py, ry)

def test_centro_es_centro():
    lon, lat = pixel_to_geo((W - 1) / 2, (H - 1) / 2, BOX, W, H)
    assert abs(lon - BOX["lonc"]) < 1e-6
    assert abs(lat - BOX["latc"]) < 1e-6

def test_sin_rotacion_esquinas():
    box0 = dict(BOX, rot=0.0)
    lon, lat = pixel_to_geo(0, 0, box0, W, H)  # esquina superior-izq
    assert abs(lon - box0["w"]) < 1e-6
    assert abs(lat - box0["n"]) < 1e-6

def test_detect_neatline_recuadro():
    img = np.full((200, 300, 3), 255, np.uint8)
    img[15:186, 20:21] = 0; img[15:186, 279:280] = 0
    img[15:16, 20:280] = 0; img[185:186, 20:280] = 0
    x0, y0, x1, y1 = detect_neatline(img)
    assert abs(x0 - 20) <= 3 and abs(x1 - 279) <= 3
    assert abs(y0 - 15) <= 3 and abs(y1 - 185) <= 3


def test_detect_neatline_ignora_columnas_internas():
    # marco del mapa + tablas internas casi tan altas como el marco (caso F19:
    # la columna cronoestratigrafica). Deben ganar los EXTREMOS, no el interior.
    img = np.full((400, 600, 3), 255, np.uint8)
    img[30:371, 40:41] = 0; img[30:371, 559:560] = 0      # marco vertical
    img[30:31, 40:560] = 0; img[370:371, 40:560] = 0       # marco horizontal
    img[30:371, 300:301] = 0; img[30:371, 340:341] = 0     # columnas internas
    x0, y0, x1, y1 = detect_neatline(img)
    assert abs(x0 - 40) <= 3 and abs(x1 - 559) <= 3        # NO 300/340
    assert abs(y0 - 30) <= 3 and abs(y1 - 370) <= 3


def test_detect_neatline_rechaza_sliver():
    # rect implausiblemente delgado -> ValueError (guarda anti-sliver)
    import pytest
    img = np.full((400, 600, 3), 255, np.uint8)
    img[10:391, 295:296] = 0; img[10:391, 305:306] = 0     # dos verticales muy juntas
    img[10:11, 295:306] = 0; img[390:391, 295:306] = 0
    with pytest.raises(ValueError):
        detect_neatline(img)
