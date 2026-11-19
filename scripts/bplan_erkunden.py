"""Erkundung: Woher kommen Bauweise, Fluchtlinien, Besondere Bestimmungen maschinenlesbar?"""
import re, html, json, urllib.request, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 (bebauungsstudie/0.1)"}

def hole(url, t=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()

def text(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))

for url in ["https://www.wien.gv.at/stadtentwicklung/flaechenwidmung/geodaten.html",
            "https://www.wien.gv.at/stadtentwicklung/flaechenwidmung/hilfetext/daten.html"]:
    try:
        h, u = hole(url)
        i = h.find("<main") if "<main" in h else 0
        print("BP SEITE", url, text(h[i:])[:5000], flush=True)
        print("BP LINKS", url, sorted(set(re.findall(r'href="([^"]+)"', h)))[:150], flush=True)
    except Exception as e:
        print("BP SEITE", url, "FEHLER", e, flush=True)

try:
    h, _ = hole("https://data.europa.eu/api/hub/search/datasets/d8ed7c1d-2d49-476d-b0c6-711d4fcf9f0f")
    d = json.loads(h)["result"]
    print("BP EU", json.dumps({k: d.get(k) for k in ("title", "description")}, ensure_ascii=False)[:2500], flush=True)
    for x in d.get("distributions", []):
        print("BP EU-DIST", x.get("title"), x.get("access_url"), x.get("download_url"), x.get("format"), flush=True)
except Exception as e:
    print("BP EU FEHLER", e, flush=True)

# Plan-Viewer: Skripte nach Dienst-URLs durchsuchen
gesehen = set()
muster = re.compile(r"""["'](https?://[^"']*?(?:MapServer|FeatureServer|wms|wfs|WMS|WFS|geoserver|arcgis|rest/services|/ogc|\.json|/api/)[^"']*)["']""")
for start in ["https://www.wien.gv.at/flaechenwidmung/public/", "https://www.wien.gv.at/flaechenwidmung/public/start.aspx",
              "https://www.wien.gv.at/stadtplan/", "https://www.wien.gv.at/flaechenwidmung/public/index.html"]:
    try:
        h, u = hole(start)
    except Exception as e:
        print("BP VIEWER", start, "FEHLER", e, flush=True); continue
    print("BP VIEWER", start, "->", u, len(h), text(h)[:400], flush=True)
    urls = set(muster.findall(h))
    for s in re.findall(r"""<script[^>]+src=["']([^"']+)["']""", h) + re.findall(r"""<iframe[^>]+src=["']([^"']+)["']""", h):
        s = urllib.parse.urljoin(u, s)
        if s in gesehen: continue
        gesehen.add(s)
        try:
            js, _ = hole(s)
            treffer = set(muster.findall(js))
            print("BP SKRIPT", s, len(js), sorted(treffer)[:40], flush=True)
            urls |= treffer
        except Exception as e:
            print("BP SKRIPT", s, "FEHLER", e, flush=True)
    print("BP DIENSTE", start, sorted(urls)[:80], flush=True)
