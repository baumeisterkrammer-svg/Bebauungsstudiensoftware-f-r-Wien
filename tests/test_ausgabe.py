import ezdxf
import ifcopenshell

from bebauungsstudie import Bauplatz, erstelle_studie
from bebauungsstudie.ausgabe.paket import exportiere_alles
from bebauungsstudie.modell import erzeuge_modell
from bebauungsstudie.regeln.bauklassen import Bauklasse


def _studie():
    bp = Bauplatz([(0, 0), (40, 0), (40, 50), (0, 50)], {0}, Bauklasse.III, "o",
                  fluchtlinienabstand=12.0)
    return erstelle_studie(bp)


def test_modell_geschosse_passen_zur_bgf():
    s = _studie()
    mm = erzeuge_modell(s)
    summe = sum(g.flaeche.area for g in mm.geschosse)
    assert abs(summe - s.werte["BGF m²"].wert) < 1.0
    assert mm.geschosse[0].ok_fussboden == 0


def test_alle_ausgaben(tmp_path):
    s = _studie()
    dateien = {p.name for p in exportiere_alles(s, tmp_path)}
    assert {"plaene.pdf", "modell.ifc", "plaene.dxf", "bericht.txt",
            "schnitt.png"} <= dateien

    ifc = ifcopenshell.open(str(tmp_path / "modell.ifc"))
    assert len(ifc.by_type("IfcBuildingStorey")) == len(erzeuge_modell(s).geschosse)
    assert ifc.by_type("IfcWall")

    dxf = ezdxf.readfile(tmp_path / "plaene.dxf")
    assert "GESCHOSS" in dxf.layers
    assert len(dxf.modelspace().query("LWPOLYLINE")) > 5


def test_ausgaben_mit_umgebung(tmp_path):
    import numpy as np
    from shapely.geometry import box

    from bebauungsstudie.daten.kontext import Baukoerper, Kontext

    s = _studie()
    yy, xx = np.mgrid[0:200, 0:200]
    bild = np.stack([xx % 256, yy % 256, np.full_like(xx, 120)], axis=-1).astype(np.uint8)
    s.kontext = Kontext(
        bestand=[Baukoerper(box(-15, 0, -1, 14), 15.0), Baukoerper(box(41, 5, 55, 30), 9.5),
                 Baukoerper(box(5, 20, 15, 30), 6.0, am_bauplatz=True)],
        luftbild=bild, luftbild_ausdehnung=(-30.0, 70.0, -30.0, 80.0))
    dateien = {p.name for p in exportiere_alles(s, tmp_path)}
    assert {"umgebung.png", "axonometrie.png"} <= dateien

    ifc = ifcopenshell.open(str(tmp_path / "modell.ifc"))
    assert len(ifc.by_type("IfcBuildingElementProxy")) == 2

    dxf = ezdxf.readfile(tmp_path / "plaene.dxf")
    assert len(dxf.modelspace().query('LWPOLYLINE[layer=="BESTAND"]')) == 2
