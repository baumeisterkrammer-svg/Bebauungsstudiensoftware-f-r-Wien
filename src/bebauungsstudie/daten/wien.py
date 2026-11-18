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


def _hole(url: str, params: dict, timeout: float = 60) -> bytes:
    voll = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(voll, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


@dataclass
class Adresstreffer:
    text: str
    x: float
    y: float
    roh: dict


def suche_adresse(adresse: str) -> list[Adresstreffer]:
    """Adresse in Koordinaten (EPSG:31256) umwandeln."""
    daten = json.loads(_hole(ADRESSE, {"Address": adresse, "crs": CRS}))
    treffer = []
    for f in daten.get("features", []):
        x, y = f["geometry"]["coordinates"][:2]
        props = f.get("properties", {})
        text = props.get("Adresse") or props.get("Address") or adresse
        treffer.append(Adresstreffer(str(text), float(x), float(y), f))
    return treffer


def layer_liste() -> list[tuple[str, str]]:
    """Alle WFS-Layer als (Name, Titel)."""
    xml = _hole(WFS, {"service": "WFS", "request": "GetCapabilities",
                      "version": "1.1.0"}).decode("utf-8", "replace")
    out = []
    for block in re.findall(r"<(?:wfs:)?FeatureType>(.*?)</(?:wfs:)?FeatureType>", xml, re.S):
        name = re.search(r"<(?:wfs:)?Name>(.*?)</", block)
        titel = re.search(r"<(?:wfs:)?Title>(.*?)</", block)
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
