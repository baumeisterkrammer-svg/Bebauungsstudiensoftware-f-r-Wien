"""DXF-Export für CAD: Lageplan, Schnitt und Ansicht in einer Datei.

Koordinaten in Metern. Der Lageplan liegt in Landeskoordinaten, Schnitt und
Ansicht daneben im lokalen System (u entlang der Straße, v ins Grundstück).
Layer: BAUPLATZ, VORGARTEN, GESCHOSS, DACHGESCHOSS, UMRISS, GELAENDE, TEXT.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf
from shapely.geometry import Polygon

from ..modell import Massenmodell
from ..studie import Studie
from .plaene import _huelle_profil, _polys, _schnittintervalle

LAYER = {
    "BAUPLATZ": 7, "VORGARTEN": 5, "GESCHOSS": 1, "DACHGESCHOSS": 30,
    "UMRISS": 5, "GELAENDE": 8, "TEXT": 7,
}


def _poly(msp, p: Polygon, layer: str, dx=0.0, dy=0.0):
    msp.add_lwpolyline([(x + dx, y + dy) for x, y in p.exterior.coords],
                       close=True, dxfattribs={"layer": layer})


def exportiere_dxf(studie: Studie, mm: Massenmodell, pfad: str | Path) -> Path:
    doc = ezdxf.new("R2018", setup=True)
    doc.units = ezdxf.units.M
    for name, farbe in LAYER.items():
        doc.layers.add(name, color=farbe)
    msp = doc.modelspace()

    # Lageplan in Originalkoordinaten
    _poly(msp, mm.bauplatz, "BAUPLATZ")
    if mm.vorgarten_linie is not None:
        msp.add_lwpolyline(list(mm.vorgarten_linie.coords), dxfattribs={"layer": "VORGARTEN"})
    for p in _polys(mm.bebaubar):
        _poly(msp, p, "GESCHOSS")
    for g in mm.geschosse:
        if g.dachgeschoss:
            for p in _polys(g.flaeche):
                _poly(msp, p, "DACHGESCHOSS")
    kt = getattr(mm, "kontext", None)
    if kt is not None and kt.bestand:
        doc.layers.add("BESTAND", color=8)
        for b in kt.bestand:
            if b.am_bauplatz or b.grundriss.area < 2:
                continue
            _poly(msp, b.grundriss, "BESTAND")
            c = b.grundriss.representative_point()
            msp.add_text(f"{b.hoehe:.1f}", height=0.8,
                         dxfattribs={"layer": "BESTAND"}).set_placement((c.x, c.y))
    x0, y0, x1, y1 = mm.bauplatz.bounds
    msp.add_text("LAGEPLAN", height=1.5, dxfattribs={"layer": "TEXT"}).set_placement((x0, y1 + 4))

    # Schnitt und Ansicht rechts daneben, lokal
    bp = mm.lokal(mm.bauplatz)
    bau = mm.lokal(mm.bebaubar)
    bx0, by0, bx1, by1 = bp.bounds
    ox = x1 + 20
    oy = y0

    def schnitt_x(v):
        return ox + (v - by0)

    u = bau.centroid.x
    msp.add_line((schnitt_x(by0 - 10), oy), (schnitt_x(by1 + 5), oy), dxfattribs={"layer": "GELAENDE"})
    for iv in _schnittintervalle(bau, u):
        prof = _huelle_profil(iv, mm.gebaeudehoehe, mm.dachabschluss, mm.umrisswinkel)
        msp.add_lwpolyline([(schnitt_x(v), oy + z) for v, z in prof], dxfattribs={"layer": "UMRISS"})
    for g in mm.geschosse:
        layer = "DACHGESCHOSS" if g.dachgeschoss else "GESCHOSS"
        for a, b in _schnittintervalle(mm.lokal(g.flaeche), u):
            z0, z1 = oy + g.ok_fussboden, oy + g.ok_fussboden + g.hoehe
            msp.add_lwpolyline([(schnitt_x(a), z0), (schnitt_x(b), z0), (schnitt_x(b), z1),
                                (schnitt_x(a), z1)], close=True, dxfattribs={"layer": layer})
    msp.add_text("SCHNITT A-A", height=1.5, dxfattribs={"layer": "TEXT"}).set_placement(
        (schnitt_x(by0), oy + mm.dachabschluss + 4))

    ox2 = schnitt_x(by1 + 5) + 20

    def ansicht_x(uu):
        return ox2 + (uu - bx0)

    msp.add_line((ansicht_x(bx0 - 5), oy), (ansicht_x(bx1 + 5), oy), dxfattribs={"layer": "GELAENDE"})
    for g in mm.geschosse:
        layer = "DACHGESCHOSS" if g.dachgeschoss else "GESCHOSS"
        for p in _polys(mm.lokal(g.flaeche)):
            a, _, b, _ = p.bounds
            z0, z1 = oy + g.ok_fussboden, oy + g.ok_fussboden + g.hoehe
            msp.add_lwpolyline([(ansicht_x(a), z0), (ansicht_x(b), z0), (ansicht_x(b), z1),
                                (ansicht_x(a), z1)], close=True, dxfattribs={"layer": layer})
    msp.add_text("STRASSENANSICHT", height=1.5, dxfattribs={"layer": "TEXT"}).set_placement(
        (ansicht_x(bx0), oy + mm.dachabschluss + 4))

    pfad = Path(pfad)
    doc.saveas(pfad)
    return pfad
