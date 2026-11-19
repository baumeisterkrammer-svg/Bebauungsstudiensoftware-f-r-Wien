import pytest

from bebauungsstudie.regeln.bauklassen import (
    Bauklasse,
    hoehe_nach_strassenbreite,
    hoehenrahmen,
    zulaessige_gebaeudehoehe,
)


@pytest.mark.parametrize(
    "bk, rahmen",
    [
        (Bauklasse.I, (2.5, 9.0)),
        (Bauklasse.II, (2.5, 12.0)),
        (Bauklasse.III, (9.0, 16.0)),
        (Bauklasse.IV, (12.0, 21.0)),
        (Bauklasse.V, (16.0, 26.0)),
    ],
)
def test_hoehenrahmen(bk, rahmen):
    assert hoehenrahmen(bk).wert == rahmen


def test_bauklasse_vi_braucht_grenzmasse():
    with pytest.raises(ValueError):
        hoehenrahmen(Bauklasse.VI)
    assert hoehenrahmen(Bauklasse.VI, (32.0, 38.0)).wert == (32.0, 38.0)


@pytest.mark.parametrize(
    "bk, abstand, hoehe",
    [
        (Bauklasse.I, 8.0, 10.0),
        (Bauklasse.III, 10.0, 13.0),
        (Bauklasse.IV, 15.0, 18.0),
        (Bauklasse.IV, 16.0, 20.0),
        (Bauklasse.V, 12.0, 24.0),
    ],
)
def test_hoehe_nach_strassenbreite(bk, abstand, hoehe):
    assert hoehe_nach_strassenbreite(bk, abstand).wert == hoehe


def test_schmale_strasse_begrenzt_hoehe():
    e = zulaessige_gebaeudehoehe(Bauklasse.IV, fluchtlinienabstand=12.0)
    assert e.wert == 15.0
    assert "Straßenbreite" in e.begruendung


def test_schutzzone_ignoriert_strassenbreite():
    e = zulaessige_gebaeudehoehe(Bauklasse.IV, fluchtlinienabstand=12.0, schutzzone=True)
    assert e.wert == 21.0
    assert e.hinweise


def test_festgesetzte_hoehe_gilt_wenn_niedriger():
    assert zulaessige_gebaeudehoehe(Bauklasse.III, festgesetzte_hoehe=14.0).wert == 14.0


def test_gartensiedlung():
    assert zulaessige_gebaeudehoehe(None, gartensiedlung=True).wert == 5.5
