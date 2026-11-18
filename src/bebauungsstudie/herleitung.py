"""Nachvollziehbare Ergebnisse: jeder Wert mit Rechtsquelle und Begründung."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Quelle:
    """Rechtsquelle eines Werts, z. B. ``Quelle("BO für Wien", "§ 75 Abs. 2")``."""

    norm: str
    stelle: str

    def __str__(self) -> str:
        return f"{self.norm} {self.stelle}"


@dataclass(frozen=True)
class Ergebnis(Generic[T]):
    """Ein berechneter Wert mit seiner Herleitung."""

    wert: T
    quellen: tuple[Quelle, ...]
    begruendung: str
    hinweise: tuple[str, ...] = field(default=())

    def __str__(self) -> str:
        q = ", ".join(str(x) for x in self.quellen)
        return f"{self.wert} ({q}): {self.begruendung}"


BO = "BO für Wien"
WGARG = "WGarG 2008"
