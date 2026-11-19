"""Bebauungsstudie für eine Wiener Adresse, vollautomatisch aus Stadt-Wien-Daten.

Aufruf:
    python scripts/studie_adresse.py "Olbrichgasse 9, 1120 Wien" ergebnis \
        --breite 20 --tiefe 40 --bauweise o --strassenbreite 12

Widmung, Bauklasse, Zonen, Bausperre, Stellplatzzone und Bestand kommen aus
den offenen Daten der Stadt Wien, das Grundstück aus der Digitalen
Katastralmappe des BEV (beides CC BY 4.0). Der Ausschnitt des Flächen-
widmungs- und Bebauungsplans wird als Bild beigelegt. Bauweise und
Straßenbreite liegen nur als Bild vor und werden als Eingabe übernommen.
Ohne Kataster (Fehler oder --rechteck) wird ein Rechteck --breite × --tiefe gerechnet.
"""

import argparse
import sys
from pathlib import Path

from bebauungsstudie import Bauplatz, erstelle_studie
from bebauungsstudie.ausgabe.paket import exportiere_alles
from bebauungsstudie.daten import bebauungsplan, kataster
from bebauungsstudie.daten.standort import ermittle_standort


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("adresse")
    ap.add_argument("ordner")
    ap.add_argument("--grundstuecke", default="",
                    help="weitere Grundstücksnummern des Bauplatzes, durch Komma getrennt")
    ap.add_argument("--rechteck", action="store_true", help="Kataster nicht verwenden")
    ap.add_argument("--breite", type=float, default=20.0, help="Grundstücksbreite an der Straße (m)")
    ap.add_argument("--tiefe", type=float, default=40.0, help="Grundstückstiefe (m)")
    ap.add_argument("--bauweise", default="o", choices=["o", "gk", "ogk", "gr", "g"])
    ap.add_argument("--strassenbreite", type=float, default=None,
                    help="Abstand der Fluchtlinien (m), leer = unbekannt")
    a = ap.parse_args()

    out = Path(a.ordner)
    out.mkdir(parents=True, exist_ok=True)
    st = ermittle_standort(a.adresse)

    gst = None
    if not a.rechteck:
        try:
            weitere = tuple(g.strip() for g in a.grundstuecke.split(",") if g.strip())
            gst = kataster.grundstueck_am_punkt(st.x, st.y, weitere)
            st.protokoll += gst.protokoll
        except Exception as e:
            st.protokoll.append(f"Kataster nicht abrufbar ({type(e).__name__}: {e}); Rechteck angenommen")
    if gst is not None:
        umriss = gst.punkte
        kanten = gst.strassenkanten
        if not kanten:
            # ohne erkannte Straße: Kante, die dem Adresspunkt am nächsten liegt
            from shapely.geometry import LineString, Point
            n = len(umriss)
            kanten = {min(range(n), key=lambda i: LineString([umriss[i], umriss[(i + 1) % n]])
                          .distance(Point(st.x, st.y)))}
            st.protokoll.append(f"Straßenkante nicht erkannt, Kante {min(kanten)} angenommen")
        grund_text = (f"KG {gst.kg}, Grundstück {gst.gnr}: {gst.flaeche:.0f} m² laut BEV-Katastralmappe "
                      f"(Stichtag {gst.stichtag[6:]}.{gst.stichtag[4:6]}.{gst.stichtag[:4]}), "
                      f"Straßenkanten {sorted(kanten)}")
    else:
        umriss = [(0, 0), (a.breite, 0), (a.breite, a.tiefe), (0, a.tiefe)]
        kanten = {0}
        grund_text = f"{a.breite} m breit × {a.tiefe} m tief (Rechteck, Annahme)"

    plan_dateien = []
    flucht = None
    strassenbreite, strassenbreite_text = a.strassenbreite, (
        f"{a.strassenbreite} m (Eingabe)" if a.strassenbreite else "unbekannt")
    try:
        xs, ys = zip(*umriss)
        rand = max(25.0, 0.6 * max(max(xs) - min(xs), max(ys) - min(ys)))
        bbox = (min(xs) - rand, min(ys) - rand, max(xs) + rand, max(ys) + rand)
        if gst is not None:
            try:
                flucht, _, _ = bebauungsplan.lies_fluchtlinien(umriss, kanten, bbox)
                st.protokoll += flucht.protokoll
                if strassenbreite is None and flucht.strassenbreiten:
                    strassenbreite = min(flucht.strassenbreiten.values())
                    strassenbreite_text = (f"{strassenbreite:.1f} m (aus dem Planbild gemessen, "
                                           "schmalste angrenzende Straße)")
            except Exception as e:
                st.protokoll.append(f"Fluchtlinien nicht auswertbar ({type(e).__name__}: {e})")
            plan_dateien = bebauungsplan.zeichne_ausschnitt(
                out / "bebauungsplan", umriss, bbox, ebenen=("flwbplmzk", "flwbplflucht"),
                titel=f"Flächenwidmungs- und Bebauungsplan – {st.adresse}",
                erkannt=flucht.flaeche if flucht else None)
            st.protokoll.append("Bebauungsplan: Ausschnitt als Bild beigelegt")
    except Exception as e:
        st.protokoll.append(f"Bebauungsplan-Ausschnitt nicht abrufbar ({type(e).__name__}: {e})")
        try:
            (out / "wmts_capabilities.xml").write_text(bebauungsplan._capabilities(), encoding="utf-8")
        except Exception:
            pass

    kopf = [
        f"# Bebauungsstudie {a.adresse}",
        "",
        "Vorabschätzung, keine Rechtsauskunft. Datenquellen: Stadt Wien – data.wien.gv.at, "
        "BEV – data.bev.gv.at (beide CC BY 4.0).",
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
        "",
        "## Eingaben und Annahmen (im Plandokument nur als Bild, bitte prüfen)",
        "",
        f"- Grundstück: {grund_text}",
        f"- Bauweise: {a.bauweise} (Annahme, im Plandokument prüfen)",
        f"- Abstand der Fluchtlinien (Straßenbreite): {strassenbreite_text}",
        "- Bebaubare Fläche: " + ("innerhalb der aus dem Planbild erkannten Baufluchtlinien (bitte prüfen)"
                                  if flucht and flucht.flaeche else "pauschal mit Vorgarten 5 m gerechnet"),
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
        umriss=umriss,
        strassenkanten=kanten,
        bauklasse=st.bauklasse,
        bauweise=a.bauweise,
        fluchtlinienabstand=strassenbreite,
        fluchtlinien_flaeche=flucht.flaeche if flucht else None,
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
                     + [f"- {p.name}" for p in dateien]
                     + [f"- {Path(p).name}" for p in plan_dateien])
    (out / "ergebnis.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
