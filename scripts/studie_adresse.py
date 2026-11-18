"""Bebauungsstudie für eine Wiener Adresse, vollautomatisch aus Stadt-Wien-Daten.

Aufruf:
    python scripts/studie_adresse.py "Olbrichgasse 9, 1120 Wien" ergebnis \
        --breite 20 --tiefe 40 --bauweise o --strassenbreite 12

Widmung, Bauklasse, Zonen, Bausperre, Stellplatzzone und Bestand kommen aus
den offenen Daten. Grundstücksmaße, Bauweise und Straßenbreite sind in den
offenen Daten nicht enthalten und werden als Eingabe übernommen.
"""

import argparse
import sys
from pathlib import Path

from bebauungsstudie import Bauplatz, erstelle_studie
from bebauungsstudie.ausgabe.paket import exportiere_alles
from bebauungsstudie.daten.standort import ermittle_standort


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("adresse")
    ap.add_argument("ordner")
    ap.add_argument("--breite", type=float, default=20.0, help="Grundstücksbreite an der Straße (m)")
    ap.add_argument("--tiefe", type=float, default=40.0, help="Grundstückstiefe (m)")
    ap.add_argument("--bauweise", default="o", choices=["o", "gk", "ogk", "gr", "g"])
    ap.add_argument("--strassenbreite", type=float, default=None,
                    help="Abstand der Fluchtlinien (m), leer = unbekannt")
    a = ap.parse_args()

    out = Path(a.ordner)
    out.mkdir(parents=True, exist_ok=True)
    st = ermittle_standort(a.adresse)

    kopf = [
        f"# Bebauungsstudie {a.adresse}",
        "",
        "Vorabschätzung, keine Rechtsauskunft. Datenquelle: Stadt Wien – data.wien.gv.at (CC BY 4.0).",
        "",
        "## Aus den Stadt-Wien-Daten (automatisch)",
        "",
        f"- Gefundene Adresse: {st.adresse} (x={st.x:.1f}, y={st.y:.1f}, EPSG:31256)",
        f"- Widmung: {st.widmung} – {st.widmung_text}",
        f"- Bauklasse: {st.bauklasse.name if st.bauklasse else '–'}"
        + (" (Gartensiedlungsgebiet)" if st.gartensiedlung else ""),
        f"- Schutzzone: {'ja' if st.schutzzone else 'nein'} · Wohnzone: {'ja' if st.wohnzone else 'nein'}"
        f" · Bausperre: {'ja' if st.bausperre else 'nein'}",
        f"- Stellplatzzone (WGarG § 50a): {st.stellplatzzone}",
        f"- Bestand im Umkreis von 20 m: {len(st.bestand)} Gebäudeteile, Höhen "
        + ", ".join(f"{b.hoehe_m} m" for b in st.bestand if b.hoehe_m is not None),
        "",
        "## Eingaben und Annahmen (nicht in den offenen Daten)",
        "",
        f"- Grundstück: {a.breite} m breit × {a.tiefe} m tief (Rechteck, Annahme)",
        f"- Bauweise: {a.bauweise} (Annahme, im Plandokument prüfen)",
        f"- Abstand der Fluchtlinien: {a.strassenbreite or 'unbekannt'} m",
        "- Besondere Bestimmungen des Plandokuments: nicht berücksichtigt",
        "",
        "## Protokoll",
        "",
    ] + [f"- {z}" for z in st.protokoll]

    if not st.bauland:
        kopf += ["", f"**Keine Studie:** Widmung {st.widmung} ist kein Bauland."]
        (out / "ergebnis.md").write_text("\n".join(kopf), encoding="utf-8")
        print("\n".join(kopf))
        return 0

    bp = Bauplatz(
        umriss=[(0, 0), (a.breite, 0), (a.breite, a.tiefe), (0, a.tiefe)],
        strassenkanten={0},
        bauklasse=st.bauklasse,
        bauweise=a.bauweise,
        fluchtlinienabstand=a.strassenbreite,
        schutzzone=st.schutzzone,
        gartensiedlung=st.gartensiedlung,
        wohngebiet=(st.widmungsklasse == "WO"),
    )
    studie = erstelle_studie(bp)
    if st.bausperre:
        studie.hinweise.append("Bausperre am Standort: Bebauung derzeit eingeschränkt.")
    if st.stellplatzzone:
        studie.hinweise.append(
            f"Stellplatzzone {st.stellplatzzone}: mögliche Reduktion der Pflichtstellplätze "
            "nach WGarG § 50a ist noch nicht eingerechnet.")
    dateien = exportiere_alles(studie, out) if "BGF m²" in studie.werte else []
    text = "\n".join(kopf + ["", "## Ergebnis", "", "```", studie.bericht(), "```", ""]
                     + [f"- {p.name}" for p in dateien])
    (out / "ergebnis.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
