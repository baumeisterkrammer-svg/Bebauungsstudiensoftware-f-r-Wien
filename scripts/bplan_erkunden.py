"""Erkundung 3: WMTS Flächenwidmungs- und Bebauungsplan, Plandokument-WMS, Plandokument-Texte."""
import re, html, json, urllib.request, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 (bebauungsstudie/0.1)"}
X, Y = -2309.34, 336954.0  # Olbrichgasse 9, EPSG:31256

def hole(url, t=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r:
        return r.read().decode("utf-8", "replace"), r.geturl(), r.headers.get("Content-Type")

def zeige(titel, url, n=2500):
    try:
        t, u, ct = hole(url)
        print("BP", titel, ct, len(t), re.sub(r"\s+", " ", t[:n]), flush=True)
        return t
    except Exception as e:
        print("BP", titel, "FEHLER", url, e, flush=True); return ""

for ds in ["stadt-wien_flchenwidmungsundbebauungsplanwien", "0adc90c9-ac6b-47ef-aa83-b7780594720c",
           "1039ed7e-97fb-435f-b6cc-f6a105ba5e09", "4111e2d8-1729-4953-899a-c55bc382857e",
           "a14e57c4-ea1c-4a7a-863a-b874ccf23790", "a73c5b74-a9c9-4caa-a796-e4c832645614",
           "dc82da19-6878-46e8-a653-4966fa4dd108", "e4079286-310c-435a-af2d-64604ba9ade5",
           "ee97fa6e-e96c-4f37-ae3f-26b2ed3ada0d"]:
    t = zeige("DS " + ds, "https://www.data.gv.at/katalog/dataset/" + ds, 0)
    titel = re.search(r"<title>([^<]+)", t)
    urls = sorted({u for u in re.findall(r'(https?://[^"\'<> ]+)', html.unescape(t))
                   if re.search(r"wmts|wms|wfs|WMTS|WMS|WFS|data\.wien|\.zip|\.pdf|\.json|\.xml", u) and "data.gv.at/assets" not in u})
    print("BP DS-INFO", ds, titel.group(1).strip() if titel else "", urls[:25], flush=True)

cap = zeige("WMTS-CAP", "https://mapsneu.wien.gv.at/wmtsneu/1.0.0/WMTSCapabilities.xml", 0) or \
      zeige("WMTS-CAP2", "https://maps.wien.gv.at/wmts/1.0.0/WMTSCapabilities.xml", 0)
ids = re.findall(r"<ows:Identifier>([^<]+)</ows:Identifier>", cap)
print("BP WMTS-IDS", len(ids), [i for i in ids if re.search(r"flw|widm|bebau|plan|fmzk", i, re.I)][:60], flush=True)
for m in re.finditer(r"<ResourceURL[^>]+>", cap):
    if re.search(r"flw|widm|bebau", m.group(0), re.I):
        print("BP WMTS-RES", m.group(0), flush=True); break

for base in ["https://data.wien.gv.at/daten/geo", "https://data.wien.gv.at/daten/wms"]:
    t = zeige("WMS-CAP " + base, base + "?service=WMS&request=GetCapabilities&version=1.3.0", 0)
    print("BP WMS-LAYER", base, [n for n in re.findall(r"<Name>([^<]+)</Name>", t) if re.search(r"PLAN|FLW|WIDM|BEBAU|FLUCHT", n, re.I)][:40], flush=True)
