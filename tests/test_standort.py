"""Standortermittlung mit aufgezeichneten Antworten der Stadt Wien (Olbrichgasse 9)."""

from bebauungsstudie.daten import standort, wien
from bebauungsstudie.regeln.bauklassen import Bauklasse

X, Y = -2309.34, 336954.0


def _quadrat(cx, cy, r=10):
    return {"type": "Polygon", "coordinates": [[(cx - r, cy - r), (cx + r, cy - r),
                                                (cx + r, cy + r), (cx - r, cy + r),
                                                (cx - r, cy - r)]]}


# Aufgezeichnet am 18.11.2026 über data.wien.gv.at (gekürzt)
ANTWORTEN = {
    "ogdwien:GENFLWIDMUNGOGD": [{"geometry": _quadrat(X, Y, 50), "properties": {
        "WIDMUNGSKLASSE": "WO", "WIDMUNGSKLASSE_TXT": "Wohngebiet", "WIDMUNG": "W1",
        "WIDMUNG_TXT": "Wohngebiet Bauklasse 1"}}],
    "ogdwien:STELLPLATZVERPFLOGD": [{"geometry": _quadrat(X, Y, 500), "properties": {
        "ZONE": 2}}],
    "ogdwien:FMZKBKMOGD": [
        {"geometry": _quadrat(X, Y, 5), "properties": {"O_KOTE": 75.7, "T_KOTE": 71.416}},
        {"geometry": _quadrat(X + 12, Y, 4), "properties": {"O_KOTE": 78.2, "T_KOTE": 71.328}},
    ],
}


def _fake_features(layer, x, y, radius=30.0, max_features=200):
    return {"features": ANTWORTEN.get(layer, [])}


def _fake_adresse(adresse, protokoll=None):
    return [wien.Adresstreffer("9, Olbrichgasse, 1120 Wien", X, Y, {})]


def test_olbrichgasse(monkeypatch):
    monkeypatch.setattr(wien, "features", _fake_features)
    monkeypatch.setattr(wien, "suche_adresse", _fake_adresse)
    s = standort.ermittle_standort("Olbrichgasse 9, 1120 Wien")
    assert s.widmung == "W1"
    assert s.bauklasse is Bauklasse.I
    assert s.bauland
    assert not s.schutzzone and not s.bausperre
    assert s.stellplatzzone == 2
    assert sorted(b.hoehe_m for b in s.bestand) == [4.3, 6.9]


def test_lies_widmung():
    assert standort.lies_widmung("W1") == (Bauklasse.I, False)
    assert standort.lies_widmung("GB3") == (Bauklasse.III, False)
    assert standort.lies_widmung("GS") == (None, True)
    assert standort.lies_widmung(None) == (None, False)


def test_fehler_im_dienst_bricht_nicht_ab(monkeypatch):
    def kaputt(*a, **k):
        raise TimeoutError("zu langsam")
    monkeypatch.setattr(wien, "features", kaputt)
    monkeypatch.setattr(wien, "suche_adresse", _fake_adresse)
    s = standort.ermittle_standort("x")
    assert s.widmung is None
    assert any("nicht abrufbar" in z for z in s.protokoll)
