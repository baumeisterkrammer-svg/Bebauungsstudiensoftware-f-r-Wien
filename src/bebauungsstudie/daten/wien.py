"""Zugriff auf die offenen Geodaten der Stadt Wien (data.wien.gv.at).

Datenquelle: Stadt Wien – https://data.wien.gv.at (CC BY 4.0).
Die Daten sind nicht rechtsverbindlich; verbindlich sind die Plandokumente.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASIS = "https://data.wien.gv.at"
WFS = f"{BASIS}/daten/geo"
ADRESSE = f"{BASIS}/daten/OGDAddressService/rest/AddressSearch"
CRS = "EPSG:31256"  # MGI / Austria GK East, Meter
USER_AGENT = "bebauungsstudie/0.1"


def _hole(url: str, params: dict, timeout: float = 20, versuche: int = 3) -> bytes:
    """GET mit Wiederholung bei Serverfehlern (5xx) und Zeitüberschreitung."""
    import time
    import urllib.error

    voll = f"{url}?{urllib.parse.urlencode(params)}"
    for i in range(versuche):
        req = urllib.request.Request(voll, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == versuche - 1:
                try:
                    text = e.read()[:300].decode("utf-8", "replace")
                except Exception:
                    text = ""
                raise RuntimeError(f"HTTP {e.code} von {url}: {' '.join(text.split())}") from e
        except (TimeoutError, urllib.error.URLError):
            if i == versuche - 1:
                raise
        time.sleep(3 * (i + 1))
    raise RuntimeError("unerreichbar")


@dataclass
class Adresstreffer:
    text: str
    x: float
    y: float
    roh: dict


def _wien_adresse(adresse: str) -> list[Adresstreffer]:
    daten = json.loads(_hole(ADRESSE, {"Address": adresse, "crs": CRS}))
    treffer = []
    for f in daten.get("features", []):
        x, y = f["geometry"]["coordinates"][:2]
        props = f.get("properties", {})
        text = props.get("Adresse") or props.get("Address") or adresse
        treffer.append(Adresstreffer(str(text), float(x), float(y), f))
    return treffer


def _osm_adresse(adresse: str) -> list[Adresstreffer]:
    """Ersatz: OpenStreetMap Nominatim, Ergebnis nach EPSG:31256 umgerechnet."""
    from pyproj import Transformer

    daten = json.loads(_hole("https://nominatim.openstreetmap.org/search",
                             {"q": adresse, "format": "json", "limit": "3",
                              "countrycodes": "at"}))
    tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    treffer = []
    for d in daten:
        x, y = tr.transform(float(d["lon"]), float(d["lat"]))
        treffer.append(Adresstreffer(d.get("display_name", adresse), x, y, d))
    return treffer


def suche_adresse(adresse: str, protokoll: list[str] | None = None) -> list[Adresstreffer]:
    """Adresse in Koordinaten (EPSG:31256) umwandeln.

    Zuerst der Adressdienst der Stadt Wien, bei Fehler OpenStreetMap.
    """
    for name, fn in (("Stadt Wien", _wien_adresse), ("OpenStreetMap", _osm_adresse)):
        try:
            treffer = fn(adresse)
        except Exception as e:  # nächsten Dienst versuchen
            if protokoll is not None:
                protokoll.append(f"Adresssuche {name}: {type(e).__name__}: {e}")
            continue
        if treffer:
            if protokoll is not None:
                protokoll.append(f"Adresssuche {name}: {len(treffer)} Treffer")
            return treffer
    return []


def layer_liste() -> list[tuple[str, str]]:
    """Alle WFS-Layer als (Name, Titel)."""
    xml = _hole(WFS, {"service": "WFS", "request": "GetCapabilities",
                      "version": "1.1.0"}).decode("utf-8", "replace")
    out = []
    for block in re.findall(r"<(?:\w+:)?FeatureType\b[^>]*>(.*?)</(?:\w+:)?FeatureType>", xml, re.S):
        name = re.search(r"<(?:\w+:)?Name>(.*?)</", block)
        titel = re.search(r"<(?:\w+:)?Title>(.*?)</", block)
        if name:
            out.append((name.group(1), titel.group(1) if titel else ""))
    return out


def features(layer: str, x: float, y: float, radius: float = 30.0,
             max_features: int = 200) -> dict:
    """Features eines Layers im Quadrat um einen Punkt als GeoJSON."""
    bbox = f"{x - radius},{y - radius},{x + radius},{y + radius},{CRS}"
    roh = _hole(WFS, {
        "service": "WFS", "request": "GetFeature", "version": "1.1.0",
        "typeName": layer, "srsName": CRS, "outputFormat": "json",
        "bbox": bbox, "maxFeatures": str(max_features),
    })
    return json.loads(roh)
