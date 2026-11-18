import pytest

from bebauungsstudie.regeln import abstaende, stellplaetze, umriss
from bebauungsstudie.regeln.bauklassen import Bauklasse


def test_abstaende_offene_bauweise():
    werte = {bk: abstaende.abstand_nachbargrenze(bk).wert for bk in Bauklasse}
    assert werte == {
        Bauklasse.I: 6, Bauklasse.II: 6, Bauklasse.III: 12,
        Bauklasse.IV: 14, Bauklasse.V: 16, Bauklasse.VI: 20,
    }


def test_vorgarten():
    assert abstaende.vorgarten_tiefe().wert == 5.0
    assert abstaende.vorgarten_tiefe(3.0).wert == 3.0


def test_baeume_je_angefangene_200m2():
    assert abstaende.baeume(0).wert == 0
    assert abstaende.baeume(200).wert == 1
    assert abstaende.baeume(201).wert == 2


def test_dachhoehe():
    assert umriss.max_dachhoehe(Bauklasse.I, "o").wert == 4.5
    assert umriss.max_dachhoehe(Bauklasse.III, "g").wert == 7.5


def test_dachgeschosse_45_grad():
    # Trakttiefe 12 m, 45°: erstes DG ab 2,5 m lichter Höhe -> 12 - 5 = 7 m
    e = umriss.dachgeschosse(12.0, 45.0, 7.5, 3.0)
    assert e.wert[0] == pytest.approx(7.0)
    assert len(e.wert) == 1  # zweites DG wäre nur 12 - 2*5,5 = 1 m breit


@pytest.mark.parametrize(
    "wnf, prozent, erwartet",
    [(180, 100, 1), (200, 100, 2), (1000, 50, 5), (1000, 110, 11)],
)
def test_stellplaetze(wnf, prozent, erwartet):
    assert stellplaetze.pflichtstellplaetze(wnf, prozent).wert == erwartet


def test_stellplaetze_kleinhaus():
    assert stellplaetze.pflichtstellplaetze(150, kleinhaus_eine_wohnung=True).wert == 0
