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
    bloecke = {}
    for blk in re.findall(r"<TileMatrixSet(?:\s[^>]*)?>(.*?)</TileMatrixSet>", xml, re.S):
        if "<TileMatrix>" in blk or "<TileMatrix " in blk:
            ident = re.search(r"<ows:Identifier>([^<]+)</ows:Identifier>", blk).group(1).strip()
            bloecke[ident] = blk
    for ms in sets:
        body = bloecke.get(ms.strip())
        if not body:
            continue
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
    raise LookupError(f"Kein projiziertes TileMatrixSet für {name} (Sets {sets}, bekannt {list(bloecke)})")


def ausschnitt(name: str, bbox31256: tuple[float, float, float, float],
               ziel_aufloesung: float = 0.15, max_kacheln: int = 64, modus: str = "RGB"):
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
    leer = (255, 255, 255) if modus == "RGB" else (0, 0, 0, 0)
    bild = Image.new(modus, ((c1 - c0 + 1) * m.kachel, (r1 - r0 + 1) * m.kachel), leer)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            url = (e.vorlage.replace("{Style}", e.stil).replace("{TileMatrixSet}", e.matrixset)
                   .replace("{TileMatrix}", m.ident).replace("{TileRow}", str(r)).replace("{TileCol}", str(c)))
            try:
                k = Image.open(io.BytesIO(_hole(url))).convert("RGBA")
                if modus == "RGB":
                    hinten = Image.new("RGBA", k.size, (255, 255, 255, 255))
                    k = Image.alpha_composite(hinten, k)
                bild.paste(k.convert(modus), ((c - c0) * m.kachel, (r - r0) * m.kachel))
            except Exception:
                pass
    lx, oy = m.links + c0 * groesse, m.oben - r0 * groesse
    rx, uy = m.links + (c1 + 1) * groesse, m.oben - (r1 + 1) * groesse
    (ax, bx), (ay, by) = zur.transform([lx, rx], [uy, oy])
    return np.asarray(bild), (ax, bx, ay, by)


def zeichne_ausschnitt(pfad, umriss_pts, bbox, ebenen=("flwbplmzk",), titel="",
                       erkannt=None) -> list[str]:
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
        ax.plot(xs, ys, color="#d00", lw=2, label="Grundstück (BEV)")
        if erkannt:
            ex, ey = zip(*(list(erkannt) + [erkannt[0]]))
            ax.plot(ex, ey, color="#06c", lw=1.6, ls="--", label="erkannte Baufluchtlinien")
            ax.legend(loc="upper right", fontsize=7)
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


# --- Fluchtlinien aus dem Planbild -------------------------------------------

@dataclass
class Fluchtlinien:
    flaeche: list[tuple[float, float]] | None
    """Fläche innerhalb der Baufluchtlinien, die das Grundstück überdeckt (EPSG:31256)."""
    strassenbreiten: dict[int, float]
    """Abstand der Baulinien über die Straße je Straßenkante des Grundstücks (m)."""
    protokoll: list[str]


def _rote_linien(bild: np.ndarray) -> np.ndarray:
    r, g, b = (bild[..., i].astype(int) for i in range(3))
    sichtbar = bild[..., 3] > 80 if bild.shape[-1] == 4 else np.ones(r.shape, bool)
    return sichtbar & (r > 140) & (g < 120) & (b < 120) & (r - g > 60)


