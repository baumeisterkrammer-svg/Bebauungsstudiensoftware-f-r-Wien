"""Erkundung: BEV-Kataster Open Data (CC BY 4.0) – Verzeichnisse, Dateien, Felder."""
import re, sys, urllib.request, zipfile, io, os

BASIS = "https://data.bev.gv.at/download/Kataster/"

def hole(url, n=None):
    req = urllib.request.Request(url, headers={"User-Agent": "bebauungsstudie/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read() if n is None else r.read(n)

def liste(url):
    try:
        html = hole(url).decode("utf-8", "replace")
    except Exception as e:
        print("FEHLER", url, e, flush=True); return []
    links = [l for l in re.findall(r'href="([^"?]+)"', html) if not l.startswith(("/", "http", "..")) or l.startswith(url)]
    print("LISTE", url, links[:60], flush=True)
    return links

for d in liste(BASIS):
    if d.endswith("/"):
        for e in liste(BASIS + d):
            if e.endswith("/"):
                sub = liste(BASIS + d + e)
                print("SUB", d + e, [s for s in sub if "Wien" in s or "wien" in s.lower()], flush=True)
