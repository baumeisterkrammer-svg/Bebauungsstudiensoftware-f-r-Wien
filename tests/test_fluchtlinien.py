import numpy as np
from shapely.geometry import Polygon

from bebauungsstudie.daten.bebauungsplan import fluchtlinien_auswerten

PX = 0.1  # m je Pixel
EXT = (-20.0, 40.0, -30.0, 50.0)  # xmin, xmax, ymin, ymax


def _bild():
    w, h = int((EXT[1] - EXT[0]) / PX), int((EXT[3] - EXT[2]) / PX)
    b = np.zeros((h, w, 4), np.uint8)

    def px(x, y):
        return int((x - EXT[0]) / PX), int((EXT[3] - y) / PX)

    def linie(p, q, strich=None):
        n = int(np.hypot(q[0] - p[0], q[1] - p[1]) / (PX / 3))
        for t in np.linspace(0, 1, n):
            x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
            if strich and (t * n * PX / 3) % sum(strich) > strich[0]:
                continue
            c, r = px(x, y)
            b[max(r - 2, 0):r + 2, max(c - 2, 0):c + 2] = (255, 0, 0, 255)

    linie((-20, 0), (40, 0))      # Baulinie an der Grundstücksgrenze
    linie((-20, -12), (40, -12))  # gegenüberliegende Baulinie, 12 m
    gestrichelt = (2.0, 1.5)      # Baufluchtlinien: 2 m Strich, 1,5 m Lücke
    for p, q in [((3, 5), (17, 5)), ((17, 5), (17, 20)), ((17, 20), (3, 20)), ((3, 20), (3, 5))]:
        linie(p, q, gestrichelt)
    return b


def test_fluchtlinien_und_strassenbreite():
    umriss = [(0, 0), (20, 0), (20, 30), (0, 30)]
    erg = fluchtlinien_auswerten(_bild(), EXT, umriss, {0})
    assert erg.flaeche is not None, erg.protokoll
    innen = Polygon(erg.flaeche)
    assert abs(innen.area - 14 * 15) < 25, erg.protokoll
    assert innen.contains(Polygon([(4, 6), (16, 6), (16, 19), (4, 19)]))
    assert erg.strassenbreiten == {0: 12.0}, erg.protokoll


def test_planschrift_drehung_zurueck():
    from PIL import Image
    from bebauungsstudie.daten.planschrift import zurueck
    b = np.full((100, 160), 255, np.uint8)
    b[20:24, 120:124] = 0  # Marke bei (x=121.5, y=21.5)
    for winkel in (0, 30, 90, 135):
        g = Image.fromarray(b).rotate(winkel, expand=True, fillcolor=255)
        ys, xs = np.nonzero(np.asarray(g) < 128)
        x, y = zurueck(xs.mean(), ys.mean(), winkel, g.size, (160, 100))
        assert abs(x - 121.5) < 1.5 and abs(y - 21.5) < 1.5, (winkel, x, y)


def test_bauweise_aus_woertern():
    from bebauungsstudie.daten.planschrift import Wort, bauweise_aus_woertern
    w = [Wort("W", 5, 5, 90), Wort("I", 6, 5, 90), Wort("o", 8, 5, 85), Wort("12.00", 0, -6, 90),
         Wort("WIo", 9, 5, 70), Wort("gk", 200, 200, 90)]
    bw, text = bauweise_aus_woertern(w, 0, 0)
    assert bw == "o", text
