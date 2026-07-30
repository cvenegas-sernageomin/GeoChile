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