def _ist_strich(teil: np.ndarray, px: float, py: float, toleranz: float = 0.45) -> bool:
    """True für gerade Striche und Strich-Ecken (L-Form), False für Buchstaben.

    Das Skelett eines Strichs hat zwei Enden, keine Verzweigung und lässt sich
    durch höchstens zwei gerade Stücke annähern. Buchstaben wie W, g, m, 0, 5
    haben Schleifen, Verzweigungen oder mehrere Knicke."""
    from scipy import ndimage
    from shapely.geometry import LineString, MultiPoint
    from skimage.morphology import skeletonize

    ske = skeletonize(teil)
    if ske.sum() < 2:
        return True
    nachbarn = ndimage.convolve(ske.astype(int), np.ones((3, 3), int), mode="constant") - 1
    enden = np.argwhere(ske & (nachbarn == 1))
    if len(enden) != 2 or (ske & (nachbarn >= 3)).sum() > 2:
        return False
    pts = np.argwhere(ske)[:, ::-1] * np.array([px, py])
    a, b = enden[0][::-1] * np.array([px, py]), enden[1][::-1] * np.array([px, py])
    wolke = MultiPoint(pts)
    gerade = LineString([a, b])
    abst = np.array([gerade.distance(p) for p in wolke.geoms])
    if abst.max() <= toleranz:
        return True
    c = pts[int(abst.argmax())]
    knick = LineString([a, c, b])
    return max(knick.distance(p) for p in wolke.geoms) <= toleranz


def trenne_linien_schrift(rot: np.ndarray, px: float, py: float) -> tuple[np.ndarray, np.ndarray]:
    """Teilt die rote Maske in Linien (Fluchtlinien, Striche) und Schrift.

    Teile länger als 8 m oder kleiner als 3 m² sind Linien; die übrigen
    werden über ihr Skelett unterschieden (siehe `_ist_strich`)."""
    from scipy import ndimage

    lab, n = ndimage.label(rot, structure=np.ones((3, 3)))
    linien = np.zeros_like(rot)
    schrift = np.zeros_like(rot)
    for k, sl in enumerate(ndimage.find_objects(lab), start=1):
        teil = lab[sl] == k
        # kleine Teile (Striche, Strichecken, Punkte) bleiben Linien, damit
        # gestrichelte Baufluchtlinien geschlossen bleiben
        if (max(teil.shape[0] * py, teil.shape[1] * px) > 8.0 or teil.sum() * px * py < 3.0
                or _ist_strich(teil, px, py)):
            linien[sl] |= teil
        else:
            schrift[sl] |= teil
    return linien, schrift


