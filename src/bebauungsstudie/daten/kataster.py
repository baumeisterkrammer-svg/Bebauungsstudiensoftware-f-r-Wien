"""Grundstück zur Adresse aus der Digitalen Katastralmappe (DKM) des BEV.

Quelle: BEV – Kataster Grafik Grundstücksverzeichnis GPKG, Stichtagsdaten,
Lizenz CC BY 4.0 (https://data.bev.gv.at). Die österreichweite GeoPackage-
Datei (rund 35 GB) wird nicht geladen: GDAL liest über HTTP-Range-Anfragen
nur die Seiten des räumlichen Index und die Grundstücke am Punkt.

Geometrien liegen in EPSG:31287 (MGI / Austria Lambert) und werden nach
EPSG:31256 (MGI / Austria GK East) umgerechnet, wie die Stadt-Wien-Daten.

Straßenkanten: Für jede Grundstückskante wird ein Punkt 1,5 m außerhalb der
Kantenmitte geprüft. Liegt er in einer Nutzungsfläche (NFL) mit Straßen-
nutzung, gilt die Kante als Straßenkante. Das ersetzt nicht die Baulinie
aus dem Bebauungsplan, ist aber für die Vorabschätzung meist zutreffend.
"""

from __future__ import annotations

import datetime as dt
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache

from pyproj import Transformer
from shapely import from_wkb
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import transform

BASIS = "https://data.bev.gv.at/download/Kataster/gpkg/national/KAT_DKM_GST_epsg31287_{d}.gpkg"
NACH_LAMBERT = Transformer.from_crs(31256, 31287, always_xy=True)
NACH_GK = Transformer.from_crs(31287, 31256, always_xy=True)

# Nutzungen der DKM (Feld NS, BEV-Schnittstelle Katastralmappe, Tabelle 8)
NUTZUNG = {"41": "Gebäude", "42": "Parkplatz", "52": "Garten", "63": "Betriebsfläche",
           "65": "Verkehrsrandfläche", "83": "Gebäudenebenfläche", "92": "Schiene",
           "95": "Straßenverkehrsanlage", "96": "Erholungsfläche"}
STRASSEN_NS = {"95", "65"}


@dataclass
class Grundstueck:
    kg: str
    gnr: str
    umriss: Polygon
    """In EPSG:31256, gegen den Uhrzeigersinn, ohne Bögen."""
    strassenkanten: set[int] = field(default_factory=set)
    nachbarn: list[tuple[str, float]] = field(default_factory=list)
    """Angrenzende Grundstücke (Nummer, Fläche m²), ohne Straßen."""
    nutzungen: dict[str, float] = field(default_factory=dict)
    """Nutzungsanteile im Grundstück in m²."""
    stichtag: str = ""
    protokoll: list[str] = field(default_factory=list)

    @property
    def flaeche(self) -> float:
        return self.umriss.area

    @property
    def punkte(self) -> list[tuple[float, float]]:
        return [(round(x, 3), round(y, 3)) for x, y in self.umriss.exterior.coords[:-1]]


def _stichtage(heute: dt.date | None = None) -> list[str]:
    """Mögliche Stichtage (1.4. und 1.10.), der neueste zuerst."""
    heute = heute or dt.date.today()
    tage = []
    for jahr in range(heute.year, heute.year - 3, -1):
        for monat in (10, 4):
            d = dt.date(jahr, monat, 1)
            if d <= heute:
                tage.append(d.strftime("%Y%m%d"))
    return tage


@lru_cache(maxsize=1)
def aktuelle_datei() -> tuple[str, str]:
    """(Stichtag, URL) der neuesten verfügbaren DKM-Datei."""
    for d in _stichtage():
        url = BASIS.format(d=d)
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "bebauungsstudie/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return d, url
        except Exception:
            continue
    raise LookupError("Keine DKM-Datei des BEV erreichbar")


def _lies(url: str, layer: str, bbox: tuple[float, float, float, float]) -> list[tuple[dict, object]]:
    import pyogrio

    meta, _, geom, felder = pyogrio.raw.read("/vsicurl/" + url, layer=layer, bbox=bbox)
    namen = list(meta["fields"])
    return [({n: (str(felder[j][i]) if felder[j][i] is not None else None) for j, n in enumerate(namen)},
             from_wkb(geom[i])) for i in range(len(geom))]


def _in_gk(g):
    return transform(lambda x, y, z=None: NACH_GK.transform(x, y), g)


def _vereinfache(poly: Polygon) -> Polygon:
    """Bögen der DKM sind fein segmentiert; auf 5 cm vereinfachen."""
    p = poly.simplify(0.05, preserve_topology=True)
    return orient(p if isinstance(p, Polygon) else poly, sign=1.0)


def ist_strasse(attribute: dict) -> bool:
    return (attribute.get("NS") or "").strip() in STRASSEN_NS


