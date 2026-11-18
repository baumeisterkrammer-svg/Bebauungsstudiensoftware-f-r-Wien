"""§ 79 BO für Wien: Vorgärten, Abstandsflächen, gärtnerische Ausgestaltung.

Stand: in Kraft seit 13.03.2024.
"""

from __future__ import annotations

import math

from ..herleitung import BO, Ergebnis, Quelle
from .bauklassen import Bauklasse

VORGARTEN_TIEFE = 5.0  # Abs. 1

# Abs. 3: Abstand von den Nachbargrenzen in der offenen Bauweise (m)
ABSTAND_OFFEN: dict[Bauklasse, float] = {
    Bauklasse.I: 6.0,
    Bauklasse.II: 6.0,
    Bauklasse.III: 12.0,
    Bauklasse.IV: 14.0,
    Bauklasse.V: 16.0,
    Bauklasse.VI: 20.0,
}

# Abs. 3: Bebaute Fläche, die über die Abstandslinie ragen darf (m²),
# je Front und je Bauplatz
UEBERSCHREITUNG_JE_FRONT: dict[Bauklasse, float] = {
    Bauklasse.I: 45.0,
    Bauklasse.II: 45.0,
    Bauklasse.III: 90.0,
    Bauklasse.IV: 105.0,
    Bauklasse.V: 120.0,
    Bauklasse.VI: 150.0,
}
UEBERSCHREITUNG_JE_BAUPLATZ: dict[Bauklasse, float] = {
    k: 2 * v for k, v in UEBERSCHREITUNG_JE_FRONT.items()
}

UNVERSIEGELT_ANTEIL = 2 / 3  # Abs. 6
FLAECHE_JE_BAUM = 200.0  # Abs. 7


def abstand_nachbargrenze(bauklasse: Bauklasse) -> Ergebnis[float]:
    """Regelabstand von der Nachbargrenze in offener Bauweise (Abs. 3)."""
    a = ABSTAND_OFFEN[bauklasse]
    return Ergebnis(
        wert=a,
        quellen=(Quelle(BO, "§ 79 Abs. 3"),),
        begruendung=f"offene Bauweise, Bauklasse {bauklasse.name}: {a} m",
        hinweise=(
            "Heranrücken bis zur Hälfte des Abstands und Überschreitungsflächen "
            f"bis {UEBERSCHREITUNG_JE_FRONT[bauklasse]} m² je Front sind möglich, "
            "in dieser Version aber nicht ausgenutzt (konservativ).",
        ),
    )


def vorgarten_tiefe(festgesetzt: float | None = None) -> Ergebnis[float]:
    """Tiefe des Vorgartens (Abs. 1): 5 m, wenn der Plan nichts anderes sagt."""
    if festgesetzt is not None:
        return Ergebnis(
            wert=festgesetzt,
            quellen=(Quelle("Bebauungsplan", "Vorgartentiefe"),),
            begruendung=f"im Bebauungsplan festgesetzt: {festgesetzt} m",
        )
    return Ergebnis(
        wert=VORGARTEN_TIEFE,
        quellen=(Quelle(BO, "§ 79 Abs. 1"),),
        begruendung=f"Regeltiefe {VORGARTEN_TIEFE} m",
    )


def mindest_unversiegelt(freiflaeche_m2: float) -> Ergebnis[float]:
    """Mindestens unversiegelte, begrünte Fläche von Vorgarten und Abstandsflächen."""
    wert = round(freiflaeche_m2 * UNVERSIEGELT_ANTEIL, 1)
    return Ergebnis(
        wert=wert,
        quellen=(Quelle(BO, "§ 79 Abs. 6"),),
        begruendung=f"2/3 von {freiflaeche_m2:.1f} m² = {wert} m²",
    )


def baeume(gartenflaeche_m2: float) -> Ergebnis[int]:
    """Anzahl zu pflanzender Bäume: einer je angefangene 200 m² (Abs. 7)."""
    n = math.ceil(gartenflaeche_m2 / FLAECHE_JE_BAUM) if gartenflaeche_m2 > 0 else 0
    return Ergebnis(
        wert=n,
        quellen=(Quelle(BO, "§ 79 Abs. 7"),),
        begruendung=f"{gartenflaeche_m2:.1f} m² / 200 m², aufgerundet = {n}",
        hinweise=("Gilt, wenn der Bebauungsplan gärtnerische Ausgestaltung vorsieht.",),
    )
