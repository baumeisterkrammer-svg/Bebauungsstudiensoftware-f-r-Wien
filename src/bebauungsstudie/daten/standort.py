"""Standortdaten zu einer Wiener Adresse aus den offenen Daten der Stadt Wien.

Automatisch verfügbar (OGD, CC BY 4.0): Widmung und Bauklasse (generalisierte
Flächenwidmung), Schutz- und Wohnzonen, Bausperren, Stellplatzzone und die
Bestandsgebäude. Das Grundstück kommt aus der BEV-Katastralmappe (kataster.py).
Bauweise, Fluchtlinien und Besondere Bestimmungen gibt es nur als Planbild.
Diese Werte kommen als Eingabe oder Annahme und werden so gekennzeichnet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from shapely.geometry import Point, shape

from ..regeln.bauklassen import Bauklasse
from . import wien

BAUKLASSE_ZIFFER = {"1": Bauklasse.I, "2": Bauklasse.II, "3": Bauklasse.III,
                    "4": Bauklasse.IV, "5": Bauklasse.V, "6": Bauklasse.VI}
BAULAND = {"WO", "GB", "GS", "IG", "WG", "BL"}


@dataclass
class Bestandsgebaeude:
    grundflaeche_m2: float
    hoehe_m: float | None


@dataclass
class Standort:
    adresse: str
    x: float
    y: float
    widmung: str | None = None
    widmung_text: str | None = None
    widmungsklasse: str | None = None
    bauklasse: Bauklasse | None = None
    gartensiedlung: bool = False
    schutzzone: bool = False
    wohnzone: bool = False
    bausperre: bool = False
    stellplatzzone: int | None = None
    bestand: list[Bestandsgebaeude] = field(default_factory=list)
    protokoll: list[str] = field(default_factory=list)

    @property
    def bauland(self) -> bool:
        return (self.widmungsklasse or "") in BAULAND or self.bauklasse is not None


def lies_widmung(code: str | None) -> tuple[Bauklasse | None, bool]:
    """'W1' → (Bauklasse I, False), 'GS' → (None, True), 'GB3' → (III, False)."""
    if not code:
        return None, False
    c = code.strip().upper()
    if c.startswith("GS"):
        return None, True
    m = re.search(r"([1-6])", c)
    return (BAUKLASSE_ZIFFER[m.group(1)] if m else None), False


def _am_punkt(layer: str, x: float, y: float, radius: float = 3.0) -> list[dict]:
    p = Point(x, y)
    feats = wien.features(layer, x, y, radius=radius).get("features", [])
    treffer = [f for f in feats if f.get("geometry") and shape(f["geometry"]).buffer(0.5).contains(p)]
    return treffer or feats


def ermittle_standort(adresse: str) -> Standort:
    log: list[str] = []
    treffer = wien.suche_adresse(adresse, log)
    if not treffer:
        raise LookupError(f"Adresse nicht gefunden: {adresse}")
    t = treffer[0]
    s = Standort(adresse=t.text, x=t.x, y=t.y, protokoll=log)

    def versuch(name, fn):
        try:
            fn()
        except Exception as e:
            s.protokoll.append(f"{name}: nicht abrufbar ({type(e).__name__}: {e})")

    def widmung():
        f = _am_punkt("ogdwien:GENFLWIDMUNGOGD", s.x, s.y)
        if not f:
            s.protokoll.append("Widmung: keine Fläche gefunden")
            return
        p = f[0]["properties"]
        s.widmung = p.get("WIDMUNG")
        s.widmung_text = p.get("WIDMUNG_TXT")
        s.widmungsklasse = p.get("WIDMUNGSKLASSE")
        s.bauklasse, s.gartensiedlung = lies_widmung(s.widmung)
        s.protokoll.append(f"Widmung: {s.widmung} ({s.widmung_text})")

    def zonen():
        for f in wien.features("ogdwien:GRPZONENOGD", s.x, s.y, radius=3).get("features", []):
            text = " ".join(str(v) for v in f.get("properties", {}).values()).upper()
            s.schutzzone |= "SCHUTZ" in text
            s.wohnzone |= "WOHNZONE" in text
        s.schutzzone |= bool(wien.features("ogdwien:SCHUTZZONEOGD", s.x, s.y, radius=3).get("features"))
        s.protokoll.append(f"Schutzzone: {'ja' if s.schutzzone else 'nein'}, Wohnzone: {'ja' if s.wohnzone else 'nein'}")

    def bausperre():
        for layer in ("ogdwien:BAUSPERRE82OGD", "ogdwien:BAUSPERRE86OGD"):
            s.bausperre |= bool(wien.features(layer, s.x, s.y, radius=3).get("features"))
        s.protokoll.append(f"Bausperre: {'ja' if s.bausperre else 'nein'}")

    def stellplatz():
        f = _am_punkt("ogdwien:STELLPLATZVERPFLOGD", s.x, s.y)
        if f:
            s.stellplatzzone = f[0]["properties"].get("ZONE")
        s.protokoll.append(f"Stellplatzzone: {s.stellplatzzone}")

    def bestand():
        for f in wien.features("ogdwien:FMZKBKMOGD", s.x, s.y, radius=20).get("features", []):
            p = f.get("properties", {})
            o, t_ = p.get("O_KOTE"), p.get("T_KOTE") or p.get("HOEHE_DGM")
            h = round(o - t_, 1) if o is not None and t_ is not None else None
            s.bestand.append(Bestandsgebaeude(round(shape(f["geometry"]).area, 1), h))
        s.protokoll.append(f"Bestand im Umkreis von 20 m: {len(s.bestand)} Gebäudeteile")

    for name, fn in (("Widmung", widmung), ("Zonen", zonen), ("Bausperre", bausperre),
                     ("Stellplatzzone", stellplatz), ("Bestand", bestand)):
        versuch(name, fn)
    return s
