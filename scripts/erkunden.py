"""Erkundung: welche Stadt-Wien-Layer liefern an einer Adresse welche Daten.

Schreibt Rohantworten nach <ordner>/roh/ und eine Übersicht nach
<ordner>/uebersicht.md. Läuft in GitHub Actions (freies Internet).
"""

import json
import sys
import traceback
from pathlib import Path

from bebauungsstudie.daten import wien

VERMUTET = ["ogdwien:FMZKBKMOGD", "ogdwien:FLAECHENWIDMUNGOGD", "ogdwien:FLWIDMUNGOGD",
            "ogdwien:BEBAUUNGSPLANOGD", "ogdwien:FLWBPLOGD", "ogdwien:PLANDOKUMENTOGD"]

STICHWORTE = ("WIDMUNG", "BEBAU", "FLWB", "FLUCHT", "PLAN", "GRUND", "KATAST",
              "BAUBLOCK", "BKM", "GEBAEUDE", "SCHUTZ", "BAUSPERR", "WOHNZONE",
              "HOEHE", "BAUKLASSE", "STELLPLATZ", "PARKPICKERL", "REALNUT")


class Protokoll(list):
    """Liste, die jede Zeile sofort ausgibt (sichtbar auch bei Abbruch)."""

    def append(self, x):
        print(x, flush=True)
        super().append(x)

    def __iadd__(self, xs):
        for x in xs:
            self.append(x)
        return self


def main(adresse: str, ordner: str) -> None:
    out = Path(ordner)
    (out / "roh").mkdir(parents=True, exist_ok=True)
    zeilen = Protokoll()
    zeilen += [f"# Erkundung für {adresse}", ""]

    protokoll: list[str] = []
    treffer = wien.suche_adresse(adresse, protokoll)
    zeilen += protokoll + [""]
    (out / "roh" / "adresse.json").write_text(
        json.dumps([t.roh for t in treffer], ensure_ascii=False, indent=1))
    if not treffer:
        zeilen.append("Adresse nicht gefunden.")
        (out / "uebersicht.md").write_text("\n".join(zeilen))
        return
    t = treffer[0]
    zeilen += [f"Treffer: {t.text} bei x={t.x:.2f}, y={t.y:.2f} (EPSG:31256)", ""]

    # Diagnose der Capabilities-Antwort
    for version in ("1.1.0", "2.0.0"):
        try:
            roh = wien._hole(wien.WFS, {"service": "WFS", "request": "GetCapabilities",
                                        "version": version})
            text = roh.decode("utf-8", "replace")
            (out / "roh" / f"capabilities_{version}.xml").write_text(text)
            zeilen.append(f"Capabilities {version}: {len(roh)} Bytes, Anfang: "
                          + text[:300].replace("\n", " "))
        except Exception as e:
            zeilen.append(f"Capabilities {version}: {type(e).__name__}: {e}")
    zeilen.append("")
    layer = wien.layer_liste()
    for vermutet in VERMUTET:
        if vermutet not in [n for n, _ in layer]:
            layer.append((vermutet, "(vermutet)"))
    (out / "roh" / "layer.json").write_text(json.dumps(layer, ensure_ascii=False, indent=1))
    zeilen.append(f"{len(layer)} WFS-Layer insgesamt.\n")
    zeilen.append("ALLE: " + " ; ".join(f"{n.split(':')[-1]}={ti}" for n, ti in layer))
    for detail in ("ogdwien:GENFLWIDMUNGOGD", "ogdwien:STELLPLATZVERPFLOGD",
                   "ogdwien:GEBAEUDEINFOOGD", "ogdwien:FMZKBKMOGD"):
        try:
            gj = wien.features(detail, t.x, t.y, radius=15)
            for f in gj.get("features", [])[:4]:
                g = f.get("geometry") or {}
                zeilen.append(f"DETAIL {detail}: {g.get('type')} "
                              + json.dumps(f.get("properties", {}), ensure_ascii=False)[:900])
        except Exception as e:
            zeilen.append(f"DETAIL {detail}: {type(e).__name__}: {e}")
    passend = [(n, ti) for n, ti in layer
               if any(s in (n + " " + ti).upper() for s in STICHWORTE)]
    zeilen.append("| Layer | Titel | Features | Attribute (erstes Feature) |")
    zeilen.append("| --- | --- | --- | --- |")
    for name, titel in passend:
        try:
            gj = wien.features(name, t.x, t.y, radius=25)
            feats = gj.get("features", [])
            datei = name.replace(":", "_") + ".json"
            (out / "roh" / datei).write_text(json.dumps(gj, ensure_ascii=False))
            attr = feats[0].get("properties", {}) if feats else {}
            kurz = ", ".join(f"{k}={str(v)[:30]}" for k, v in list(attr.items())[:15])
            zeilen.append(f"| {name} | {titel} | {len(feats)} | {kurz} |")
        except Exception as e:  # weiter mit dem nächsten Layer
            zeilen.append(f"| {name} | {titel} | Fehler | {type(e).__name__}: {e} |")
    (out / "uebersicht.md").write_text("\n".join(zeilen), encoding="utf-8")


if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception:
        traceback.print_exc()
        sys.exit(1)
