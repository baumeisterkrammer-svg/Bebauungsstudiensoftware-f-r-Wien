"""Bebauungsstudie für einen Bauplatz: Hüllkörper und Kennzahlen.

Version 0.1 rechnet einen einzelnen Baukörper auf einem ebenen Bauplatz.
Koordinaten in Metern in einem projizierten System (z. B. MGI / Austria
GK East, EPSG:31256).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry

from .herleitung import Ergebnis, Quelle
from .regeln import abstaende, bauklassen, stellplaetze, umriss
from .regeln.bauklassen import Bauklasse

BAUWEISEN = ("o", "gk", "ogk", "gr", "g")


@dataclass
class Bauplatz:
    """Eingangsdaten aus Kataster und Bebauungsplan."""

    umriss: list[tuple[float, float]]
    strassenkanten: set[int]
    """Indizes der Kanten an der Baulinie; Kante i läuft von Punkt i zu i+1."""
    bauklasse: Bauklasse | None
    bauweise: str
    fluchtlinienabstand: float | None = None
    festgesetzte_hoehe: float | None = None
    grenzmasse_vi: tuple[float, float] | None = None
    vorgarten: bool = True
    vorgarten_tiefe: float | None = None
    bebaubare_flaeche_max_m2: float | None = None
    bebaubare_flaeche_max_anteil: float | None = None
    schutzzone: bool = False
    gartensiedlung: bool = False
    wohngebiet: bool = True
    dachneigung: float | None = None
    stellplatzregulativ_prozent: float = 100.0

    def __post_init__(self) -> None:
        if self.bauweise not in BAUWEISEN:
            raise ValueError(f"Unbekannte Bauweise {self.bauweise!r}")

    @property
    def polygon(self) -> Polygon:
        return Polygon(self.umriss)

    def kante(self, i: int) -> LineString:
        n = len(self.umriss)
        return LineString([self.umriss[i], self.umriss[(i + 1) % n]])


@dataclass
class Annahmen:
    """Planerische Annahmen, keine Rechtsvorgaben. Vom Nutzer änderbar."""

    geschosshoehe: float = 3.0
    nutzflaechenfaktor: float = 0.75
    """Anteil Nutzfläche an der BGF."""
    wohnungsgroesse_m2: float = 65.0
    trakttiefe: float | None = None
    """Für Dachgeschoße; ohne Angabe die kürzere Seite des Grundrisses."""


@dataclass
class Studie:
    bauplatz: Bauplatz
    annahmen: Annahmen
    grundriss: BaseGeometry
    werte: dict[str, Ergebnis] = field(default_factory=dict)
    hinweise: list[str] = field(default_factory=list)

    def bericht(self) -> str:
        zeilen = ["Bebauungsstudie (Vorabschätzung, keine Rechtsauskunft)", ""]
        for name, e in self.werte.items():
            q = ", ".join(str(x) for x in e.quellen)
            zeilen.append(f"{name}: {e.wert}  [{q}]  {e.begruendung}")
        hin = list(self.hinweise)
        for e in self.werte.values():
            hin.extend(e.hinweise)
        if hin:
            zeilen += ["", "Hinweise:"] + [f"- {h}" for h in dict.fromkeys(hin)]
        return "\n".join(zeilen)


def _bebaubarer_grundriss(bp: Bauplatz, studie_hinweise: list[str]) -> BaseGeometry:
    flaeche = bp.polygon
    n = len(bp.umriss)
    vg = abstaende.vorgarten_tiefe(bp.vorgarten_tiefe).wert
    abstand = (
        abstaende.abstand_nachbargrenze(bp.bauklasse).wert
        if bp.bauklasse is not None and bp.bauweise != "g"
        else 0.0
    )
    if bp.bauweise in ("gk", "ogk", "gr"):
        studie_hinweise.append(
            f"Bauweise {bp.bauweise}: Anbau an eine Grenze ist zulässig, "
            "hier aber konservativ wie offene Bauweise gerechnet."
        )
    if bp.bauweise == "g":
        studie_hinweise.append(
            "Geschlossene Bauweise: hintere Baufluchtlinie aus dem Plandokument "
            "muss ergänzt werden."
        )
    for i in range(n):
        if i in bp.strassenkanten:
            d = vg if bp.vorgarten else 0.0
        else:
            d = abstand
        if d > 0:
            streifen = bp.kante(i).buffer(d, cap_style="square", join_style="mitre")
            flaeche = flaeche.difference(streifen)
    return flaeche


def _kuerzere_seite(geom: BaseGeometry) -> float:
    rect = geom.minimum_rotated_rectangle
    xs = list(rect.exterior.coords)
    seiten = [math.dist(xs[i], xs[i + 1]) for i in range(4)]
    return min(seiten)


def erstelle_studie(bp: Bauplatz, annahmen: Annahmen | None = None) -> Studie:
    a = annahmen or Annahmen()
    hinweise: list[str] = []
    grundriss = _bebaubarer_grundriss(bp, hinweise)
    s = Studie(bp, a, grundriss, hinweise=hinweise)
    w = s.werte

    bauplatz_m2 = bp.polygon.area
    w["Bauplatzfläche m²"] = Ergebnis(
        round(bauplatz_m2, 1), (Quelle("Kataster", "Grundstücksgrenzen"),), "aus Geometrie"
    )

    flaeche = grundriss.area
    begr = "Bauplatz abzüglich Vorgarten und Abstandsflächen"
    quellen: tuple[Quelle, ...] = (
        Quelle("BO für Wien", "§ 79 Abs. 1, 3"),
    )
    grenzen = []
    if bp.bebaubare_flaeche_max_m2 is not None:
        grenzen.append(bp.bebaubare_flaeche_max_m2)
    if bp.bebaubare_flaeche_max_anteil is not None:
        grenzen.append(bp.bebaubare_flaeche_max_anteil * bauplatz_m2)
    if grenzen and min(grenzen) < flaeche:
        flaeche = min(grenzen)
        begr = "begrenzt durch Besondere Bestimmung zur bebaubaren Fläche"
        quellen += (Quelle("Bebauungsplan", "§ 5 Abs. 4 BO, bebaubare Fläche"),)
    w["Bebaute Fläche m²"] = Ergebnis(round(flaeche, 1), quellen, begr)
    if flaeche <= 0:
        hinweise.append("Nach Abständen bleibt keine bebaubare Fläche.")
        return s

    gh = bauklassen.zulaessige_gebaeudehoehe(
        bp.bauklasse,
        fluchtlinienabstand=bp.fluchtlinienabstand,
        festgesetzte_hoehe=bp.festgesetzte_hoehe,
        grenzmasse_vi=bp.grenzmasse_vi,
        schutzzone=bp.schutzzone,
        gartensiedlung=bp.gartensiedlung,
    )
    w["Gebäudehöhe m"] = gh

    geschosse = math.floor(gh.wert / a.geschosshoehe + 1e-9)
    w["Vollgeschoße"] = Ergebnis(
        geschosse,
        gh.quellen,
        f"{gh.wert} m / {a.geschosshoehe} m Geschoßhöhe (Annahme), abgerundet",
    )

    winkel = umriss.umrisswinkel(bp.gartensiedlung, bp.dachneigung)
    dach = umriss.max_dachhoehe(bp.bauklasse, bp.bauweise, bp.wohngebiet)
    trakt = a.trakttiefe or _kuerzere_seite(grundriss)
    # Rest über dem letzten Vollgeschoß bleibt für das Dach nutzbar
    rest = gh.wert - geschosse * a.geschosshoehe
    dg = umriss.dachgeschosse(
        trakt, winkel.wert, dach.wert + rest, a.geschosshoehe
    )
    # Umriss steigt von allen Fronten an: Dachgeschoß = Grundriss, allseitig eingerückt
    anteil = flaeche / grundriss.area
    dg_flaechen = [
        grundriss.buffer(-(trakt - b) / 2, join_style="mitre").area * anteil
        for b in dg.wert
    ]
    w["Dachgeschoße"] = dg

    bgf = flaeche * geschosse + sum(dg_flaechen)
    w["BGF m²"] = Ergebnis(
        round(bgf, 1),
        gh.quellen + winkel.quellen + dach.quellen,
        (
            f"{flaeche:.1f} m² × {geschosse} Vollgeschoße + "
            f"{sum(dg_flaechen):.1f} m² Dachgeschoße"
        ),
    )

    nf = bgf * a.nutzflaechenfaktor
    w["Nutzfläche m²"] = Ergebnis(
        round(nf, 1),
        (Quelle("Annahme", "Nutzflächenfaktor"),),
        f"BGF × {a.nutzflaechenfaktor}",
    )
    wohnungen = math.floor(nf / a.wohnungsgroesse_m2)
    w["Wohnungen"] = Ergebnis(
        wohnungen,
        (Quelle("Annahme", "Wohnungsgröße"),),
        f"{nf:.0f} m² / {a.wohnungsgroesse_m2} m² je Wohnung",
    )
    w["Pflichtstellplätze"] = stellplaetze.pflichtstellplaetze(
        nf, bp.stellplatzregulativ_prozent, kleinhaus_eine_wohnung=wohnungen <= 1
    )

    frei = bauplatz_m2 - flaeche
    w["Freifläche m²"] = Ergebnis(
        round(frei, 1), (Quelle("BO für Wien", "§ 79"),), "Bauplatz minus bebaute Fläche"
    )
    w["davon unversiegelt mind. m²"] = abstaende.mindest_unversiegelt(frei)
    w["Bäume"] = abstaende.baeume(frei)
    return s
