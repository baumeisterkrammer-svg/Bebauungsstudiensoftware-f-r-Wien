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
