"""Erkundung: BEV-Kataster – GetFeatureInfo am WMS und Fernlesen des GPKG."""
import sys, time, urllib.request, urllib.parse, json
X, Y = 620682.254, 478847.421  # Olbrichgasse 9 in EPSG:31287

def hole(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bebauungsstudie/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")

for fmt in ["application/json", "text/plain"]:
    q = urllib.parse.urlencode({"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetFeatureInfo",
        "LAYERS": "DKM_GST", "QUERY_LAYERS": "DKM_GST", "CRS": "EPSG:31287",
        "BBOX": f"{X-50},{Y-50},{X+50},{Y+50}", "WIDTH": 101, "HEIGHT": 101, "I": 50, "J": 50,
        "INFO_FORMAT": fmt, "FEATURE_COUNT": 3, "STYLES": "", "FORMAT": "image/png"})
    try:
        t = hole("https://data.bev.gv.at/geoserver/BEVdataKAT/wms?" + q)
        print("KAT GFI", fmt, len(t), t[:3000].replace("\n", " "), flush=True)
    except Exception as e:
        print("KAT GFI", fmt, "FEHLER", e, flush=True)

try:
    import pyogrio
    from shapely import from_wkb
    t0 = time.time()
    url = "/vsicurl/https://data.bev.gv.at/download/Kataster/gpkg/national/KAT_DKM_GST_epsg31287_20261001.gpkg"
    print("KAT LAYERS", pyogrio.list_layers(url).tolist(), round(time.time() - t0, 1), flush=True)
    meta, _, geom, felder = pyogrio.raw.read(url, layer="GST", bbox=(X - 5, Y - 5, X + 5, Y + 5))
    zeilen = [dict(zip(meta["fields"], [f[i] for f in felder])) for i in range(len(geom))]
    print("KAT GST", round(time.time() - t0, 1), meta["crs"], zeilen, [from_wkb(g).wkt[:500] for g in geom], flush=True)
    t1 = time.time()
    w = " OR ".join(f"(KGNR='{z['KG']}' AND GSTNR='{z['GNR']}')" for z in zeilen)
    meta2, _, _, f2 = pyogrio.raw.read(url, layer="Grundstuecksverzeichnis", read_geometry=False, where=w)
    print("KAT GV", round(time.time() - t1, 1), meta2["fields"].tolist(), [list(map(str, c)) for c in f2], flush=True)
except Exception as e:
    print("KAT GPKG FEHLER", repr(e), flush=True)
