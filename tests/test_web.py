"""Ablauf der Kunden-Homepage im Demo-Modus (ohne Zahlung, mit Beispielergebnis)."""

import importlib
import time
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

ERGEBNIS = """# Bebauungsstudie Test
- Widmung: W1 – Wohngebiet Bauklasse 1
```
BGF m²: 622.6  [BO für Wien § 75 Abs. 2]  Herleitung
Wohnungen: 7  [Annahme Wohnungsgröße]  467 m² / 65 m²

Hinweise:
- Testhinweis.
```
"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "ergebnis.md").write_text(ERGEBNIS, encoding="utf-8")
    for n in ("plaene.pdf", "modell.ifc", "plaene.dxf", "bericht.txt"):
        (demo / n).write_text("x")
    monkeypatch.setenv("STUDIE_DEMO_ORDNER", str(demo))
    monkeypatch.setenv("STUDIE_DATEN", str(tmp_path / "auftraege"))
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    import web.app as m
    importlib.reload(m)
    return TestClient(m.app)


def _bestellen(client, paket):
    r = client.post("/bestellen", data={"paket": paket, "adresse": "Olbrichgasse 9, 1120 Wien",
                                        "email": "a@b.at", "agb": "ja"}, follow_redirects=False)
    assert r.status_code == 303
    url = r.headers["location"]
    for _ in range(50):
        if "Kennzahlen" in client.get(url).text:
            return url
        time.sleep(0.1)
    raise AssertionError("Studie nicht fertig")


def test_startseite_zeigt_pakete(client):
    t = client.get("/").text
    assert "Basis" in t and "Standard" in t and "Profi" in t


def test_eingaben_werden_geprueft(client):
    r = client.post("/bestellen", data={"paket": "basis", "adresse": "Hauptstraße 1, Graz",
                                        "email": "a@b.at", "agb": "ja"})
    assert r.status_code == 400 and "Wiener Adresse" in r.text


def test_paket_bestimmt_downloads(client):
    url = _bestellen(client, "standard")
    t = client.get(url).text
    assert "622.6" in t and "plaene.pdf" in t and "modell.ifc" not in t
    assert client.get(url + "/datei/modell.ifc").status_code == 404
    url = _bestellen(client, "profi")
    assert client.get(url + "/datei/modell.ifc").status_code == 200
    assert client.get(url + "/alles.zip").status_code == 200
