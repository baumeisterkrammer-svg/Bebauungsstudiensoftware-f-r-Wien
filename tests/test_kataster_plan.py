from shapely.geometry import Polygon, box

from bebauungsstudie.daten import bebauungsplan, kataster


def test_strassenkante_aus_nutzung():
    gst = Polygon([(0, 0), (20, 0), (20, 30), (0, 30)])
    strasse = box(-50, -15, 70, 0)
    garten = box(-50, 30, 70, 80)
    kanten = kataster.strassenkanten(gst, [({"NS": "95"}, strasse), ({"NS": "52"}, garten)])
    assert kanten == {0}


def test_stichtage_neueste_zuerst():
    import datetime as dt
    assert kataster._stichtage(dt.date(2026, 11, 19))[:3] == ["20261001", "20260401", "20251001"]


CAPS = """<Capabilities><Contents>
<Layer><ows:Identifier>flwbplmzk</ows:Identifier><Style isDefault="true"><ows:Identifier>normal</ows:Identifier></Style>
<TileMatrixSetLink><TileMatrixSet>google3857</TileMatrixSet></TileMatrixSetLink>
<ResourceURL format="image/jpeg" template="https://x/wmts/flwbplmzk/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg" resourceType="tile"/>
</Layer>
<TileMatrixSet><ows:Identifier>google3857</ows:Identifier><ows:SupportedCRS>urn:ogc:def:crs:EPSG:6.18.3:3857</ows:SupportedCRS>
<TileMatrix><ows:Identifier>19</ows:Identifier><ScaleDenominator>1066.3647919249</ScaleDenominator>
<TopLeftCorner>-20037508.3428 20037508.3428</TopLeftCorner><TileWidth>256</TileWidth><TileHeight>256</TileHeight>
<MatrixWidth>524288</MatrixWidth><MatrixHeight>524288</MatrixHeight></TileMatrix>
</TileMatrixSet></Contents></Capabilities>"""


def test_wmts_ebene_lesen():
    e = bebauungsplan.ebene("flwbplmzk", CAPS)
    assert e.crs == 3857 and e.stil == "normal" and e.matrixset == "google3857"
    assert abs(e.matrizen[0].aufloesung - 0.2986) < 0.001
