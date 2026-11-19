from shapely.geometry import box

from bebauungsstudie import Bauplatz, erstelle_studie
from bebauungsstudie.nachverdichtung import bestandsgeschosse, erstelle_nachverdichtung
from bebauungsstudie.regeln.bauklassen import Bauklasse


def _studie():
    # geschlossene Bauweise, 16 m breit, 30 m tief, Bauklasse III
    bp = Bauplatz([(0, 0), (16, 0), (16, 30), (0, 30)], {0}, Bauklasse.III, "g",
                  fluchtlinienabstand=15.0)
    return erstelle_studie(bp)


def test_bestandsgeschosse():
    assert bestandsgeschosse(6.5, 3.2) == 2
    assert bestandsgeschosse(9.8, 3.2) == 3
    assert bestandsgeschosse(2.5, 3.2) == 1


def test_aufstockung_zubau_differenz():
    s = _studie()
    n = s.werte["Vollgeschoße"].wert
    # zweigeschoßiges Straßenhaus, 12 m tief, über die ganze Breite
    nv = erstelle_nachverdichtung(s, [(box(0, 0, 16, 12), 6.5)])
    w = nv.werte
    assert w["Bestand BGF m² (geschätzt)"].wert == 16 * 12 * 2
    assert w["Aufstockung BGF m²"].wert > 0
    drin = box(0, 0, 16, 12).intersection(s.grundriss).area
    assert abs(w["Aufstockung BGF m²"].wert - drin * (n - 2)) < 1
    assert w["Zubau im Hof BGF m²"].wert > 0
    plus = w["Aufstockung BGF m²"].wert + w["Dachgeschoßausbau BGF m²"].wert + w["Zubau im Hof BGF m²"].wert
    assert abs(w["Zusätzliche BGF m²"].wert - plus) < 0.5
    # Bestand im Vorgarten bleibt erhalten und kommt zur Neubau-BGF dazu
    aussen = box(0, 0, 16, 12).difference(s.grundriss).area * 2
    assert w["BGF nach Nachverdichtung m²"].wert <= s.werte["BGF m²"].wert + aussen + 1


def test_ohne_bestand_kein_ergebnis():
    assert erstelle_nachverdichtung(_studie(), []) is None


def test_plan_seite(tmp_path):
    from bebauungsstudie.ausgabe.paket import exportiere_alles
    s = _studie()
    s.nachverdichtung = erstelle_nachverdichtung(s, [(box(0, 0, 16, 12), 6.5)])
    namen = {p.name for p in exportiere_alles(s, tmp_path)}
    assert "nachverdichtung.png" in namen
    assert "Nachverdichtung" in (tmp_path / "bericht.txt").read_text(encoding="utf-8")
