"""Stellplatzverpflichtung nach Wiener Garagengesetz 2008 (§§ 48, 50)."""

from __future__ import annotations

import math

from ..herleitung import WGARG, Ergebnis, Quelle

M2_JE_STELLPLATZ = 100.0


def pflichtstellplaetze(
    wohnnutzflaeche_m2: float,
    regulativ_prozent: float = 100.0,
    kleinhaus_eine_wohnung: bool = False,
) -> Ergebnis[int]:
    """Pflichtstellplätze für Wohnnutzung.

    Regelbedarf ein Stellplatz je volle 100 m² Wohnnutzfläche. Ein
    Stellplatzregulativ im Bebauungsplan kann den Bedarf auf 10 % bis
    110 % ändern.
    """
    if kleinhaus_eine_wohnung:
        return Ergebnis(
            0,
            (Quelle(WGARG, "§ 50"),),
            "Kleinhaus mit nur einer Wohneinheit: keine Stellplatzpflicht",
        )
    if not 10.0 <= regulativ_prozent <= 110.0:
        raise ValueError("Stellplatzregulativ muss zwischen 10 % und 110 % liegen.")
    regel = math.floor(wohnnutzflaeche_m2 / M2_JE_STELLPLATZ)
    pflicht = math.floor(regel * regulativ_prozent / 100.0)
    quellen = (Quelle(WGARG, "§ 50"),)
    hinweise: tuple[str, ...] = ()
    if regulativ_prozent != 100.0:
        quellen += (Quelle(WGARG, "§ 48 (Stellplatzregulativ)"),)
        hinweise = ("Rundung bei Stellplatzregulativ mit der MA 37 abklären.",)
    return Ergebnis(
        pflicht,
        quellen,
        (
            f"{wohnnutzflaeche_m2:.0f} m² WNF / 100 = {regel} Regelbedarf, "
            f"× {regulativ_prozent:.0f} % = {pflicht}"
        ),
        hinweise,
    )
