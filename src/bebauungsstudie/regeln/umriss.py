"""§ 81 BO für Wien: Gebäudeumriss und Dach.

Stand: in Kraft seit 14.12.2023.
"""

from __future__ import annotations

import math

from ..herleitung import BO, Ergebnis, Quelle
from .bauklassen import Bauklasse

UMRISS_WINKEL = 45.0  # Abs. 4
UMRISS_WINKEL_GARTENSIEDLUNG = 25.0
DACH_UEBER_GH_KLEIN = 4.5  # Abs. 1: Bauklasse I, offen/gekuppelt, Wohngebiet
DACH_UEBER_GH = 7.5


def umrisswinkel(
    gartensiedlung: bool = False, dachneigung: float | None = None
) -> Ergebnis[float]:
    """Winkel des Gebäudeumrisses über der Gebäudehöhe (Abs. 4)."""
    if dachneigung is not None:
        return Ergebnis(
            dachneigung,
            (Quelle("Bebauungsplan", "Dachneigung"),),
            f"im Bebauungsplan festgesetzte Dachneigung {dachneigung}°",
        )
    w = UMRISS_WINKEL_GARTENSIEDLUNG if gartensiedlung else UMRISS_WINKEL
    return Ergebnis(w, (Quelle(BO, "§ 81 Abs. 4"),), f"Regelwinkel {w}°")


def max_dachhoehe(
    bauklasse: Bauklasse | None, bauweise: str, wohngebiet: bool = True
) -> Ergebnis[float]:
    """Höhe des obersten Dachabschlusses über der zulässigen Gebäudehöhe (Abs. 1)."""
    klein = (
        bauklasse is Bauklasse.I and bauweise in ("o", "gk", "ogk") and wohngebiet
    )
    h = DACH_UEBER_GH_KLEIN if klein else DACH_UEBER_GH
    return Ergebnis(
        h,
        (Quelle(BO, "§ 81 Abs. 1"),),
        f"oberster Dachabschluss höchstens {h} m über der Gebäudehöhe",
    )


def dachgeschosse(
    trakttiefe: float,
    winkel: float,
    max_dach: float,
    geschosshoehe: float,
    lichte_hoehe: float = 2.5,
    mindestbreite: float = 3.0,
) -> Ergebnis[list[float]]:
    """Nutzbare Breite je Dachgeschoß im Umriss, beidseitig ansteigend.

    Näherung: Ein Dachgeschoß zählt nur in der Breite, in der die lichte
    Raumhöhe ganz unter dem Umriss liegt; schmäler als ``mindestbreite``
    zählt nicht. Liefert die Breiten je Geschoß
    von unten nach oben.
    """
    tan = math.tan(math.radians(winkel))
    breiten: list[float] = []
    z = 0.0
    while z + lichte_hoehe <= max_dach + 1e-9:
        b = trakttiefe - 2 * (z + lichte_hoehe) / tan
        if b < mindestbreite:
            break
        breiten.append(round(b, 2))
        z += geschosshoehe
    return Ergebnis(
        breiten,
        (Quelle(BO, "§ 81 Abs. 1, 4"),),
        (
            f"Trakttiefe {trakttiefe} m, Umriss {winkel}°, bis {max_dach} m über GH: "
            f"{len(breiten)} Dachgeschoß(e)"
        ),
        hinweise=("Dachaufbauten nach § 81 Abs. 6 nicht berücksichtigt.",),
    )
