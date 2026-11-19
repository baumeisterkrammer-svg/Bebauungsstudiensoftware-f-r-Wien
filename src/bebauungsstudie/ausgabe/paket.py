"""Alle Ausgaben einer Studie in einen Ordner schreiben."""

from __future__ import annotations

from pathlib import Path

from ..modell import erzeuge_modell
from ..studie import Studie
from .dxf import exportiere_dxf
from .ifc import exportiere_ifc
from .plaene import exportiere_plaene


def exportiere_alles(studie: Studie, ordner: str | Path) -> list[Path]:
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    mm = erzeuge_modell(studie)
    dateien = exportiere_plaene(studie, mm, ordner)
    dateien.append(exportiere_ifc(studie, mm, ordner / "modell.ifc"))
    dateien.append(exportiere_dxf(studie, mm, ordner / "plaene.dxf"))
    bericht = ordner / "bericht.txt"
    bericht.write_text(studie.bericht(), encoding="utf-8")
    dateien.append(bericht)
    return dateien
