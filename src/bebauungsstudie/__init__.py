"""Automatisierte Bebauungsstudien für Wien.

Jedes Ergebnis trägt seine Herleitung (Paragraph und Begründung), damit
Nutzer jede Zahl nachvollziehen können. Die Ergebnisse sind eine
Vorabschätzung und ersetzen keine Prüfung durch die Behörde.
"""

from .studie import Annahmen, Bauplatz, Studie, erstelle_studie

__all__ = ["Annahmen", "Bauplatz", "Studie", "erstelle_studie"]
