"""IFC-Export (BIM) des Massenmodells.

Je Geschoß ein IfcBuildingStorey mit Decke (IfcSlab), Außenwänden (IfcWall)
und einem Raum (IfcSpace) für die BGF. Dazu der Bauplatz als IfcSite.
Das Modell ist ein Volumenmodell für die Vorplanung, kein Ausführungsmodell.
"""

from __future__ import annotations

import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.geometry.base import BaseGeometry

from ..modell import Massenmodell
from ..studie import Studie

WANDSTAERKE = 0.3
DECKENSTAERKE = 0.25


def _polygone(geom: BaseGeometry) -> list[Polygon]:
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]


def _matrix(x: float, y: float, z: float, winkel: float = 0.0) -> np.ndarray:
    m = np.eye(4)
    c, s = math.cos(winkel), math.sin(winkel)
    m[0, 0], m[0, 1], m[1, 0], m[1, 1] = c, -s, s, c
    m[:3, 3] = (x, y, z)
    return m


def exportiere_ifc(studie: Studie, modell: Massenmodell, pfad: str | Path) -> Path:
    api = ifcopenshell.api
    f = api.project.create_file(version="IFC4")
    projekt = api.root.create_entity(f, ifc_class="IfcProject", name="Bebauungsstudie")
    api.unit.assign_unit(f)
    ctx = api.context.add_context(f, context_type="Model")
    body = api.context.add_context(
        f, context_type="Model", context_identifier="Body",
        target_view="MODEL_VIEW", parent=ctx,
    )

    site = api.root.create_entity(f, ifc_class="IfcSite", name="Bauplatz")
    api.aggregate.assign_object(f, products=[site], relating_object=projekt)
    gebaeude = api.root.create_entity(f, ifc_class="IfcBuilding", name="Baukörper")
    api.aggregate.assign_object(f, products=[gebaeude], relating_object=site)

    # Bauplatz als dünne Platte, damit er im Viewer sichtbar ist
    bp_pts = list(modell.bauplatz.exterior.coords)[:-1]
    flaeche = api.root.create_entity(f, ifc_class="IfcSlab", name="Bauplatz",
                                     predefined_type="BASESLAB")
    rep = api.geometry.add_slab_representation(f, context=body, depth=0.05,
                                               polyline=bp_pts)
    api.geometry.assign_representation(f, product=flaeche, representation=rep)
    api.geometry.edit_object_placement(f, product=flaeche, matrix=_matrix(0, 0, -0.05))
    api.spatial.assign_container(f, products=[flaeche], relating_structure=site)

    for g in modell.geschosse:
        storey = api.root.create_entity(f, ifc_class="IfcBuildingStorey", name=g.name)
        api.aggregate.assign_object(f, products=[storey], relating_object=gebaeude)
        api.geometry.edit_object_placement(f, product=storey,
                                           matrix=_matrix(0, 0, g.ok_fussboden))
        storey.Elevation = g.ok_fussboden
        elemente = []
        for poly in _polygone(g.flaeche):
            pts = list(poly.exterior.coords)[:-1]

            decke = api.root.create_entity(f, ifc_class="IfcSlab",
                                           name=f"Decke {g.name}", predefined_type="FLOOR")
            rep = api.geometry.add_slab_representation(
                f, context=body, depth=DECKENSTAERKE, polyline=pts)
            api.geometry.assign_representation(f, product=decke, representation=rep)
            api.geometry.edit_object_placement(
                f, product=decke, matrix=_matrix(0, 0, g.ok_fussboden))
            elemente.append(decke)

            # gegen den Uhrzeigersinn, damit die Wanddicke nach innen zeigt
            ring = list(orient(poly, sign=1.0).exterior.coords)
            for i in range(len(ring) - 1):
                (x0, y0), (x1, y1) = ring[i], ring[i + 1]
                laenge = math.hypot(x1 - x0, y1 - y0)
                if laenge < 0.01:
                    continue
                wand = api.root.create_entity(f, ifc_class="IfcWall",
                                              name=f"Außenwand {g.name}")
                rep = api.geometry.add_wall_representation(
                    f, context=body, length=laenge,
                    height=g.hoehe - DECKENSTAERKE, thickness=WANDSTAERKE)
                api.geometry.assign_representation(f, product=wand, representation=rep)
                api.geometry.edit_object_placement(
                    f, product=wand,
                    matrix=_matrix(x0, y0, g.ok_fussboden + DECKENSTAERKE,
                                   math.atan2(y1 - y0, x1 - x0)))
                elemente.append(wand)

        raum = api.root.create_entity(f, ifc_class="IfcSpace", name=f"BGF {g.name}")
        api.aggregate.assign_object(f, products=[raum], relating_object=storey)
        pset = api.pset.add_pset(f, product=raum, name="Pset_SpaceCommon")
        api.pset.edit_pset(f, pset=pset, properties={"Reference": g.name})
        qto = api.pset.add_qto(f, product=raum, name="Qto_SpaceBaseQuantities")
        api.pset.edit_qto(f, qto=qto, properties={
            "GrossFloorArea": round(g.flaeche.area, 2),
            "Height": g.hoehe,
        })
        if elemente:
            api.spatial.assign_container(f, products=elemente, relating_structure=storey)

    kennz = api.pset.add_pset(f, product=gebaeude, name="Bebauungsstudie_Kennzahlen")
    props = {}
    for name, e in studie.werte.items():
        if isinstance(e.wert, (int, float)):
            quellen = ", ".join(str(q) for q in e.quellen)
            props[name] = f"{e.wert} ({quellen})"
    api.pset.edit_pset(f, pset=kennz, properties=props)

    pfad = Path(pfad)
    f.write(str(pfad))
    return pfad
