# Bebauungsstudie Olbrichgasse 9, 1120 Wien

Vorabschätzung, keine Rechtsauskunft. Datenquellen: Stadt Wien – data.wien.gv.at, BEV – data.bev.gv.at (beide CC BY 4.0).

## Aus den Stadt-Wien-Daten (automatisch)

- Gefundene Adresse: 9, Olbrichgasse, Katastralgemeinde Hetzendorf, Meidling, Wien, 1120, Österreich (x=-2309.3, y=336954.0, EPSG:31256)
- Widmung: W1 – Wohngebiet Bauklasse 1
- Bauklasse: I
- Schutzzone: nein · Wohnzone: nein · Bausperre: nein
- Stellplatzzone (WGarG § 50a): 2
- Bestand im Umkreis von 20 m: 5 Gebäudeteile, Höhen 2.4 m, 4.7 m, 4.3 m, 6.9 m, 1.7 m


## Eingaben und Annahmen (im Plandokument nur als Bild, bitte prüfen)

- Grundstück: KG 01304, Grundstück 453/47, 453/16: 692 m² laut BEV-Katastralmappe (Stichtag 01.10.2026), Straßenkanten [0, 3, 4]
- Bauweise: o (aus der Planbeschriftung gelesen, bitte prüfen)
- Abstand der Fluchtlinien (Straßenbreite): 12.0 m (aus dem Planbild gemessen, schmalste angrenzende Straße)
- Bebaubare Fläche: innerhalb der aus dem Planbild erkannten Baufluchtlinien (bitte prüfen)
- Besondere Bestimmungen des Plandokuments: nicht berücksichtigt

## Protokoll

- Adresssuche Stadt Wien: HTTPError: HTTP Error 404: Not Found
- Adresssuche OpenStreetMap: 1 Treffer
- Widmung: W1 (Wohngebiet Bauklasse 1)
- Schutzzone: nein, Wohnzone: nein
- Bausperre: nein
- Stellplatzzone: 2
- Bestand im Umkreis von 20 m: 5 Gebäudeteile
- Kataster: KG 01304, Gst. 453/47, 111 m² (BEV DKM Stichtag 01.10.2026, CC BY 4.0)
- Kataster: Nutzung Gebäude 111 m²; Straßenkanten keine erkannt; Nachbargrundstücke 453/16 (581 m²)
- Kataster: Grundstück 453/47 ist überbaut und grenzt nicht an die Straße; mit dem einzigen Nachbargrundstück 453/16 zum Bauplatz zusammengelegt (bitte prüfen).
- Kataster: Nutzung Gebäude 111 m², Garten 580 m²; Straßenkanten [0, 3, 4]; Nachbargrundstücke 453/15 (883 m²), 453/17 (544 m²)
- Fluchtlinien-Bild: 768×768 px, 0.20 m/px, rote Pixel 4.4%
- Baufluchtlinien: geschlossene Fläche 1048 m² erkannt, davon 272 m² im Grundstück
- Straßenkante 0: Abstand der Baulinien ca. 24.5 m (Messungen 24.3, 24.3, 24.3, 24.2, 24.2)
- Straßenkante 3: Abstand der Baulinien ca. 12.0 m (Messungen 12.0, 12.0, 3.7, 3.6, 12.1)
- Straßenkante 4: Abstand der Baulinien ca. 12.0 m (Messungen 11.9, 11.9, 11.9, 12.0, 11.8)
- Planbeschriftung: &, ,, 02, 1, 16, 2, 20, 45,, 6, 6.8m, 7, 9, >, @, De,, KK, OZ, TH, W,, Wi, Wy, \, g, naw, o, ov, we, wn, x,, |, ©, °, —, ‘, ‘cam
- Bauweise „o“ aus der Planbeschriftung gelesen (38 m vom Grundstück, innerhalb derselben Baufluchtlinien)
- Bebauungsplan: Ausschnitt als Bild beigelegt

## Ergebnis

```
Bebauungsstudie (Vorabschätzung, keine Rechtsauskunft)

Bauplatzfläche m²: 691.5  [Eingabe Grundstücksgeometrie]  aus Geometrie
Bebaute Fläche m²: 183.3  [BO für Wien § 79 Abs. 1, 3, Bebauungsplan Baufluchtlinien (§ 5 Abs. 4 BO)]  innerhalb der Baufluchtlinien laut Bebauungsplan, abzüglich Abstandsflächen
Gebäudehöhe m: 9.0  [BO für Wien § 75 Abs. 2, BO für Wien § 75 Abs. 4]  maßgeblich: Bauklasse I mit 9.0 m
Vollgeschoße: 3  [BO für Wien § 75 Abs. 2, BO für Wien § 75 Abs. 4]  9.0 m / 3.0 m Geschoßhöhe (Annahme), abgerundet
Dachgeschoße: [9.44]  [BO für Wien § 81 Abs. 1, 4]  Trakttiefe 14.444449427536313 m, Umriss 45.0°, bis 4.5 m über GH: 1 Dachgeschoß(e)
BGF m²: 622.6  [BO für Wien § 75 Abs. 2, BO für Wien § 75 Abs. 4, BO für Wien § 81 Abs. 4, BO für Wien § 81 Abs. 1]  183.3 m² × 3 Vollgeschoße + 72.7 m² Dachgeschoße
Nutzfläche m²: 466.9  [Annahme Nutzflächenfaktor]  BGF × 0.75
Wohnungen: 7  [Annahme Wohnungsgröße]  467 m² / 65.0 m² je Wohnung
Pflichtstellplätze: 4  [WGarG 2008 § 50]  467 m² WNF / 100 = 4 Regelbedarf, × 100 % = 4
Freifläche m²: 508.2  [BO für Wien § 79]  Bauplatz minus bebaute Fläche
davon unversiegelt mind. m²: 338.8  [BO für Wien § 79 Abs. 6]  2/3 von 508.2 m² = 338.8 m²
Bäume: 3  [BO für Wien § 79 Abs. 7]  508.2 m² / 200 m², aufgerundet = 3

Hinweise:
- Stellplatzzone 2: mögliche Reduktion der Pflichtstellplätze nach WGarG § 50a ist noch nicht eingerechnet.
- Dachaufbauten nach § 81 Abs. 6 nicht berücksichtigt.
- Gilt, wenn der Bebauungsplan gärtnerische Ausgestaltung vorsieht.
```

- plaene.pdf
- lageplan.png
- schnitt.png
- ansicht.png
- axonometrie.png
- modell.ifc
- plaene.dxf
- bericht.txt
- bebauungsplan_flwbplmzk.png
- bebauungsplan_flwbplflucht.png