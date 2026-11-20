import pytest

from bebauungsstudie import Annahmen, Bauplatz, erstelle_studie
from bebauungsstudie.regeln.bauklassen import Bauklasse

# 40 m breit an der Straße (Kante 0), 50 m tief
RECHTECK = [(0, 0), (40, 0), (40, 50), (0, 50)]


def test_offene_bauweise_bk_ii():
    bp = Bauplatz(RECHTECK, {0}, Bauklasse.II, "o", fluchtlinienabstand=20.0)
    s = erstelle_studie(bp, Annahmen(trakttiefe=12.0))
    # Breite 40 - 2*6 = 28, Tiefe 50 - 5 (Vorgarten) - 6 = 39
    assert s.werte["Bebaute Fläche m²"].wert == pytest.approx(28 * 39)
    assert s.werte["Gebäudehöhe m"].wert == 12.0
    assert s.werte["Vollgeschoße"].wert == 4
    assert s.werte["BGF m²"].wert > 28 * 39 * 4
    assert "Vorabschätzung" in s.bericht()


def test_geschlossene_bauweise_mit_bebaubarer_flaeche():
    bp = Bauplatz(
        RECHTECK, {0}, Bauklasse.IV, "g",
        fluchtlinienabstand=14.0, vorgarten=False,
        bebaubare_flaeche_max_anteil=0.5,
    )
    s = erstelle_studie(bp)
    assert s.werte["Bebaute Fläche m²"].wert == pytest.approx(1000)
    assert s.werte["Gebäudehöhe m"].wert == 17.0
    assert s.werte["Vollgeschoße"].wert == 5
    assert any("Baufluchtlinie" in h for h in s.hinweise)


def test_kein_platz_bei_zu_kleinem_bauplatz():
    bp = Bauplatz([(0, 0), (20, 0), (20, 20), (0, 20)], {0}, Bauklasse.III, "o")
    s = erstelle_studie(bp)
    assert s.werte["Bebaute Fläche m²"].wert == 0
    assert "BGF m²" not in s.werte


def test_geschlossene_bauweise_dachgeschoss_von_nachbar_zu_nachbar():
    from bebauungsstudie.regeln.bauklassen import Bauklasse
    from bebauungsstudie.studie import dachgeschoss_grundriss, feuermauern
    # 8 m breit an der Straße, 14 m tief, Baulinie an der Straße
    bp = Bauplatz(umriss=[(0, 0), (8, 0), (8, 14), (0, 14)], strassenkanten={0},
                  bauklasse=Bauklasse.II, bauweise="g", vorgarten=False)
    assert len(feuermauern(bp)) == 2
    s = erstelle_studie(bp)
    dg = dachgeschoss_grundriss(bp, s.grundriss, 2.0)
    minx, miny, maxx, maxy = dg.bounds
    assert abs(minx - 0) < 1e-6 and abs(maxx - 8) < 1e-6  # volle Breite
    assert abs(miny - 2) < 1e-6 and abs(maxy - 12) < 1e-6  # Straße und Hof eingerückt


def test_gekuppelte_bauweise_baut_an_eine_seitengrenze():
    from bebauungsstudie.studie import feuermauern
    from bebauungsstudie.regeln.bauklassen import Bauklasse as BK
    umriss = [(0, 0), (18, 0), (18, 30), (0, 30)]
    offen = erstelle_studie(Bauplatz(umriss, {0}, BK.I, "ogk", fluchtlinienabstand=12.0))
    gek = erstelle_studie(Bauplatz(umriss, {0}, BK.I, "ogk", fluchtlinienabstand=12.0, gekuppelt=True))
    b_off = offen.grundriss.bounds
    b_gek = gek.grundriss.bounds
    assert abs((b_gek[2] - b_gek[0]) - (b_off[2] - b_off[0]) - (b_off[0] - 0)) < 0.01
    assert b_gek[0] == 0 or b_gek[2] == 18
    assert len(feuermauern(gek.bauplatz)) == 1
    assert gek.werte["BGF m²"].wert > offen.werte["BGF m²"].wert
    assert any("Gekuppelte Bauweise" in h for h in gek.hinweise)
