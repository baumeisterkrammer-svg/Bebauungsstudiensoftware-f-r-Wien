"""Ausschnitt des Flächenwidmungs- und Bebauungsplans (Stadt Wien, WMTS, CC BY 4.0).

Die Stadt Wien veröffentlicht den Flächenwidmungs- und Bebauungsplan nur
als Kachelbild (WMTS), nicht als Vektordaten. Ebenen:

- flwbplmzk: gesamter Plan mit Bebauungsbestimmungen über der Mehrzweckkarte
- flwbplflucht: nur Fluchtlinien
- flwbplgen, flwbplschutz, flwbplwohn: Widmung, Schutzzonen, Wohnzonen

Dieses Modul holt die Kacheln rund um ein Grundstück, setzt sie zu einem
georeferenzierten Bild zusammen und legt den Ausschnitt dem Bericht bei.
"""

from __future__ import annotations

import io
import math
import re
import urllib.request
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from pyproj import Transformer

CAPS = "https://mapsneu.wien.gv.at/wmtsneu/1.0.0/WMTSCapabilities.xml"
UA = {"User-Agent": "bebauungsstudie/0.1"}


def _hole(url: str, timeout: float = 30) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


@dataclass
class Matrix:
    ident: str
    aufloesung: float  # CRS-Einheiten je Pixel
    links: float
    oben: float
    kachel: int
    breite: int
    hoehe: int


@dataclass
class Ebene:
    name: str
    vorlage: str
    stil: str
    matrixset: str
    crs: int
    matrizen: list[Matrix]


@lru_cache(maxsize=1)
def _capabilities() -> str:
    return _hole(CAPS).decode("utf-8", "replace")


def ebene(name: str, xml: str | None = None) -> Ebene:
    xml = xml or _capabilities()
    m = re.search(r"<Layer>(?:(?!</Layer>).)*?<ows:Identifier>" + re.escape(name)
                  + r"</ows:Identifier>(?:(?!</Layer>).)*</Layer>", xml, re.S)
    if not m:
        raise LookupError(f"WMTS-Ebene {name} nicht gefunden")
    lay = m.group(0)
    vorlage = re.search(r'<ResourceURL[^>]*template="([^"]+)"', lay).group(1)
    stil = re.search(r"<Style[^>]*>.*?<ows:Identifier>([^<]+)</ows:Identifier>", lay, re.S).group(1)
    sets = re.findall(r"<TileMatrixSet>([^<]+)</TileMatrixSet>", lay)
    for ms in sets:
        tms = re.search(r"<TileMatrixSet>\s*<ows:Identifier>" + re.escape(ms)
                        + r"</ows:Identifier>(.*?)</TileMatrixSet>", xml, re.S)
        if not tms:
            continue
        body = tms.group(1)
        crs_text = re.search(r"<ows:SupportedCRS>([^<]+)<", body).group(1)
        crs = int(re.findall(r"(\d+)", crs_text)[-1])
        matrizen = []
        for tm in re.findall(r"<TileMatrix>(.*?)</TileMatrix>", body, re.S):
            g = lambda tag: re.search(rf"<(?:ows:)?{tag}>([^<]+)</", tm).group(1)  # noqa: E731
            links, oben = (float(v) for v in g("TopLeftCorner").split())
            if crs == 4326:
                links, oben = oben, links
            matrizen.append(Matrix(g("Identifier"), float(g("ScaleDenominator")) * 0.00028,
                                   links, oben, int(g("TileWidth")), int(g("MatrixWidth")),
                                   int(g("MatrixHeight"))))
        if matrizen and crs != 4326:
            return Ebene(name, vorlage, stil, ms, crs, matrizen)
    raise LookupError(f"Kein projiziertes TileMatrixSet für {name}")


def ausschnitt(name: str, bbox31256: tuple[float, float, float, float],
               ziel_aufloesung: float = 0.15, max_kacheln: int = 64):
    """Bild (H×W×3, uint8) und Ausdehnung (xmin, xmax, ymin, ymax) in EPSG:31256.

    Die Kacheln liegen im CRS des Dienstes; für die Darstellung im lokalen
    System wird das Bild über die Eckpunkte eingepasst (bei Wien und kleinem
    Ausschnitt ist die Verzerrung vernachlässigbar)."""
    from PIL import Image

    e = ebene(name)
    hin = Transformer.from_crs(31256, e.crs, always_xy=True)
    zur = Transformer.from_crs(e.crs, 31256, always_xy=True)
    xs, ys = hin.transform([bbox31256[0], bbox31256[2], bbox31256[0], bbox31256[2]],
                           [bbox31256[1], bbox31256[1], bbox31256[3], bbox31256[3]])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    massstab = (x1 - x0) / max(1e-9, bbox31256[2] - bbox31256[0])
    passend = [m for m in e.matrizen if m.aufloesung <= ziel_aufloesung * massstab * 1.5]
    m = min(passend, key=lambda m: -m.aufloesung) if passend else min(e.matrizen, key=lambda m: m.aufloesung)
    groesse = m.kachel * m.aufloesung
    c0, c1 = int((x0 - m.links) // groesse), int((x1 - m.links) // groesse)
    r0, r1 = int((m.oben - y1) // groesse), int((m.oben - y0) // groesse)
    if (c1 - c0 + 1) * (r1 - r0 + 1) > max_kacheln:
        raise ValueError("Ausschnitt zu groß")
    bild = Image.new("RGB", ((c1 - c0 + 1) * m.kachel, (r1 - r0 + 1) * m.kachel), "white")
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            url = (e.vorlage.replace("{Style}", e.stil).replace("{TileMatrixSet}", e.matrixset)
                   .replace("{TileMatrix}", m.ident).replace("{TileRow}", str(r)).replace("{TileCol}", str(c)))
            try:
                k = Image.open(io.BytesIO(_hole(url))).convert("RGB")
                bild.paste(k, ((c - c0) * m.kachel, (r - r0) * m.kachel))
            except Exception:
                pass
    lx, oy = m.links + c0 * groesse, m.oben - r0 * groesse
    rx, uy = m.links + (c1 + 1) * groesse, m.oben - (r1 + 1) * groesse
    (ax, bx), (ay, by) = zur.transform([lx, rx], [uy, oy])
    return np.asarray(bild), (ax, bx, ay, by)


def zeichne_ausschnitt(pfad, umriss_pts, bbox, ebenen=("flwbplmzk",), titel="") -> list[str]:
    """Speichert PNGs der Planebenen mit dem Grundstück als rote Linie."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dateien = []
    for name in ebenen:
        bild, ext = ausschnitt(name, bbox)
        fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
        ax.imshow(bild, extent=ext, interpolation="bilinear")
        xs, ys = zip(*(list(umriss_pts) + [umriss_pts[0]]))
        ax.plot(xs, ys, color="#d00", lw=2)
        ax.set_xlim(bbox[0], bbox[2])
        ax.set_ylim(bbox[1], bbox[3])
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(titel or name, fontsize=9)
        ax.text(0.01, 0.01, "Plan: Stadt Wien – data.wien.gv.at, CC BY 4.0 (keine Rechtsauskunft)",
                transform=ax.transAxes, fontsize=6, bbox=dict(fc="white", ec="none", alpha=0.8))
        p = f"{pfad}_{name}.png"
        fig.savefig(p, bbox_inches="tight")
        plt.close(fig)
        dateien.append(p)
    return dateien
