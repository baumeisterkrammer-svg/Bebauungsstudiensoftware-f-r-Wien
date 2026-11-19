"""Erkundung 2: Plan-Viewer-Endpunkte, WMTS, Plandokument-WMS."""
import re, html, json, urllib.request, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 (bebauungsstudie/0.1)"}
X, Y = -2309.34, 336954.0  # Olbrichgasse 9, EPSG:31256

def hole(url, t=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r:
        return r.read().decode("utf-8", "replace"), r.geturl(), r.headers.get("Content-Type")

def zeige(titel, url, n=3000):
    try:
        t, u, ct = hole(url)
        print("BP", titel, ct, len(t), re.sub(r"\s+", " ", t[:n]), flush=True)
        return t
    except Exception as e:
        print("BP", titel, "FEHLER", e, flush=True); return ""

js = zeige("CTRL", "https://www.wien.gv.at/flaechenwidmung/public/ControlScript.ctrl?r=", 0)
for m in sorted(set(re.findall(r"""["']([^"'\s]{0,80}(?:\.aspx|\.ashx|\.ctrl|\.asmx|\.svc|wmts|WMTS|wms|WMS|Info|info|Abfrage|abfrage|GetFeature|tile|Tile)[^"'\s]{0,120})["']""", js)))[:200]:
    print("BP JS-URL", m, flush=True)
for kw in ["InfoAbfrage", "infoabfrage", "getInfo", "GetInfo", "featureinfo", "FeatureInfo", "Bauweise", "Fluchtlinie", "plandokument", "Plandokument"]:
    for m in list(re.finditer(kw, js))[:3]:
        print("BP JS-KONTEXT", kw, re.sub(r"\s+", " ", js[max(0, m.start() - 250): m.end() + 250]), flush=True)

for pid in ["stadt-wien_flchenwidmungsundbebauungsplanwien", "4111e2d8-1729-4953-899a-c55bc382857e",
            "a14e57c4-ea1c-4a7a-863a-b874ccf23790", "dc82da19-6878-46e8-a653-4966fa4dd108"]:
    t = zeige("CKAN " + pid, "https://www.data.gv.at/katalog/api/3/action/package_show?id=" + pid, 0)
    try:
        r = json.loads(t)["result"]
        print("BP PAKET", r.get("title"), re.sub(r"\s+", " ", r.get("notes") or "")[:1200], flush=True)
        for res in r.get("resources", []):
            print("BP RES", res.get("name"), res.get("format"), res.get("url"), flush=True)
    except Exception as e:
        print("BP PAKET FEHLER", e, flush=True)
