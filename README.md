# Bebauungsstudien für Wien

Software, die für ein Wiener Grundstück aus Flächenwidmungs- und Bebauungsplan
das zulässige Bauvolumen und die wichtigsten Kennzahlen (bebaute Fläche, BGF,
Nutzfläche, Wohnungen, Stellplätze, Grünflächen) ableitet. Jede Zahl trägt
ihre Rechtsquelle und Begründung.

Zielgruppe der ersten Version: Projektentwickler und Investoren.
Konzept: [Konzept: Automatisierte Bebauungsstudien Wien](https://claude.ai/artifact/SVBQ9UzVzfHjgBvFgZPS6V)

> Ergebnisse sind eine Vorabschätzung und keine Rechtsauskunft. Verbindlich
> sind die beschlossenen Plandokumente und die Entscheidung der Behörde.

## Stand (Version 0.1)

| Regel | Quelle | Status |
| --- | --- | --- |
| Höhe je Bauklasse, Straßenbreite, Schutzzone, Gartensiedlung | BO § 75 | umgesetzt |
| Vorgarten, Abstände offene Bauweise, Begrünung, Bäume | BO § 79 | umgesetzt (ohne Heranrücken) |
| Gebäudeumriss, Dachabschluss, Dachgeschoße | BO § 81 | Näherung |
| Pflichtstellplätze, Stellplatzregulativ | WGarG §§ 48, 50 | umgesetzt |
| Eckregel | BO § 75 Abs. 5 | offen |
| gekuppelte und Gruppenbauweise | BO § 76 | konservativ wie offen |
| Datenimport Stadt Wien (OGD) und Kataster | | offen |
| Besondere Bestimmungen aus Plandokumenten | | offen |
| OIB-Richtlinien (Gebäudeklasse, Stiegenhäuser) | | offen |

Die Regelwerte sind aus den Gesetzestexten übernommen und müssen vor dem
produktiven Einsatz fachlich gegengelesen werden.

## Loslegen

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python beispiele/beispiel.py
```

## Aufbau

- `src/bebauungsstudie/regeln/`: je Paragraph ein Modul
- `src/bebauungsstudie/studie.py`: Hüllkörper und Kennzahlen für einen Bauplatz
- `src/bebauungsstudie/herleitung.py`: Ergebnis mit Quelle und Begründung
- `tests/`: Testfälle je Regel

## Datenquellen

Flächenwidmungs- und Bebauungsplan: Datenquelle Stadt Wien – data.wien.gv.at (CC BY 4.0).
