# Bebauungsstudie Ferrogasse 6, 1180 Wien

Vorabschätzung, keine Rechtsauskunft. Datenquellen: Stadt Wien – data.wien.gv.at, BEV – data.bev.gv.at (beide CC BY 4.0).

## Aus den Stadt-Wien-Daten (automatisch)

- Gefundene Adresse: 6, Ferrogasse, Neu-Gersthof, Katastralgemeinde Gersthof, Währing, Wien, 1180, Österreich (x=-349.3, y=343816.2, EPSG:31256)
- Widmung: W2 – Wohngebiet Bauklasse 2
- Bauklasse: II
- Schutzzone: ja · Wohnzone: nein · Bausperre: nein
- Stellplatzzone (WGarG § 50a): 2
- Bestand im Umkreis von 20 m: 19 Gebäudeteile, Höhen 15.0 m, 14.8 m, 12.9 m, 14.7 m, 10.3 m, 10.6 m, 10.8 m, 16.1 m, 11.6 m, 11.4 m, 15.0 m, 7.8 m, 10.3 m, 7.5 m, 14.5 m, 7.3 m, 11.3 m, 4.5 m, 11.4 m


## Eingaben und Annahmen (im Plandokument nur als Bild, bitte prüfen)

- Grundstück: KG 01501, Grundstück 479/2: 126 m² laut BEV-Katastralmappe (Stichtag 01.10.2026), Straßenkanten [0]
- Bauweise: g (aus der Planbeschriftung gelesen, bitte prüfen)
- Festgesetzte Gebäudehöhe: 10.5 m (aus der Planbeschriftung, bitte prüfen)
- Abstand der Fluchtlinien (Straßenbreite): 15.0 m (aus dem Planbild gemessen, schmalste angrenzende Straße)
- Bebaubare Fläche: innerhalb der aus dem Planbild erkannten Baufluchtlinien (bitte prüfen)
- Besondere Bestimmungen des Plandokuments: nicht berücksichtigt

## Protokoll

- Adresssuche Stadt Wien: HTTPError: HTTP Error 404: Not Found
- Adresssuche OpenStreetMap: 1 Treffer
- Widmung: W2 (Wohngebiet Bauklasse 2)
- Schutzzone: ja, Wohnzone: nein
- Bausperre: nein
- Stellplatzzone: 2
- Bestand im Umkreis von 20 m: 19 Gebäudeteile
- Kataster: KG 01501, Gst. 479/2, 126 m² (BEV DKM Stichtag 01.10.2026, CC BY 4.0)
- Kataster: Nutzung Gebäude 122 m², Gebäudenebenfläche 4 m²; Straßenkanten [0]; Nachbargrundstücke 481/2 (115 m²), 479/1 (92 m²), 476 (391 m²)
- Kataster: Das Grundstück am Adresspunkt ist fast ganz überbaut. Der Bauplatz umfasst vermutlich weitere Grundstücke derselben Einlagezahl; bitte prüfen.
- Fluchtlinien-Bild: 768×512 px, 0.20 m/px, rote Pixel 7.0%
- Linien 4.8%, Schrift 2.2% der Bildfläche
- Baufluchtlinien: geschlossene Fläche 1780 m² erkannt, davon 113 m² im Grundstück
- Straßenkante 0: Abstand der Baulinien ca. 15.0 m (Messungen 15.0, 15.0, 15.0, 15.0, 15.0)
- Planbeschriftung: %, &, 00, 002, 00S, 00¢, 105m, 2, 2,00, 2.00, 200, 4, 5, 5m, 6, 7, 8, 9, 99, =, >, BR, G, M4, My, OG, Op, Oy, RY, S, V, VE, VL, Ve, W, WW, Wg, \N, g, ges
- Bauweise „g“ aus der Planbeschriftung gelesen (4 m vom Grundstück, innerhalb derselben Baufluchtlinien)
- Gebäudehöhe 10.5 m aus der Planbeschriftung gelesen (45 m vom Grundstück)
- Bebauungsplan: Ausschnitt als Bild beigelegt

## Ergebnis

```
Bebauungsstudie (Vorabschätzung, keine Rechtsauskunft)

Bauplatzfläche m²: 126.0  [Eingabe Grundstücksgeometrie]  aus Geometrie
Bebaute Fläche m²: 113.1  [BO für Wien § 79 Abs. 1, 3, Bebauungsplan Baufluchtlinien (§ 5 Abs. 4 BO)]  innerhalb der Baufluchtlinien laut Bebauungsplan, abzüglich Abstandsflächen
Gebäudehöhe m: 10.5  [BO für Wien § 75 Abs. 2, Bebauungsplan Besondere Bestimmung]  maßgeblich: im Bebauungsplan festgesetzte Höhe mit 10.5 m
Vollgeschoße: 3  [BO für Wien § 75 Abs. 2, Bebauungsplan Besondere Bestimmung]  10.5 m / 3.0 m Geschoßhöhe (Annahme), abgerundet
Dachgeschoße: [7.06]  [BO für Wien § 81 Abs. 1, 4]  Trakttiefe 12.064014850941021 m, Umriss 45.0°, bis 9.0 m über GH: 1 Dachgeschoß(e)
BGF m²: 404.8  [BO für Wien § 75 Abs. 2, Bebauungsplan Besondere Bestimmung, BO für Wien § 81 Abs. 4, BO für Wien § 81 Abs. 1]  113.1 m² × 3 Vollgeschoße + 65.4 m² Dachgeschoße
Nutzfläche m²: 303.6  [Annahme Nutzflächenfaktor]  BGF × 0.75
Wohnungen: 4  [Annahme Wohnungsgröße]  304 m² / 65.0 m² je Wohnung
Pflichtstellplätze: 3  [WGarG 2008 § 50]  304 m² WNF / 100 = 3 Regelbedarf, × 100 % = 3
Freifläche m²: 12.9  [BO für Wien § 79]  Bauplatz minus bebaute Fläche
davon unversiegelt mind. m²: 8.6  [BO für Wien § 79 Abs. 6]  2/3 von 12.9 m² = 8.6 m²
Bäume: 1  [BO für Wien § 79 Abs. 7]  12.9 m² / 200 m², aufgerundet = 1

Hinweise:
- Geschlossene Bauweise: hintere Baufluchtlinie aus dem Plandokument muss ergänzt werden.
- Geschlossene Bauweise: Dachgeschoße reichen von Nachbar zu Nachbar, der Umriss steigt nur von Straßen- und Hoffront an (§ 81).
- Stellplatzzone 2: mögliche Reduktion der Pflichtstellplätze nach WGarG § 50a ist noch nicht eingerechnet.
- Schutzzone: Straßenbreite begrenzt die Höhe nicht (§ 75 Abs. 6).
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