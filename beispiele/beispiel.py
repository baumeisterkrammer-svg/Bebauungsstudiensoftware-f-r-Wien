"""Beispiel: Eckbauplatz 40 × 50 m, Bauklasse III, offene Bauweise."""

from bebauungsstudie import Annahmen, Bauplatz, erstelle_studie
from bebauungsstudie.regeln.bauklassen import Bauklasse

bauplatz = Bauplatz(
    umriss=[(0, 0), (40, 0), (40, 50), (0, 50)],
    strassenkanten={0},
    bauklasse=Bauklasse.III,
    bauweise="o",
    fluchtlinienabstand=12.0,
)
print(erstelle_studie(bauplatz, Annahmen(trakttiefe=12.0)).bericht())
