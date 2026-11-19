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
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402
from shapely.geometry import LineString, Polygon  # noqa: E402
from shapely.geometry.base import BaseGeometry  # noqa: E402

from ..modell import Massenmodell  # noqa: E402
from ..studie import Studie  # noqa: E402

A3 = (16.54, 11.69)
FARBE_BAU = "#c8553d"
FARBE_DG = "#e9a06b"
FARBE_GRENZE = "#222222"
FARBE_HILF = "#5b7db1"


def _polys(geom: BaseGeometry) -> list[Polygon]:
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]


def _plankopf(fig, titel: str, studie: Studie, massstab: str) -> None:
    w = studie.werte
    zeilen = [
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


def seite_axonometrie(studie: Studie, mm: Massenmodell):
    fig = plt.figure(figsize=A3)
    ax = fig.add_axes(FREI, projection="3d")
    _plankopf(fig, "Axonometrie", studie, "")
    ax.computed_zorder = False
    bp = mm.lokal(mm.bauplatz)
    xs, ys = bp.exterior.xy
    ax.plot(xs, ys, [0] * len(xs), color=FARBE_GRENZE, lw=1.4, zorder=0)
    for g in mm.geschosse:
        farbe = FARBE_DG if g.dachgeschoss else FARBE_BAU
        for p in _polys(mm.lokal(g.flaeche)):
            ring = list(p.exterior.coords)[:-1]
            z0, z1 = g.ok_fussboden, g.ok_fussboden + g.hoehe
            flaechen = [[(x, y, z0) for x, y in ring], [(x, y, z1) for x, y in ring]]
            for i in range(len(ring)):
                (xa, ya), (xb, yb) = ring[i], ring[(i + 1) % len(ring)]
                flaechen.append([(xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1)])
            ax.add_collection3d(Poly3DCollection(flaechen, facecolor=farbe,
                                                 edgecolor="white", lw=0.6, alpha=0.95))
    x0, y0, x1, y1 = bp.bounds
    r = max(x1 - x0, y1 - y0, mm.gesamthoehe) * 0.8
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ax.set_xlim(cx - r / 2, cx + r / 2)
    ax.set_ylim(cy - r / 2, cy + r / 2)
    ax.set_zlim(0, r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=28, azim=-60)
    ax.set_axis_off()
    return fig


SEITEN = {
    "lageplan": seite_lageplan,
    "schnitt": seite_schnitt,
    "ansicht": seite_ansicht,
    "axonometrie": seite_axonometrie,
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
            pdf.savefig(fig)
            if png:
                p = ordner / f"{name}.png"
                fig.savefig(p, dpi=110)
                erzeugt.append(p)
            plt.close(fig)
    return erzeugt