def fluchtlinien_auswerten(bild: np.ndarray, ext, umriss, strassenkanten,
                           spaltbreite: float = 3.0) -> Fluchtlinien:
    """Erkennt aus dem Fluchtlinien-Bild (rot auf transparent) die Fläche innerhalb
    der Baufluchtlinien am Grundstück und die Straßenbreiten.

    Vorgehen: rote Pixel maskieren, Strichlücken bis `spaltbreite` schließen,
    die eingeschlossenen Flächen beschriften; maßgeblich ist die geschlossene
    Fläche mit der größten Überdeckung des Grundstücks."""
    from contourpy import contour_generator
    from matplotlib.path import Path as MPath
    from scipy import ndimage
    from shapely.geometry import Polygon as SPolygon

    log: list[str] = []
    h, w = bild.shape[:2]
    px = (ext[1] - ext[0]) / w
    py = (ext[3] - ext[2]) / h
    rot = _rote_linien(bild)
    rot_anteil = rot.mean()
    log.append(f"Fluchtlinien-Bild: {w}×{h} px, {px:.2f} m/px, rote Pixel {rot_anteil:.1%}")

    def welt(col, row):
        return ext[0] + (col + 0.5) * px, ext[3] - (row + 0.5) * py

    def pixel(x, y):
        return (x - ext[0]) / px - 0.5, (ext[3] - y) / py - 0.5

    # Strichlücken schließen
    rad = max(1, int(round(spaltbreite / 2 / px)))
    yy, xx = np.ogrid[-rad:rad + 1, -rad:rad + 1]
    scheibe = (xx * xx + yy * yy) <= rad * rad
    # Linien um die halbe Lückenbreite verdicken; die gefundenen Flächen werden
    # danach um dasselbe Maß wieder vergrößert
    linien, _schrift = trenne_linien_schrift(rot, px, py)
    log.append(f"Linien {linien.mean():.1%}, Schrift {_schrift.mean():.1%} der Bildfläche")
    zu = ndimage.binary_dilation(linien, structure=scheibe)
    lab, anzahl = ndimage.label(~zu)
    rand = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}

    cols, rows = np.meshgrid(np.arange(w), np.arange(h))
    gx, gy = welt(cols, rows)
    im_gst = MPath(list(umriss)).contains_points(np.c_[gx.ravel(), gy.ravel()]).reshape(h, w)
    gst_flaeche = SPolygon(umriss).area
    pix = px * py
    beste, beste_ueb = None, 0.0
    for k in range(1, anzahl + 1):
        if k in rand:
            continue
        maske = lab == k
        flaeche = maske.sum() * pix
        ueb = (maske & im_gst).sum() * pix
        if ueb > beste_ueb and 5 < flaeche < 3 * gst_flaeche + 3000:
            beste, beste_ueb = k, ueb
    flaeche_pts = None
    if beste is not None and beste_ueb > 0.08 * gst_flaeche:
        linien = contour_generator(z=(lab == beste).astype(float)).lines(0.5)
        ring = max(linien, key=len)
        pts = [welt(c, r) for c, r in ring]
        poly = SPolygon(pts).buffer(rad * px + 0.1, join_style="mitre").simplify(0.25)
        if poly.geom_type == "Polygon" and poly.area > 10:
            flaeche_pts = [(round(x, 2), round(y, 2)) for x, y in poly.exterior.coords[:-1]]
            log.append(f"Baufluchtlinien: geschlossene Fläche {poly.area:.0f} m² erkannt, "
                       f"davon {poly.intersection(SPolygon(umriss)).area:.0f} m² im Grundstück")
    if flaeche_pts is None:
        log.append("Baufluchtlinien: keine geschlossene Fläche am Grundstück erkannt")

    # Straßenbreiten: von der Straßenkante nach außen bis zur gegenüberliegenden Baulinie
    breiten = {}
    n = len(umriss)
    for i in sorted(strassenkanten):
        (x0, y0), (x1, y1) = umriss[i], umriss[(i + 1) % n]
        lang = math.hypot(x1 - x0, y1 - y0)
        if lang < 3:
            continue
        nx, ny = (y1 - y0) / lang, -(x1 - x0) / lang
        messungen = []
        for f in (0.2, 0.35, 0.5, 0.65, 0.8):
            mx, my = x0 + f * (x1 - x0), y0 + f * (y1 - y0)
            t, im_rot, verlassen = 0.0, False, False
            while t < 60:
                c, r = pixel(mx + nx * t, my + ny * t)
                c, r = int(round(c)), int(round(r))
                if not (0 <= c < w and 0 <= r < h):
                    break
                ist = bool(rot[r, c])
                if t > 1.5 and not ist:
                    verlassen = True
                if verlassen and ist and t > 3:
                    start = t
                    while t < 60:
                        c, r = (int(round(v)) for v in pixel(mx + nx * t, my + ny * t))
                        if not (0 <= c < w and 0 <= r < h and rot[r, c]):
                            break
                        t += px / 2
                    messungen.append((start + t) / 2)
                    break
                t += px / 2
        if len(messungen) >= 3:
            b = round(float(np.median(messungen)) * 2) / 2
            breiten[i] = b
            log.append(f"Straßenkante {i}: Abstand der Baulinien ca. {b:.1f} m "
                       f"(Messungen {', '.join(f'{m:.1f}' for m in messungen)})")
        else:
            log.append(f"Straßenkante {i}: Straßenbreite nicht messbar")
    return Fluchtlinien(flaeche_pts, breiten, log)


def lies_fluchtlinien(umriss, strassenkanten, bbox, aufloesung: float = 0.1):
    bild, ext = ausschnitt("flwbplflucht", bbox, ziel_aufloesung=aufloesung, max_kacheln=100, modus="RGBA")
    return fluchtlinien_auswerten(bild, ext, umriss, strassenkanten), bild, ext
