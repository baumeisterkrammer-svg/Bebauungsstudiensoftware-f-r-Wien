"""Erkundung: Grundstück und Nutzungsflächen am Adresspunkt aus der BEV-DKM."""
import sys, time
sys.path.insert(0, "src")
from bebauungsstudie.daten import kataster
X, Y = -2309.34, 336954.0  # Olbrichgasse 9
t0 = time.time()
g = kataster.grundstueck_am_punkt(X, Y)
print("KAT ERG", round(time.time() - t0, 1), g.kg, g.gnr, round(g.flaeche, 1), len(g.punkte), g.punkte, g.strassenkanten, g.protokoll, flush=True)
st, url = kataster.aktuelle_datei()
lx, ly = kataster.NACH_LAMBERT.transform(X, Y)
for a, geom in kataster._lies(url, "NFL", (lx - 40, ly - 40, lx + 40, ly + 40)):
    print("KAT NFL", a, round(geom.area, 1), round(geom.distance(kataster.Point(lx, ly)), 1), flush=True)
for a, geom in kataster._lies(url, "GST", (lx - 30, ly - 30, lx + 30, ly + 30)):
    print("KAT NACHBAR", a.get("GNR"), round(geom.area, 1), round(geom.distance(kataster.Point(lx, ly)), 1), flush=True)
