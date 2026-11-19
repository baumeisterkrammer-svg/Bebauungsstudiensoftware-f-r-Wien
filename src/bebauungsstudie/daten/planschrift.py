"""Beschriftung des Bebauungsplans lesen (Bauweise, Bauklasse) per Texterkennung.

Die Fluchtlinien-Ebene des Wiener Plans enthält die Beschriftung der
Bauplätze in Rot, z. B. „W I o“ (Wohngebiet, Bauklasse I, offene Bauweise).
Die Texte stehen parallel zu den Straßen, also in beliebigem Winkel. Das
Bild wird deshalb in Schritten gedreht und jeweils mit Tesseract gelesen.

Benötigt das Programm `tesseract` (Linux: apt install tesseract-ocr). Ohne
Tesseract liefert das Modul kein Ergebnis und die Bauweise bleibt Eingabe.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

BAUWEISEN = {"o": "o", "g": "g", "gk": "gk", "ogk": "ogk", "gr": "gr"}
ROEMISCH = {"I", "II", "III", "IV", "V", "VI"}
WIDMUNGEN = {"W", "GB", "GS", "G", "IG", "BS", "SN", "SWW"}


@dataclass
class Wort:
    text: str
    x: float
    y: float
    sicherheit: float


def verfuegbar() -> bool:
    return shutil.which("tesseract") is not None


def _tesseract(bild: np.ndarray) -> list[tuple[str, float, float, float, float, float]]:
    """Wörter mit (text, links, oben, breite, höhe, konfidenz) in Pixeln."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "b.png"
        Image.fromarray(bild).save(p)
        r = subprocess.run(["tesseract", str(p), "stdout", "--psm", "11", "-l", "eng", "tsv"],
                           capture_output=True, text=True, timeout=60)
    woerter = []
    for zeile in r.stdout.splitlines()[1:]:
        f = zeile.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        woerter.append((f[11].strip(), float(f[6]), float(f[7]), float(f[8]), float(f[9]), float(f[10])))
    return woerter


def zurueck(x: float, y: float, winkel: float, groesse_gedreht, groesse) -> tuple[float, float]:
    """Pixel im mit PIL `rotate(winkel, expand=True)` gedrehten Bild → ungedrehtes Bild."""
    gw, gh = groesse_gedreht
    W, H = groesse
    cx, cy = x - gw / 2, y - gh / 2
    a = math.radians(winkel)
    return (cx * math.cos(a) - cy * math.sin(a) + W / 2,
            cx * math.sin(a) + cy * math.cos(a) + H / 2)


def lies_beschriftung(rot_maske: np.ndarray, ext, schritt: int = 15, vergroesserung: int = 3) -> list[Wort]:
    """Liest rote Beschriftung; Koordinaten der Wortmitten in EPSG:31256."""
    from PIL import Image

    if not verfuegbar():
        return []
    from scipy import ndimage

    h, w = rot_maske.shape
    px, py = (ext[1] - ext[0]) / w, (ext[3] - ext[2]) / h
    # Linien entfernen: zusammenhängende Teile, die länger als ein Schriftzeichen sind
    lab, n = ndimage.label(rot_maske, structure=np.ones((3, 3)))
    schrift = np.zeros_like(rot_maske)
    for k, sl in enumerate(ndimage.find_objects(lab), start=1):
        hoehe, breite = (sl[0].stop - sl[0].start) * py, (sl[1].stop - sl[1].start) * px
        anteil = (lab[sl] == k).mean()
        if max(hoehe, breite) <= 4.0 and anteil > 0.15:
            schrift[sl] |= lab[sl] == k
    rot_maske = schrift
    grund = Image.fromarray(np.where(rot_maske, 0, 255).astype(np.uint8))
    grund = grund.resize((w * vergroesserung, h * vergroesserung), Image.NEAREST)
    W, H = grund.size
    ergebnis: list[Wort] = []
    for winkel in range(0, 180, schritt):
        gedreht = grund.rotate(winkel, resample=Image.BILINEAR, expand=True, fillcolor=255)
        gw, gh = gedreht.size
        for text, l, o, b, hh, konf in _tesseract(np.asarray(gedreht)):
            if konf < 40:
                continue
            ux, uy = zurueck(l + b / 2, o + hh / 2, winkel, (gw, gh), (W, H))
            col, row = ux / vergroesserung, uy / vergroesserung
            ergebnis.append(Wort(text, ext[0] + col * px, ext[3] - row * py, konf))
    return ergebnis


def bauweise_aus_woertern(woerter: list[Wort], x: float, y: float, radius: float = 20.0, gebiet=None):
    """Bauweisen-Angabe zum Grundstück, mit Begründung.

    `gebiet`: Fläche innerhalb der Baufluchtlinien (shapely). Die Beschriftung
    gilt für diese ganze Fläche, auch wenn sie beim Nachbarn steht."""
    from shapely.geometry import Point
    import re

    muster = re.compile(r"^(?:W|GB|GS|IG)?(?:III|II|IV|VI|I|V|1|l)?(ogk|gk|gr|o|g)$")
    kandidaten = []
    for w in woerter:
        t = w.text.strip(".,;:'\"|")
        if len(t) > 1:
            t = t.replace("0", "o")
        m = muster.match(t)
        if m:
            d = math.hypot(w.x - x, w.y - y)
            im_gebiet = gebiet is not None and gebiet.buffer(3).contains(Point(w.x, w.y))
            if d <= radius or im_gebiet:
                kandidaten.append((d, m.group(1), w))
    if not kandidaten:
        return None, "keine Bauweisen-Beschriftung im Umkreis erkannt"
    # dieselbe Beschriftung wird in mehreren Drehungen gefunden: nach Stimmen gewichten
    stimmen: dict[str, float] = {}
    for d, bw, w in kandidaten:
        stimmen[bw] = stimmen.get(bw, 0) + w.sicherheit / (1 + d / 10)
    bester = max(stimmen, key=stimmen.get)
    d = min(d for d, bw, _ in kandidaten if bw == bester)
    return bester, (f"Bauweise „{bester}“ aus der Planbeschriftung gelesen "
                    f"({d:.0f} m vom Grundstück, innerhalb derselben Baufluchtlinien)")
