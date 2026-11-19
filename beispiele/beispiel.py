"""Beispiel: Bauplatz 40 × 50 m, Bauklasse III, offene Bauweise.

Erzeugt Bericht, Pläne (PDF/PNG), BIM-Modell (IFC) und DXF in ./ausgabe.
"""

import sys

from bebauungsstudie import Bauplatz, erstelle_studie
from bebauungsstudie.ausgabe.paket import exportiere_alles
from bebauungsstudie.regeln.bauklassen import Bauklasse

bauplatz = Bauplatz(
    umriss=[(0, 0), (40, 0), (40, 50), (0, 50)],
    strassenkanten={0},
    bauklasse=Bauklasse.III,
    bauweise="o",
    fluchtlinienabstand=12.0,
)
studie = erstelle_studie(bauplatz)
print(studie.bericht())
ordner = sys.argv[1] if len(sys.argv) > 1 else "ausgabe"
for pfad in exportiere_alles(studie, ordner):
    print("geschrieben:", pfad)
