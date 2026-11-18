# Bebauungsstudie Olbrichgasse 9, 1120 Wien

Vorabschätzung, keine Rechtsauskunft. Datenquelle: Stadt Wien – data.wien.gv.at (CC BY 4.0).

## Aus den Stadt-Wien-Daten (automatisch)

- Gefundene Adresse: 9, Olbrichgasse, Katastralgemeinde Hetzendorf, Meidling, Wien, 1120, Österreich (x=-2309.3, y=336954.0, EPSG:31256)
- Widmung: W1 – Wohngebiet Bauklasse 1
- Bauklasse: I
- Schutzzone: nein · Wohnzone: nein · Bausperre: nein
- Stellplatzzone (WGarG § 50a): 2
- Bestand im Umkreis von 20 m: 5 Gebäudeteile, Höhen 2.4 m, 4.7 m, 4.3 m, 6.9 m, 1.7 m

## Eingaben und Annahmen (nicht in den offenen Daten)

- Grundstück: 20.0 m breit × 40.0 m tief (Rechteck, Annahme)
- Bauweise: o (Annahme, im Plandokument prüfen)
- Abstand der Fluchtlinien: unbekannt m
- Besondere Bestimmungen des Plandokuments: nicht berücksichtigt

## Protokoll

- Adresssuche Stadt Wien: HTTPError: HTTP Error 404: Not Found
- Adresssuche OpenStreetMap: 1 Treffer
- Widmung: W1 (Wohngebiet Bauklasse 1)
- Schutzzone: nein, Wohnzone: nein
- Bausperre: nein
- Stellplatzzone: 2
- Bestand im Umkreis von 20 m: 5 Gebäudeteile

## Ergebnis

```
Bebauungsstudie (Vorabschätzung, keine Rechtsauskunft)

Bauplatzfläche m²: 800.0  [Eingabe Grundstücksgeometrie]  aus Geometrie
Bebaute Fläche m²: 232.0  [BO für Wien § 79 Abs. 1, 3]  Bauplatz abzüglich Vorgarten und Abstandsflächen
Gebäudehöhe m: 9.0  [BO für Wien § 75 Abs. 2]  maßgeblich: Bauklasse I mit 9.0 m
Vollgeschoße: 3  [BO für Wien § 75 Abs. 2]  9.0 m / 3.0 m Geschoßhöhe (Annahme), abgerundet
Dachgeschoße: [3.0]  [BO für Wien § 81 Abs. 1, 4]  Trakttiefe 8.0 m, Umriss 45.0°, bis 4.5 m über GH: 1 Dachgeschoß(e)
BGF m²: 768.0  [BO für Wien § 75 Abs. 2, BO für Wien § 81 Abs. 4, BO für Wien § 81 Abs. 1]  232.0 m² × 3 Vollgeschoße + 72.0 m² Dachgeschoße
Nutzfläche m²: 576.0  [Annahme Nutzflächenfaktor]  BGF × 0.75
Wohnungen: 8  [Annahme Wohnungsgröße]  576 m² / 65.0 m² je Wohnung
Pflichtstellplätze: 5  [WGarG 2008 § 50]  576 m² WNF / 100 = 5 Regelbedarf, × 100 % = 5
Freifläche m²: 568.0  [BO für Wien § 79]  Bauplatz minus bebaute Fläche
davon unversiegelt mind. m²: 378.7  [BO für Wien § 79 Abs. 6]  2/3 von 568.0 m² = 378.7 m²
Bäume: 3  [BO für Wien § 79 Abs. 7]  568.0 m² / 200 m², aufgerundet = 3

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