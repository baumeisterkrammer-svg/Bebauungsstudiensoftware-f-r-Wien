"""Pläne der Studie: Lageplan mit Grundriss, Schnitt, Straßenansicht, Axonometrie.

Ausgabe als mehrseitiges PDF (A3 quer) und einzelne PNG-Dateien. Die
Zeichnungen sind schematisch (Vorentwurf), Maßstab im Plankopf angegeben.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402
from shapely import affinity  # noqa: E402
from shapely.geometry import LineString, Polygon  # noqa: E402
from shapely.geometry.base import BaseGeometry  # noqa: E402

from ..modell import Massenmodell  # noqa: E402
from ..studie import Studie  # noqa: E402

A3 = (16.54, 11.69)
FARBE_BAU = "#c8553d"
FARBE_DG = "#e9a06b"
FARBE_GRENZE = "#222222"
FARBE_HILF = "#5b7db1"
FARBE_BESTAND = "#d9d9d9"
FARBE_NACHBAR = "#ffffff"
KANTE_NACHBAR = "#8c8c8c"


def _kontext_lokal(mm: Massenmodell):
    """Nachbargebäude im lokalen System: Liste (Polygon, Höhe, am Bauplatz)."""
    k = mm.kontext
    if k is None:
        return []
    mat = list(mm.lokal_matrix())
    return [(affinity.affine_transform(b.grundriss, mat), b.hoehe, b.am_bauplatz) for b in k.bestand]


def _luftbild(ax, mm: Massenmodell, alpha: float = 1.0):
    k = mm.kontext
    if k is None or k.luftbild is None:
        return False
    a, b, d, e, xoff, yoff = mm.lokal_matrix()
    m = Affine2D(np.array([[a, b, xoff], [d, e, yoff], [0, 0, 1]]))
    im = ax.imshow(k.luftbild, extent=k.luftbild_ausdehnung, origin="upper", alpha=alpha,
                   interpolation="bilinear", zorder=0)
    im.set_transform(m + ax.transData)
    im.set_clip_path(ax.patch)
    return True


def _polys(geom: BaseGeometry) -> list[Polygon]:
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]


def _plankopf(fig, titel: str, studie: Studie, massstab: str, zeilen=None) -> None:
    w = studie.werte
    zeilen = zeilen or [
        f"Bauplatz {w['Bauplatzfläche m²'].wert:.0f} m²",
        f"bebaut {w['Bebaute Fläche m²'].wert:.0f} m²",
        f"BGF {w['BGF m²'].wert:.0f} m²",
        f"Gebäudehöhe {w['Gebäudehöhe m'].wert} m",
        f"{w['Vollgeschoße'].wert} Vollgeschoße + {len(w['Dachgeschoße'].wert)} DG",
        f"ca. {w['Wohnungen'].wert} Wohnungen, {w['Pflichtstellplätze'].wert} Stellplätze",
    ]
    fig.text(0.02, 0.96, titel, fontsize=18, weight="bold", va="top")
    fig.text(0.02, 0.925, "Bebauungsstudie · Vorentwurf · keine Rechtsauskunft",
             fontsize=10, color="#555", va="top")
    fig.text(0.98, 0.96, "\n".join(zeilen), fontsize=10, ha="right", va="top",
             family="monospace")
    if massstab:
        fig.text(0.98, 0.03, f"Maßstab {massstab} (bei A3)", fontsize=9, ha="right",
                 color="#555")


def _achse_massstab(ax, breite_m: float, hoehe_m: float, frei: tuple) -> str:
    # Zeichenfläche in cm bei A3 → Maßstab runden
    l, b, r, t = frei
    breite_cm = A3[0] * 2.54 * (r - l)
    hoehe_cm = A3[1] * 2.54 * (t - b)
    noetig = max(breite_m * 100 / breite_cm, hoehe_m * 100 / hoehe_cm)
    for m in (100, 200, 250, 500, 1000, 2000):
        if m >= noetig:
            return f"1:{m}", m
    return f"1:{math.ceil(noetig)}", math.ceil(noetig)


def _setze_massstab(ax, fig, frei, x0, x1, y0, y1, m):
    l, b, r, t = frei
    breite_m = A3[0] * 2.54 * (r - l) / 100 * m
    hoehe_m = A3[1] * 2.54 * (t - b) / 100 * m
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ax.set_xlim(cx - breite_m / 2, cx + breite_m / 2)
    ax.set_ylim(cy - hoehe_m / 2, cy + hoehe_m / 2)
    ax.set_aspect("equal")
    ax.axis("off")


FREI = (0.04, 0.06, 0.96, 0.86)


def _neue_seite(titel, studie, x0, x1, y0, y1):
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes(FREI)
    text, m = _achse_massstab(ax, x1 - x0, y1 - y0, FREI)
    _setze_massstab(ax, fig, FREI, x0, x1, y0, y1, m)
    _plankopf(fig, titel, studie, text)
    return fig, ax


def _mass(ax, p0, p1, versatz, text=None):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    l = math.hypot(dx, dy)
    nx, ny = -dy / l * versatz, dx / l * versatz
    a = (x0 + nx, y0 + ny)
    b = (x1 + nx, y1 + ny)
    ax.annotate("", a, b, arrowprops=dict(arrowstyle="<->", lw=0.7, color="#333"))
    ax.text((a[0] + b[0]) / 2 + nx * 0.25, (a[1] + b[1]) / 2 + ny * 0.25,
            text or f"{l:.2f}", ha="center", va="center", fontsize=8,
            rotation=math.degrees(math.atan2(dy, dx)) % 180 - (180 if math.degrees(math.atan2(dy, dx)) % 180 > 90 else 0),
            bbox=dict(fc="white", ec="none", pad=0.5))


def seite_lageplan(studie: Studie, mm: Massenmodell):
    bp = mm.lokal(mm.bauplatz)
    x0, y0, x1, y1 = bp.bounds
    fig, ax = _neue_seite("Lageplan und Grundriss Regelgeschoß", studie,
                          x0 - 12, x1 + 12, y0 - 14, y1 + 6)
    # Straße
    ax.fill([x0 - 12, x1 + 12, x1 + 12, x0 - 12], [-12, -12, 0, 0], color="#eee")
    ax.text((x0 + x1) / 2, -6, "Straße", ha="center", va="center", color="#777")
    ax.plot(*bp.exterior.xy, color=FARBE_GRENZE, lw=1.6, label="Bauplatz")
    if mm.vorgarten_linie is not None:
        vg = mm.lokal(mm.vorgarten_linie)
        ax.plot(*vg.xy, color=FARBE_HILF, lw=1, ls="--", label="Vorgarten")
    for p in _polys(mm.lokal(mm.bebaubar)):
        ax.fill(*p.exterior.xy, color=FARBE_BAU, alpha=0.85, label="Regelgeschoß")
        ex = list(p.exterior.coords)
        for i in range(len(ex) - 1):
            _mass(ax, ex[i], ex[i + 1], -2.0)
    for g in mm.geschosse:
        if g.dachgeschoss:
            for p in _polys(mm.lokal(g.flaeche)):
                ax.plot(*p.exterior.xy, color=FARBE_DG, lw=1.2, ls="--",
                        label=f"{g.name}")
    ex = list(bp.exterior.coords)
    for i in range(len(ex) - 1):
        _mass(ax, ex[i], ex[i + 1], 3.5)
    # Nordpfeil entfällt: lokale Ausrichtung zur Straße
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), loc="upper left", frameon=False, fontsize=9)
    return fig


def seite_umgebung(studie: Studie, mm: Massenmodell):
    bp = mm.lokal(mm.bauplatz)
    x0, y0, x1, y1 = bp.bounds
    rand = 28
    fig, ax = _neue_seite("Lageplan mit Umgebung", studie, x0 - rand, x1 + rand, y0 - rand, y1 + rand)
    hat_bild = _luftbild(ax, mm)
    for poly, h, am in _kontext_lokal(mm):
        if am:
            ax.fill(*poly.exterior.xy, facecolor="none", edgecolor="#555", hatch="///", lw=0.6,
                    zorder=2, label="Bestand am Bauplatz")
            continue
        ax.fill(*poly.exterior.xy, facecolor=FARBE_BESTAND, edgecolor="#444", lw=0.5,
                alpha=0.75 if hat_bild else 1.0, zorder=2, label="Nachbarbebauung (Höhe ü. Gelände)")
        if poly.area > 25:
            c = poly.representative_point()
            ax.text(c.x, c.y, f"{h:.1f}", ha="center", va="center", fontsize=6.5, color="#222", zorder=3)
    ax.fill(*bp.exterior.xy, facecolor="white", alpha=0.25, zorder=3)
    ax.plot(*bp.exterior.xy, color="#d00000", lw=1.8, zorder=5, label="Bauplatz")
    for p in _polys(mm.lokal(mm.bebaubar)):
        ax.fill(*p.exterior.xy, color=FARBE_BAU, alpha=0.9, zorder=4, label="Neubau (Regelgeschoß)")
    gh = mm.gesamthoehe
    c = bp.representative_point()
    ax.text(c.x, c.y, f"Neubau\n{gh:.1f}", ha="center", va="center", fontsize=8, color="white",
            weight="bold", zorder=6)
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), loc="upper left", fontsize=9, framealpha=0.9)
    if hat_bild:
        fig.text(0.04, 0.035, "Luftbild und Baukörpermodell: Stadt Wien – data.wien.gv.at (CC BY 4.0); "
                 "Grundstück: BEV (CC BY 4.0)", fontsize=7, color="#555")
    return fig


def _schnittintervalle(geom: BaseGeometry, u: float) -> list[tuple[float, float]]:
    big = 1e4
    linie = LineString([(u, -big), (u, big)])
    s = geom.intersection(linie)
    teile = [s] if isinstance(s, LineString) else list(getattr(s, "geoms", []))
    out = []
    for t in teile:
        ys = [c[1] for c in t.coords]
        if ys:
            out.append((min(ys), max(ys)))
    return out


def _huelle_profil(intervall, gh, dach, winkel):
    a, b = intervall
    tan = math.tan(math.radians(winkel))
    spitze = min(dach - gh, (b - a) / 2 * tan)
    breite_oben = (b - a) - 2 * spitze / tan
    return [
        (a, 0), (a, gh), (a + spitze / tan, gh + spitze),
        (a + spitze / tan + breite_oben, gh + spitze), (b, gh), (b, 0),
    ]


def seite_schnitt(studie: Studie, mm: Massenmodell):
    bp = mm.lokal(mm.bauplatz)
    bx0, _, bx1, _ = bp.bounds
    bau = mm.lokal(mm.bebaubar)
    u = bau.centroid.x
    _, by0, _, by1 = bp.bounds
    h = mm.dachabschluss
    fig, ax = _neue_seite("Schnitt A–A (quer zur Straße)", studie,
                          by0 - 12, by1 + 6, -4, h + 4)
    ax.plot([by0 - 12, by1 + 6], [0, 0], color=FARBE_GRENZE, lw=1.6)
    ax.fill_between([by0 - 12, by1 + 6], -2, 0, color="#ddd")
    ax.text((by0 - 12 + by0) / 2, 0.6, "Straße", ha="center", fontsize=9, color="#555")
    for y in (by0, by1):
        ax.plot([y, y], [-1.5, h + 1], color=FARBE_GRENZE, lw=0.8, ls=":")
    ax.text(by0, h + 1.4, "Grundgrenze", ha="center", fontsize=8)
    ax.text(by1, h + 1.4, "Grundgrenze", ha="center", fontsize=8)
    for iv in _schnittintervalle(bau, u):
        prof = _huelle_profil(iv, mm.gebaeudehoehe, mm.dachabschluss, mm.umrisswinkel)
        ax.plot(*zip(*prof), color=FARBE_HILF, lw=1.2, ls="--",
                label=f"zulässiger Umriss ({mm.umrisswinkel:.0f}°)")
    for g in mm.geschosse:
        for a, b in _schnittintervalle(mm.lokal(g.flaeche), u):
            farbe = FARBE_DG if g.dachgeschoss else FARBE_BAU
            ax.add_patch(plt.Rectangle((a, g.ok_fussboden), b - a, g.hoehe,
                                       fc=farbe, ec="white", lw=1.5, alpha=0.9))
            ax.text(a + 0.6, g.ok_fussboden + g.hoehe / 2, g.name, va="center",
                    fontsize=8, color="white", weight="bold")
    xr = by1 + 2.5
    for hoehe, txt in ((mm.gebaeudehoehe, "Gebäudehöhe"),
                       (mm.dachabschluss, "max. Dachabschluss")):
        ax.plot([by0 - 2, by1 + 2], [hoehe, hoehe], color="#888", lw=0.6, ls="-.")
        ax.text(xr, hoehe, f"+{hoehe:.2f} {txt}", va="center", fontsize=8)
    ax.text(xr, 0.6, "±0,00 Gelände", va="bottom", fontsize=8)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(dict(zip(labels, handles)).values(), dict(zip(labels, handles)).keys(),
              loc="upper left", frameon=False, fontsize=9)
    return fig


def seite_ansicht(studie: Studie, mm: Massenmodell):
    bp = mm.lokal(mm.bauplatz)
    bx0, _, bx1, _ = bp.bounds
    h = mm.dachabschluss
    fig, ax = _neue_seite("Straßenansicht", studie, bx0 - 6, bx1 + 6, -3, h + 4)
    ax.plot([bx0 - 6, bx1 + 6], [0, 0], color=FARBE_GRENZE, lw=1.6)
    for x in (bx0, bx1):
        ax.plot([x, x], [-1, h + 1], color=FARBE_GRENZE, lw=0.8, ls=":")
    for g in mm.geschosse:
        for p in _polys(mm.lokal(g.flaeche)):
            a, _, b, _ = p.bounds
            farbe = FARBE_DG if g.dachgeschoss else FARBE_BAU
            ax.add_patch(plt.Rectangle((a, g.ok_fussboden), b - a, g.hoehe,
                                       fc=farbe, ec="white", lw=1.5, alpha=0.9))
            # schematische Fensterachsen alle 3,0 m
            n = int((b - a - 1.0) // 3.0)
            for i in range(n):
                fx = a + 1.0 + i * 3.0 + 0.6
                ax.add_patch(plt.Rectangle((fx, g.ok_fussboden + 0.9), 1.2, 1.5,
                                           fc="white", ec="none", alpha=0.85))
    ax.plot([bx0 - 2, bx1 + 2], [mm.gebaeudehoehe] * 2, color="#888", lw=0.6, ls="-.")
    ax.text(bx1 + 2.5, mm.gebaeudehoehe, f"+{mm.gebaeudehoehe:.2f} Gebäudehöhe",
            va="center", fontsize=8)
    return fig


def _prisma(ring, z0, z1):
    flaechen = [[(x, y, z0) for x, y in ring], [(x, y, z1) for x, y in ring]]
    for i in range(len(ring)):
        (xa, ya), (xb, yb) = ring[i], ring[(i + 1) % len(ring)]
        flaechen.append([(xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1)])
    return flaechen


FARBEN_NV = {"bestand": ("#b8b0a4", "#6b645a", "Bestand (erhalten)"),
             "aufstockung": ("#e07b39", "white", "Aufstockung"),
             "zubau": ("#c8553d", "white", "Zubau im Hof"),
             "dachgeschoss": ("#f2b880", "white", "Dachgeschoßausbau")}


def _axonometrie(studie: Studie, mm: Massenmodell, titel: str, volumen, hoehe: float,
                 zeilen=None, legende=None, azim: float = -60):
    """volumen: Liste (Polygon lokal, z0, z1, Füllfarbe, Kantenfarbe)."""
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes(FREI, projection="3d")
    _plankopf(fig, titel, studie, "", zeilen)
    ax.computed_zorder = False
    elev = 30
    blick = np.array([math.cos(math.radians(elev)) * math.cos(math.radians(azim)),
                      math.cos(math.radians(elev)) * math.sin(math.radians(azim)),
                      math.sin(math.radians(elev))])
    bp = mm.lokal(mm.bauplatz)
    x0, y0, x1, y1 = bp.bounds
    kontext = _kontext_lokal(mm)
    r = max(x1 - x0, y1 - y0, hoehe) * (2.0 if kontext else 0.8)
    if kontext:
        r = max(r, 55.0)  # kleine Bauplätze: genug Umgebung zeigen
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    k = mm.kontext
    if k is not None and k.luftbild is not None:
        # Boden mit Luftbild: Bildpunkte ins lokale System, auf den Ausschnitt begrenzt
        img = k.luftbild
        xmin, xmax, ymin, ymax = k.luftbild_ausdehnung
        # rund 300 Bildpunkte über den sichtbaren Ausschnitt
        schritt = max(1, int(max(img.shape[:2]) * r / max(xmax - xmin, ymax - ymin) / 300))
        bild = img[::schritt, ::schritt] / 255.0
        hh, ww = bild.shape[:2]
        xmin, xmax, ymin, ymax = k.luftbild_ausdehnung
        gx, gy = np.meshgrid(np.linspace(xmin, xmax, ww), np.linspace(ymax, ymin, hh))
        a, b, d, e, xoff, yoff = mm.lokal_matrix()
        u, v = a * gx + b * gy + xoff, d * gx + e * gy + yoff
        innen = (np.abs(u - cx) <= r / 2) & (np.abs(v - cy) <= r / 2)
        farben = np.dstack([bild[..., :3], np.where(innen, 1.0, 0.0)])
        ax.plot_surface(u, v, np.zeros_like(u), facecolors=farben, rstride=1, cstride=1,
                        shade=False, linewidth=0, antialiased=False, zorder=0)
    xs, ys = bp.exterior.xy
    ax.plot(xs, ys, [0.05] * len(xs), color="#d00000", lw=1.6, zorder=1)

    # Nachbarn: hell und durchscheinend, nur Umgebung. Alle Flächen in einer
    # Sammlung, die matplotlib Fläche für Fläche nach Tiefe sortiert; Böden entfallen.
    nachbar_flaechen = []
    for poly, h, am in kontext:
        if am:
            continue
        c = poly.centroid
        if abs(c.x - cx) > r / 2 or abs(c.y - cy) > r / 2:
            continue
        nachbar_flaechen += _prisma(list(poly.exterior.coords)[:-1], 0, h)[1:]
    if nachbar_flaechen:
        ax.add_collection3d(Poly3DCollection(nachbar_flaechen, facecolor=FARBE_NACHBAR, alpha=0.4,
                                             edgecolor=KANTE_NACHBAR, lw=0.4, zsort="average",
                                             zorder=2))
    # Projekt: deckend und immer vor den Nachbarn; gestapelte Körper untere zuerst,
    # dann nach Blicktiefe (Malerverfahren)
    koerper = []
    for p, z0, z1, farbe, kante in volumen:
        c = p.centroid
        koerper.append((round(z0, 1), np.dot([c.x, c.y, (z0 + z1) / 2], blick),
                        _prisma(list(p.exterior.coords)[:-1], z0, z1), farbe, kante))
    koerper.sort(key=lambda k_: (k_[0], k_[1]))
    for i, (_, _, flaechen, farbe, kante) in enumerate(koerper):
        ax.add_collection3d(Poly3DCollection(flaechen, facecolor=farbe, edgecolor=kante, lw=0.5,
                                             zorder=3 + i / (len(koerper) + 1)))
    ax.set_xlim(cx - r / 2, cx + r / 2)
    ax.set_ylim(cy - r / 2, cy + r / 2)
    zf = max(0.25, 1.3 * hoehe / r) if kontext else 1.0
    ax.set_zlim(0, r * zf)
    ax.set_box_aspect((1, 1, zf), zoom=1.0)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    legende = list(legende or [])
    if nachbar_flaechen:
        legende.append((FARBE_NACHBAR, "Nachbargebäude (Bestand, Stadt Wien)"))
    if legende:
        from matplotlib.patches import Patch
        fig.legend([Patch(facecolor=f, edgecolor="#555") for f, _ in legende], [t for _, t in legende],
                   loc="upper left", bbox_to_anchor=(0.02, 0.88), frameon=False, fontsize=10)
    if kontext:
        fig.text(0.04, 0.035, "Nachbarbebauung: Baukörpermodell Stadt Wien; Luftbild: Stadt Wien "
                 "(data.wien.gv.at, CC BY 4.0)", fontsize=7, color="#555")
    return fig


def seite_axonometrie(studie: Studie, mm: Massenmodell):
    volumen = []
    for g in mm.geschosse:
        farbe = FARBE_DG if g.dachgeschoss else FARBE_BAU
        for p in _polys(mm.lokal(g.flaeche)):
            volumen.append((p, g.ok_fussboden, g.ok_fussboden + g.hoehe, farbe, "white"))
    titel = "Axonometrie im Bestand" if mm.kontext else "Axonometrie"
    if studie.nachverdichtung is not None:
        titel = "Neubau (nach Abbruch)" + (" im Bestand" if mm.kontext else "")
    legende = [(FARBE_BAU, "Neubau Vollgeschoße"), (FARBE_DG, "Neubau Dachgeschoße")]
    return _axonometrie(studie, mm, titel, volumen, mm.gesamthoehe, legende=legende)


def seite_nachverdichtung(studie: Studie, mm: Massenmodell):
    nv = studie.nachverdichtung
    if nv is None:
        return None
    gh = studie.annahmen.geschosshoehe
    volumen, arten = [], []
    for v in nv.volumen:
        farbe, kante, _ = FARBEN_NV[v.art]
        arten.append(v.art)
        # Bestand in Geschoße teilen, damit die Aufstockung ablesbar bleibt
        if v.art in ("aufstockung", "zubau"):
            stufen = [v.z0 + i * gh for i in range(round((v.z1 - v.z0) / gh) + 1)]
        else:
            stufen = [v.z0, v.z1]
        for p in _polys(mm.lokal(v.flaeche)):
            for z0, z1 in zip(stufen, stufen[1:]):
                volumen.append((p, z0, z1, farbe, kante))
    w = nv.werte
    zeilen = [
        f"Bestand BGF ca. {w['Bestand BGF m² (geschätzt)'].wert:.0f} m²",
        f"+ Aufstockung {w['Aufstockung BGF m²'].wert:.0f} m²",
        f"+ Dachgeschoßausbau {w['Dachgeschoßausbau BGF m²'].wert:.0f} m²",
        f"+ Zubau im Hof {w['Zubau im Hof BGF m²'].wert:.0f} m²",
        f"= zusätzlich {w['Zusätzliche BGF m²'].wert:.0f} m² "
        f"(ca. {w['Zusätzliche Wohnungen'].wert} Wohnungen)",
        f"Neubau zum Vergleich {w['Vergleich Neubau BGF m²'].wert:.0f} m²",
    ]
    hoehe = max([v.z1 for v in nv.volumen] + [mm.gesamthoehe])
    # Blick von der Seite, auf der der Bestand liegt, damit er nicht verdeckt ist
    bestand = [mm.lokal(v.flaeche) for v in nv.volumen if v.art == "bestand"]
    azim = -60
    if bestand:
        from shapely.ops import unary_union
        mitte = mm.lokal(mm.bauplatz).centroid
        b = unary_union(bestand).centroid
        dx, dy = b.x - mitte.x, b.y - mitte.y
        azim = max((-60, 30, 120, 210), key=lambda a: dx * math.cos(math.radians(a))
                   + dy * math.sin(math.radians(a)))
    legende = [(FARBEN_NV[a][0], FARBEN_NV[a][2]) for a in FARBEN_NV if a in arten]
    return _axonometrie(studie, mm, "Nachverdichtung (Bestand erhalten)", volumen, hoehe,
                        zeilen=zeilen, legende=legende, azim=azim)


SEITEN = {
    "umgebung": seite_umgebung,
    "lageplan": seite_lageplan,
    "schnitt": seite_schnitt,
    "ansicht": seite_ansicht,
    "axonometrie": seite_axonometrie,
    "nachverdichtung": seite_nachverdichtung,
}


def exportiere_plaene(studie: Studie, mm: Massenmodell, ordner: str | Path,
                      png: bool = True) -> list[Path]:
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    pdf_pfad = ordner / "plaene.pdf"
    erzeugt = [pdf_pfad]
    with PdfPages(pdf_pfad) as pdf:
        for name, fn in SEITEN.items():
            fig = fn(studie, mm)
            if fig is None:
                continue
            pdf.savefig(fig)
            if png:
                p = ordner / f"{name}.png"
                fig.savefig(p, dpi=110)
                erzeugt.append(p)
            plt.close(fig)
    return erzeugt
