"""Umgebung eines Bauplatzes aus den offenen Daten der Stadt Wien (CC BY 4.0).

- Nachbargebäude: Baukörpermodell der Flächen-Mehrzweckkarte (FMZKBKMOGD),
  je Baukörper Grundriss, Oberkante (O_KOTE) und Gelände (T_KOTE/HOEHE_DGM)
- Luftbild: aktuelles Orthofoto der Stadt Wien aus dem WMTS (Ebene „lb…“)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry

from . import bebauungsplan, wien


@dataclass
class Baukoerper:
    grundriss: Polygon
    hoehe: float
    """Höhe über Gelände in m."""
    am_bauplatz: bool = False


@dataclass
class Kontext:
    bestand: list[Baukoerper] = field(default_factory=list)
    luftbild: np.ndarray | None = None
    luftbild_ausdehnung: tuple[float, float, float, float] | None = None
    """xmin, xmax, ymin, ymax in EPSG:31256."""
    protokoll: list[str] = field(default_factory=list)


def luftbild_ebene(xml: str | None = None) -> str:
    xml = xml or bebauungsplan._capabilities()
    ids = re.findall(r"<Layer>.*?<ows:Identifier>([^<]+)</ows:Identifier>", xml, re.S)
    lb = [i for i in ids if re.fullmatch(r"lb(\d{4})?", i)]
    if not lb:
        lb = [i for i in ids if i.lower().startswith(("lb", "orthofoto", "luftbild"))]
    if not lb:
        raise LookupError("keine Luftbild-Ebene im WMTS gefunden")
    return "lb" if "lb" in lb else max(lb)


def _polygone(g: BaseGeometry) -> list[Polygon]:
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return []


def hole_kontext(bauplatz: Polygon, radius: float = 45.0, luftbild: bool = True,
                 luftbild_radius: float = 110.0) -> Kontext:
    """`luftbild_radius`: halbe Seitenlänge des Luftbilds; deckt das A3-Blatt im Maßstab
    1:500 auch bei gedrehtem Bauplatz ab."""
    k = Kontext()
    c = bauplatz.centroid
    rand = radius + max(bauplatz.bounds[2] - bauplatz.bounds[0], bauplatz.bounds[3] - bauplatz.bounds[1]) / 2
    try:
        feats = wien.features("ogdwien:FMZKBKMOGD", c.x, c.y, radius=rand, max_features=2000).get("features", [])
        for f in feats:
            p = f.get("properties", {})
            o, t = p.get("O_KOTE"), p.get("T_KOTE") or p.get("HOEHE_DGM")
            if o is None or t is None or not f.get("geometry"):
                continue
            h = float(o) - float(t)
            if h < 1.0:
                continue
            for poly in _polygone(shape(f["geometry"])):
                am = poly.intersection(bauplatz).area > 0.5 * poly.area
                k.bestand.append(Baukoerper(poly, round(h, 1), am))
        k.protokoll.append(f"Umgebung: {len(k.bestand)} Baukörper im Umkreis von {rand:.0f} m "
                           f"(Stadt Wien, Baukörpermodell)")
    except Exception as e:
        k.protokoll.append(f"Umgebung: Baukörpermodell nicht abrufbar ({type(e).__name__}: {e})")
    if luftbild:
        try:
            name = luftbild_ebene()
            lr = max(rand, luftbild_radius)
            bbox = (c.x - lr, c.y - lr, c.x + lr, c.y + lr)
            bild, ext = bebauungsplan.ausschnitt(name, bbox, ziel_aufloesung=0.25, max_kacheln=144)
            k.luftbild, k.luftbild_ausdehnung = bild, tuple(ext)
            k.protokoll.append(f"Luftbild: Ebene {name} (Stadt Wien, CC BY 4.0)")
        except Exception as e:
            k.protokoll.append(f"Luftbild nicht abrufbar ({type(e).__name__}: {e})")
    return k
