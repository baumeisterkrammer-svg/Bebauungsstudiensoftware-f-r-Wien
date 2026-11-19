"""Geometrisches Massenmodell einer Studie: Geschoße, Hüllkörper, Lagebezug.

Alle Ausgaben (IFC, Pläne, DXF) bauen auf diesem Modell auf, damit Zahlen
und Zeichnungen aus derselben Geometrie stammen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry

from .regeln import umriss
from .studie import Studie, _kuerzere_seite


@dataclass
class Geschoss:
    name: str
    ok_fussboden: float
    """Höhe Oberkante Fußboden über Gelände (m)."""
    hoehe: float
    flaeche: BaseGeometry
    dachgeschoss: bool = False


@dataclass
class Massenmodell:
    bauplatz: Polygon
    bebaubar: BaseGeometry
    geschosse: list[Geschoss]
    gebaeudehoehe: float
    dachabschluss: float
    """Höhe des obersten zulässigen Dachabschlusses über Gelände."""
    umrisswinkel: float
    strassenkante: LineString
    vorgarten_linie: LineString | None

    @property
    def gesamthoehe(self) -> float:
        g = self.geschosse[-1]
        return g.ok_fussboden + g.hoehe

    def lokal(self, geom: BaseGeometry) -> BaseGeometry:
        """In ein lokales System drehen: u entlang der Straße, v ins Grundstück."""
        (x0, y0), (x1, y1) = self.strassenkante.coords[:2]
        winkel = math.degrees(math.atan2(y1 - y0, x1 - x0))
        g = affinity.translate(geom, -x0, -y0)
        g = affinity.rotate(g, -winkel, origin=(0, 0))
        # sicherstellen, dass das Grundstück auf der positiven v-Seite liegt
        bp = affinity.rotate(
            affinity.translate(self.bauplatz, -x0, -y0), -winkel, origin=(0, 0)
        )
        if bp.centroid.y < 0:
            g = affinity.scale(g, 1, -1, origin=(0, 0))
        return g


def erzeuge_modell(studie: Studie) -> Massenmodell:
    bp = studie.bauplatz
    a = studie.annahmen
    w = studie.werte
    if "BGF m²" not in w:
        raise ValueError("Die Studie enthält keine bebaubare Fläche.")

    grundriss = studie.grundriss
    gh = w["Gebäudehöhe m"].wert
    n = w["Vollgeschoße"].wert
    geschosse = [
        Geschoss(
            "EG" if i == 0 else f"{i}. OG",
            i * a.geschosshoehe,
            a.geschosshoehe,
            grundriss,
        )
        for i in range(n)
    ]

    winkel = umriss.umrisswinkel(bp.gartensiedlung, bp.dachneigung).wert
    dach = umriss.max_dachhoehe(bp.bauklasse, bp.bauweise, bp.wohngebiet).wert
    trakt = a.trakttiefe or _kuerzere_seite(grundriss)
    for k, breite in enumerate(w["Dachgeschoße"].wert):
        einzug = (trakt - breite) / 2
        flaeche = grundriss.buffer(-einzug, join_style="mitre")
        if flaeche.is_empty:
            break
        geschosse.append(
            Geschoss(f"{k + 1}. DG", (n + k) * a.geschosshoehe, a.geschosshoehe,
                     flaeche, dachgeschoss=True)
        )

    kanten = sorted(bp.strassenkanten) or [0]
    strasse = bp.kante(kanten[0])
    vg = None
    if bp.vorgarten:
        tiefe = bp.vorgarten_tiefe or 5.0
        vg = strasse.parallel_offset(tiefe, "left")
        if not bp.polygon.buffer(0.01).intersects(vg):
            vg = strasse.parallel_offset(tiefe, "right")

    return Massenmodell(
        bauplatz=bp.polygon,
        bebaubar=grundriss,
        geschosse=geschosse,
        gebaeudehoehe=gh,
        dachabschluss=gh + dach,
        umrisswinkel=winkel,
        strassenkante=strasse,
        vorgarten_linie=vg,
    )
