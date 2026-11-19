# Kunden-Homepage (Prototyp)

Kunden wählen ein Paket (Basis, Standard, Profi), geben eine Wiener Adresse ein,
bezahlen über Stripe und bekommen Kennzahlen und Dateien zum Download.

## Lokal ausprobieren

```bash
pip install -e . -r web/requirements.txt
# Demo ohne Zahlung, echte Berechnung (braucht Internet zu data.wien.gv.at und BEV):
uvicorn web.app:app --reload
# Demo mit fertigem Beispielergebnis statt Berechnung:
STUDIE_DEMO_ORDNER=pfad/zu/einem/ergebnisordner uvicorn web.app:app --reload
```

Dann http://localhost:8000 öffnen.

## Einstellungen (Umgebungsvariablen)

| Variable | Bedeutung |
| --- | --- |
| `STRIPE_SECRET_KEY` | Stripe-Schlüssel. Ohne ihn läuft die Seite im Demo-Modus ohne Zahlung. |
| `STRIPE_WEBHOOK_SECRET` | Signatur für `/stripe/webhook` (Ereignis `checkout.session.completed`) |
| `BASIS_URL` | öffentliche Adresse der Seite, z. B. `https://bebauungsstudie-wien.at` |
| `STUDIE_DATEN` | Ordner für Aufträge und Ergebnisse (Standard `web_auftraege/`) |
| `ANBIETER` | Name im Fußbereich |

Preise und Paketinhalte stehen in `web/app.py` unter `PAKETE`.

## Noch offen vor dem Start

- E-Mail-Versand des Download-Links (derzeit nur als `mail.txt` im Auftragsordner)
- Impressum, AGB, Datenschutz (Platzhalterseiten)
- Hosting mit Tesseract für die Texterkennung, HTTPS, Domain
