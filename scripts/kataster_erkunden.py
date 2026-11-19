"""Erkundung: BEV-Kataster Open Data (CC BY 4.0) – WFS/WMS des BEV-Geoservers, Dateien."""
import re, sys, urllib.request, urllib.parse, json
from pyproj import Transformer
sys.path.insert(0, "src")
from bebauungsstudie.daten import wien

def hole(url, n=None, methode="GET"):
    req = urllib.request.Request(url, headers={"User-Agent": "bebauungsstudie/0.1"}, method=methode)
    with urllib.request.urlopen(req, timeout=60) as r:
        if methode == "HEAD":
            return r.headers
        return r.read() if n is None else r.read(n)

def zeige(titel, url, n=4000):
    try:
        t = hole(url).decode("utf-8", "replace")
        print("KAT", titel, len(t), t[:n].replace("\n", " "), flush=True)
        return t
    except Exception as e:
        print("KAT", titel, "FEHLER", e, flush=True)
        return ""

G = "https://data.bev.gv.at/geoserver/"
for ws in ["BEVdataKAT/", ""]:
    cap = zeige("WFS-CAP " + ws, G + ws + "wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities", 300)
    print("KAT TYPEN", ws, re.findall(r"<(?:wfs:)?Name>([^<]+)</", cap)[:80], flush=True)
wms = zeige("WMS-CAP", G + "BEVdataKAT/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities", 300)
print("KAT WMS-LAYER", re.findall(r"<Name>([^<]+)</Name>", wms)[:80], flush=True)

t = wien.suche_adresse("Olbrichgasse 9, 1120 Wien")[0]
x, y = t.x, t.y
lx, ly = Transformer.from_crs(31256, 31287, always_xy=True).transform(x, y)
print("KAT PUNKT", x, y, lx, ly, flush=True)
for typ in re.findall(r"<(?:wfs:)?Name>([^<]+)</", zeige("dummy", G + "BEVdataKAT/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities", 0)):
    if "GST" in typ.upper() or "GRUND" in typ.upper():
        for srs, (px, py) in (("EPSG:31287", (lx, ly)), ("EPSG:31256", (x, y))):
            q = urllib.parse.urlencode({"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
                "TYPENAMES": typ, "COUNT": 5, "OUTPUTFORMAT": "application/json", "SRSNAME": srs,
                "BBOX": f"{px-15},{py-15},{px+15},{py+15},{srs}"})
            zeige(f"GETFEATURE {typ} {srs}", G + "BEVdataKAT/wfs?" + q, 3000)

for d in ["20261001", "20260401", "20251001", "20250401", "20241001", "20240401", "20231001", "20230401"]:
    for url in [f"https://data.bev.gv.at/download/Kataster/shp/{d}/KAT_DKM_Wien_SHP_{d}.zip",
                f"https://data.bev.gv.at/download/Kataster/gpkg/national/KAT_DKM_GST_epsg31287_{d}.gpkg"]:
        try:
            h = hole(url, methode="HEAD")
            print("KAT DATEI", url, h.get("Content-Length"), h.get("Accept-Ranges"), flush=True)
        except Exception as e:
            print("KAT DATEI", url, "FEHLER", e, flush=True)