def strassenkanten(umriss: Polygon, nutzungen: list[tuple[dict, Polygon]], abstand: float = 1.5) -> set[int]:
    kanten = set()
    ring = list(umriss.exterior.coords)
    for i in range(len(ring) - 1):
        (x0, y0), (x1, y1) = ring[i], ring[i + 1]
        lang = LineString([(x0, y0), (x1, y1)]).length
        if lang < 0.5:
            continue
        # Außennormale bei Umlauf gegen den Uhrzeigersinn: (dy, -dx)
        nx, ny = (y1 - y0) / lang, -(x1 - x0) / lang
        p = Point((x0 + x1) / 2 + nx * abstand, (y0 + y1) / 2 + ny * abstand)
        if any(ist_strasse(a) and g.contains(p) for a, g in nutzungen):
            kanten.add(i)
    return kanten


def grundstueck_am_punkt(x: float, y: float, weitere: tuple[str, ...] = ()) -> Grundstueck:
    """Grundstück, in dem der Punkt (EPSG:31256) liegt.

    `weitere`: Nummern weiterer Grundstücke derselben KG, die zum Bauplatz
    gehören (z. B. ("453/16",)); sie werden mit dem ersten vereinigt."""
    stichtag, url = aktuelle_datei()
    lx, ly = NACH_LAMBERT.transform(x, y)
    kandidaten = _lies(url, "GST", (lx - 5, ly - 5, lx + 5, ly + 5))
    if not kandidaten:
        raise LookupError("Kein Grundstück am Adresspunkt gefunden")
    p = Point(lx, ly)
    kandidaten.sort(key=lambda ag: (not ag[1].contains(p), ag[1].distance(p)))
    attr, geom = kandidaten[0]
    gnr = attr.get("GNR") or ""
    if weitere:
        from shapely.ops import unary_union
        teile = [geom] + [g for a, g in _lies(url, "GST", (lx - 150, ly - 150, lx + 150, ly + 150))
                          if a.get("GNR") in weitere and a.get("KG") == attr.get("KG")]
        geom = unary_union([t.buffer(0.01) for t in teile]).buffer(-0.01)
        gnr = ", ".join([gnr] + [w for w in weitere])
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    umriss = _vereinfache(_in_gk(geom))
    gst = Grundstueck(kg=attr.get("KG") or "", gnr=gnr, umriss=umriss, stichtag=stichtag)
    gst.protokoll.append(
        f"Kataster: KG {gst.kg}, Gst. {gst.gnr}, {gst.flaeche:.0f} m² "
        f"(BEV DKM Stichtag {stichtag[6:]}.{stichtag[4:6]}.{stichtag[:4]}, CC BY 4.0)")
    if not geom.contains(p):
        gst.protokoll.append("Kataster: Adresspunkt liegt nicht im Grundstück, nächstes gewählt")

    minx, miny, maxx, maxy = geom.bounds
    box = (minx - 3, miny - 3, maxx + 3, maxy + 3)
    try:
        nfl = [(a, _in_gk(g)) for a, g in _lies(url, "NFL", box)]
        gst.strassenkanten = strassenkanten(umriss, nfl)
        for a, g in nfl:
            teil = g.intersection(umriss).area
            if teil > 0.5:
                name = NUTZUNG.get(a.get("NS") or "", a.get("NS") or "?")
                gst.nutzungen[name] = round(gst.nutzungen.get(name, 0) + teil, 1)
        strassen = [g for a, g in nfl if ist_strasse(a)]
        for a, g in _lies(url, "GST", box):
            g = _in_gk(g)
            if a.get("GNR") in gst.gnr.split(", ") or g.intersection(umriss.buffer(0.2)).area < 0.5:
                continue
            if any(g.intersection(s_).area > 0.5 * g.area for s_ in strassen):
                continue
            gst.nachbarn.append((a.get("GNR") or "?", round(g.area, 1)))
        gst.protokoll.append(
            "Kataster: Nutzung " + ", ".join(f"{k} {v:.0f} m²" for k, v in gst.nutzungen.items())
            + f"; Straßenkanten {sorted(gst.strassenkanten) or 'keine erkannt'}"
            + "; Nachbargrundstücke " + ", ".join(f"{n} ({f:.0f} m²)" for n, f in gst.nachbarn))
        if (gst.nutzungen.get("Gebäude", 0) > 0.8 * gst.flaeche and not gst.strassenkanten
                and len(gst.nachbarn) == 1 and not weitere):
            n = gst.nachbarn[0][0]
            gst2 = grundstueck_am_punkt(x, y, (n,))
            gst2.protokoll = gst.protokoll + [
                f"Kataster: Grundstück {gst.gnr} ist überbaut und grenzt nicht an die Straße; "
                f"mit dem einzigen Nachbargrundstück {n} zum Bauplatz zusammengelegt (bitte prüfen)."
            ] + gst2.protokoll[1:]
            return gst2
        if gst.nutzungen.get("Gebäude", 0) > 0.8 * gst.flaeche:
            gst.protokoll.append(
                "Kataster: Das Grundstück am Adresspunkt ist fast ganz überbaut. Der Bauplatz "
                "umfasst vermutlich weitere Grundstücke derselben Einlagezahl; bitte prüfen.")
    except Exception as e:
        gst.protokoll.append(f"Kataster: Nutzungsflächen nicht abrufbar ({type(e).__name__}: {e})")
    return gst
