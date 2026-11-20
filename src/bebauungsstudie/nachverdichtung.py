"""Studienmodus Nachverdichtung: Bestand erhalten, Potenzial dazurechnen.

Neubau (erstelle_studie) rechnet Abbruch und volle Ausnutzung. Nachverdichtung
behält die Bestandsgebäude am Bauplatz (Baukörpermodell der Stadt Wien) und
rechnet, was innerhalb derselben Regeln zusätzlich möglich ist:

- Aufstockung: Bestand innerhalb der bebaubaren Fläche bis zur Zahl der
  zulässigen Vollgeschoße erhöhen
- Dachgeschoßausbau: Dachgeschoße über allen Teilen, die danach die volle
  Geschoßzahl erreichen; der Umriss steigt von deren Fronten an
- Zubau im Hof: bebaubare Fläche, die noch frei ist, mit voller Geschoßzahl

Bestand außerhalb der bebaubaren Fläche bleibt unverändert stehen. Die
Geschoßzahl des Bestands wird aus der Gebäudehöhe geschätzt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .herleitung import Ergebnis, Quelle
from .regeln import umriss
from .studie import Studie, dachgeschoss_grundriss, trakttiefe

ARTEN = ("bestand", "aufstockung", "zubau", "dachgeschoss")


@dataclass
class Volumen:
    flaeche: BaseGeometry
    """Grundriss in Projektkoordinaten (wie der Bauplatz)."""
    z0: float
    z1: float
    art: str
    """bestand, aufstockung, zubau oder dachgeschoss"""


@dataclass
class Nachverdichtung:
    volumen: list[Volumen] = field(default_factory=list)
    werte: dict[str, Ergebnis] = field(default_factory=dict)
    hinweise: list[str] = field(default_factory=list)

    def bgf(self, art: str) -> float:
        return sum(v.flaeche.area for v in self.volumen if v.art == art)

    def bericht(self) -> str:
        zeilen = ["Nachverdichtung (Bestand erhalten)", ""]
        for name, e in self.werte.items():
            zeilen.append(f"{name}: {e.wert}  {e.begruendung}")
        if self.hinweise:
            zeilen += ["", "Hinweise:"] + [f"- {h}" for h in self.hinweise]
        return "\n".join(zeilen)


def _teile(g: BaseGeometry, mindest: float = 2.0) -> list[Polygon]:
    if g.is_empty:
        return []
    polys = [g] if isinstance(g, Polygon) else [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]
    return [p for p in polys if p.area >= mindest]


def bestandsgeschosse(hoehe: float, geschosshoehe: float = 3.0) -> int:
    """Geschoßzahl aus der Höhe über Gelände (Dachraum zählt nicht mit)."""
    return max(1, math.floor(hoehe / geschosshoehe + 0.2))


def erstelle_nachverdichtung(studie: Studie, bestand: list[tuple[BaseGeometry, float]],
                             geschosshoehe_bestand: float = 3.2) -> Nachverdichtung | None:
    """`bestand`: Grundrisse am Bauplatz mit Höhe über Gelände (m).

    Ohne Bestand oder ohne bebaubare Fläche: None."""
    w = studie.werte
    if not bestand or "Vollgeschoße" not in w:
        return None
    bp, a = studie.bauplatz, studie.annahmen
    platz = bp.polygon
    grundriss = studie.grundriss
    n = w["Vollgeschoße"].wert
    gh = a.geschosshoehe
    nv = Nachverdichtung()

    # Bestand ohne Überlappungen, höchste Körper zuerst
    belegt: BaseGeometry = Polygon()
    teile: list[tuple[Polygon, int, float]] = []
    for g, h in sorted(bestand, key=lambda b: -b[1]):
        rest = g.intersection(platz).difference(belegt)
        for p in _teile(rest):
            teile.append((p, bestandsgeschosse(h, geschosshoehe_bestand), h))
        belegt = belegt.union(g.intersection(platz))
    if not teile:
        return None

    bestand_bgf = 0.0
    voll: list[BaseGeometry] = []
    for p, f, h in teile:
        bestand_bgf += p.area * f
        drin = p.intersection(grundriss)
        # wo weitergebaut wird, endet der Bestand an der Decke des obersten Geschoßes
        if f <= n and drin.area > 5:
            nv.volumen.append(Volumen(drin, 0, f * gh, "bestand"))
            for q in _teile(p.difference(drin)):
                nv.volumen.append(Volumen(q, 0, h, "bestand"))
        else:
            nv.volumen.append(Volumen(p, 0, h, "bestand"))
        if f < n:
            for q in _teile(drin, 5.0):
                nv.volumen.append(Volumen(q, f * gh, n * gh, "aufstockung"))
                voll.append(q)
        elif f == n:
            voll += _teile(drin, 5.0)

    frei = grundriss.difference(belegt.buffer(0.05))
    frei = frei.buffer(-1.5, join_style="mitre").buffer(1.5, join_style="mitre").intersection(frei)
    zubau = _teile(frei, 10.0)
    for q in zubau:
        nv.volumen.append(Volumen(q, 0, n * gh, "zubau"))
    voll += zubau

    # Dachgeschoße wie beim Neubau, aber nur über voll hohen Teilen
    hoch = unary_union([v.buffer(0.1, join_style="mitre") for v in voll]).buffer(
        -0.1, join_style="mitre") if voll else Polygon()
    if not hoch.is_empty and w.get("Gebäudehöhe m") is not None:
        # Umriss von den Fronten des tatsächlichen Baukörpers (Bestand + Zubau) aus,
        # nicht vom Neubau-Grundriss: sonst sitzt das DG über einem schmaleren
        # Bestandstrakt versetzt.
        trakt = a.trakttiefe or trakttiefe(bp, hoch)
        winkel = umriss.umrisswinkel(bp.gartensiedlung, bp.dachneigung).wert
        dach = umriss.max_dachhoehe(bp.bauklasse, bp.bauweise, bp.wohngebiet).wert
        rest = w["Gebäudehöhe m"].wert - n * gh
        breiten = umriss.dachgeschosse(trakt, winkel, dach + rest, gh).wert
        for k, breite in enumerate(breiten):
            dg = dachgeschoss_grundriss(bp, hoch, (trakt - breite) / 2)
            for q in _teile(dg, 5.0):
                nv.volumen.append(Volumen(q, (n + k) * gh, (n + k + 1) * gh, "dachgeschoss"))

    def summe(art):
        return sum(v.flaeche.area * round((v.z1 - v.z0) / gh) for v in nv.volumen if v.art == art)

    auf, zu, dgf = summe("aufstockung"), summe("zubau"), summe("dachgeschoss")
    plus = auf + zu + dgf
    neubau = w["BGF m²"].wert
    q_bkm = (Quelle("Stadt Wien", "Baukörpermodell (FMZK)"),)
    q_regel = w["BGF m²"].quellen
    stock = sorted({f for _, f, _ in teile})
    nv.werte = {
        "Bestand Grundfläche m²": Ergebnis(round(sum(p.area for p, _, _ in teile), 1), q_bkm,
                                           "Baukörper am Bauplatz laut Baukörpermodell"),
        "Bestand BGF m² (geschätzt)": Ergebnis(
            round(bestand_bgf, 1), q_bkm,
            f"Grundfläche × Geschoße ({', '.join(map(str, stock))}), aus Höhe / "
            f"{geschosshoehe_bestand} m geschätzt"),
        "Aufstockung BGF m²": Ergebnis(round(auf, 1), q_regel,
                                       f"Bestand in der bebaubaren Fläche auf {n} Vollgeschoße erhöht"),
        "Dachgeschoßausbau BGF m²": Ergebnis(round(dgf, 1), q_regel,
                                              "Dachgeschoße nach § 81 Abs. 4 über dem voll hohen Baukörper (Bestand + Zubau)"),
        "Zubau im Hof BGF m²": Ergebnis(round(zu, 1), q_regel,
                                        f"freie bebaubare Fläche × {n} Vollgeschoße"),
        "Zusätzliche BGF m²": Ergebnis(round(plus, 1), q_regel,
                                       "Aufstockung + Dachgeschoßausbau + Zubau (Differenz zum Bestand)"),
        "BGF nach Nachverdichtung m²": Ergebnis(round(bestand_bgf + plus, 1), q_regel,
                                                "Bestand + zusätzliche BGF"),
        "Zusätzliche Wohnungen": Ergebnis(
            math.floor(plus * a.nutzflaechenfaktor / a.wohnungsgroesse_m2),
            (Quelle("Annahme", "Wohnungsgröße"),),
            f"zusätzliche BGF × {a.nutzflaechenfaktor} / {a.wohnungsgroesse_m2} m²"),
        "Vergleich Neubau BGF m²": Ergebnis(
            neubau, q_regel,
            f"Neubau nach Abbruch; Differenz zur Nachverdichtung {neubau - (bestand_bgf + plus):+.0f} m²"),
    }
    if auf > 0:
        nv.hinweise.append("Aufstockung: Tragfähigkeit von Wänden und Fundamenten, Brandschutz und "
                           "Erschließung (Lift) des Bestands prüfen.")
    if zu > 0:
        nv.hinweise.append("Zubau im Hof: Belichtung der bestehenden Hoffenster und Abstände zum "
                           "Bestand prüfen.")
    if any(f > n for _, f, _ in teile):
        nv.hinweise.append("Teile des Bestands sind höher als heute zulässig; sie bleiben im "
                           "Bestand erhalten, ein Neubau dürfte diese Höhe nicht erreichen.")
    if belegt.difference(grundriss.buffer(0.5)).area > 5:
        nv.hinweise.append("Teile des Bestands liegen außerhalb der bebaubaren Fläche und bleiben "
                           "unverändert (kein Ausbau dort).")
    nv.hinweise.append("Bestandsgeschoße aus der Gebäudehöhe des Baukörpermodells geschätzt; "
                       "mit Bestandsplänen abgleichen.")
    return nv
