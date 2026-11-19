"""§ 75 BO für Wien: Bauklasseneinteilung und zulässige Gebäudehöhe.

Stand: idF LGBl. Nr. 69/2018.
"""

from __future__ import annotations

from enum import Enum

from ..herleitung import BO, Ergebnis, Quelle


class Bauklasse(Enum):
    I = 1
    II = 2
    III = 3
    IV = 4
    V = 5
    VI = 6


# Abs. 2: Mindest- und Höchsthöhe in Metern. Bauklasse VI hat keine
# gesetzliche Höchsthöhe; der Bebauungsplan legt zwei Grenzmaße fest.
HOEHENRAHMEN: dict[Bauklasse, tuple[float, float | None]] = {
    Bauklasse.I: (2.5, 9.0),
    Bauklasse.II: (2.5, 12.0),
    Bauklasse.III: (9.0, 16.0),
    Bauklasse.IV: (12.0, 21.0),
    Bauklasse.V: (16.0, 26.0),
    Bauklasse.VI: (21.0, None),
}

GARTENSIEDLUNG_MAX_HOEHE = 5.5  # Abs. 7


def hoehenrahmen(
    bauklasse: Bauklasse, grenzmasse_vi: tuple[float, float] | None = None
) -> Ergebnis[tuple[float, float]]:
    """Mindest- und Höchsthöhe nach Bauklasse (Abs. 2)."""
    mindest, hoechst = HOEHENRAHMEN[bauklasse]
    if bauklasse is Bauklasse.VI:
        if grenzmasse_vi is None:
            raise ValueError(
                "Bauklasse VI braucht die Grenzmaße aus dem Bebauungsplan."
            )
        mindest, hoechst = grenzmasse_vi
        begruendung = (
            f"Bauklasse VI: Grenzmaße laut Bebauungsplan {mindest}–{hoechst} m"
        )
    else:
        begruendung = f"Bauklasse {bauklasse.name}: {mindest}–{hoechst} m"
    return Ergebnis(
        wert=(mindest, hoechst),
        quellen=(Quelle(BO, "§ 75 Abs. 2"),),
        begruendung=begruendung,
    )


def hoehe_nach_strassenbreite(
    bauklasse: Bauklasse, fluchtlinienabstand: float
) -> Ergebnis[float]:
    """Höchsthöhe an der Baulinie oder Fluchtlinie nach Abs. 4.

    ``fluchtlinienabstand`` ist der Abstand der gegenüberliegenden
    Fluchtlinien in Metern; bei ungleichem Abstand das Mittel.
    """
    a = fluchtlinienabstand
    if a <= 0:
        raise ValueError("Fluchtlinienabstand muss positiv sein.")
    if bauklasse in (Bauklasse.I, Bauklasse.II):
        h, regel = a + 2.0, "Abstand + 2 m"
    elif bauklasse is Bauklasse.III:
        h, regel = a + 3.0, "Abstand + 3 m"
    elif bauklasse is Bauklasse.IV:
        if a <= 15.0:
            h, regel = a + 3.0, "Abstand + 3 m (bis 15 m Abstand)"
        else:
            h, regel = a + 4.0, "Abstand + 4 m (über 15 m Abstand)"
    else:
        h, regel = 2.0 * a, "doppelter Abstand"
    return Ergebnis(
        wert=h,
        quellen=(Quelle(BO, "§ 75 Abs. 4"),),
        begruendung=(
            f"Fluchtlinienabstand {a} m, Bauklasse {bauklasse.name}: {regel} = {h} m"
        ),
    )


def zulaessige_gebaeudehoehe(
    bauklasse: Bauklasse | None,
    *,
    fluchtlinienabstand: float | None = None,
    festgesetzte_hoehe: float | None = None,
    grenzmasse_vi: tuple[float, float] | None = None,
    schutzzone: bool = False,
    gartensiedlung: bool = False,
) -> Ergebnis[float]:
    """Zulässige Gebäudehöhe an der Straßenfront.

    Kombiniert Bauklasse (Abs. 2), eine im Bebauungsplan festgesetzte Höhe,
    die Begrenzung durch die Straßenbreite (Abs. 4, nicht in Schutzzonen,
    Abs. 6) und das Gartensiedlungsgebiet (Abs. 7).
    """
    kandidaten: list[tuple[float, str, Quelle]] = []
    hinweise: list[str] = []

    if gartensiedlung:
        kandidaten.append(
            (
                festgesetzte_hoehe or GARTENSIEDLUNG_MAX_HOEHE,
                "Gartensiedlungsgebiet",
                Quelle(BO, "§ 75 Abs. 7"),
            )
        )
    else:
        if bauklasse is None:
            raise ValueError("Bauklasse fehlt.")
        _, hoechst = hoehenrahmen(bauklasse, grenzmasse_vi).wert
        kandidaten.append(
            (hoechst, f"Bauklasse {bauklasse.name}", Quelle(BO, "§ 75 Abs. 2"))
        )
        if festgesetzte_hoehe is not None:
            kandidaten.append(
                (
                    festgesetzte_hoehe,
                    "im Bebauungsplan festgesetzte Höhe",
                    Quelle("Bebauungsplan", "Besondere Bestimmung"),
                )
            )
        if fluchtlinienabstand is not None:
            if schutzzone:
                hinweise.append(
                    "Schutzzone: Straßenbreite begrenzt die Höhe nicht (§ 75 Abs. 6)."
                )
            else:
                s = hoehe_nach_strassenbreite(bauklasse, fluchtlinienabstand)
                kandidaten.append((s.wert, "Straßenbreite", s.quellen[0]))

    hoehe, grund, _ = min(kandidaten, key=lambda k: k[0])
    return Ergebnis(
        wert=hoehe,
        quellen=tuple(dict.fromkeys(q for _, _, q in kandidaten)),
        begruendung=f"maßgeblich: {grund} mit {hoehe} m",
        hinweise=tuple(hinweise),
    )
