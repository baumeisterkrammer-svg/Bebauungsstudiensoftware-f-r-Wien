"""Kunden-Homepage für Bebauungsstudien (Prototyp).

Ablauf: Paket wählen -> Adresse eingeben -> bezahlen (Stripe) -> Studie wird
gerechnet -> Kennzahlen und Downloads auf der Auftragsseite (Link per E-Mail).

Ohne STRIPE_SECRET_KEY läuft die Seite im Demo-Modus: keine Zahlung, die
Studie startet sofort. Mit STUDIE_DEMO_ORDNER=<ordner> wird statt der echten
Berechnung ein fertiges Beispielergebnis kopiert (zum Ausprobieren ohne
Netzzugang zu den Stadt-Wien-Daten).

Starten:  uvicorn web.app:app --reload
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

HIER = Path(__file__).resolve().parent
REPO = HIER.parent
DATEN = Path(os.environ.get("STUDIE_DATEN", REPO / "web_auftraege"))
DEMO_ORDNER = os.environ.get("STUDIE_DEMO_ORDNER")
STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
BASIS_URL = os.environ.get("BASIS_URL", "http://localhost:8000")
ANBIETER = os.environ.get("ANBIETER", "Baumeister Krammer")


@dataclass(frozen=True)
class Paket:
    id: str
    name: str
    preis_eur: int  # brutto, Platzhalter
    kurz: str
    leistungen: tuple[str, ...]
    dateien: tuple[str, ...]  # Muster der Dateien, die der Kunde bekommt
    empfohlen: bool = False


PAKETE: dict[str, Paket] = {p.id: p for p in (
    Paket("basis", "Basis", 29, "Schnelle Ersteinschätzung",
          ("Widmung, Bauklasse, Bauweise", "Bebaubare Fläche, Höhe, Geschoße",
           "BGF, Nutzfläche, Wohnungen, Stellplätze", "Ausschnitt Flächenwidmungs- und Bebauungsplan",
           "Jede Zahl mit Rechtsquelle"),
          ("bericht.txt", "ergebnis.md", "bebauungsplan_*.png")),
    Paket("standard", "Standard", 49, "Für Ankauf und Bankgespräch",
          ("Alles aus Basis", "Pläne als PDF: Lageplan, Schnitt, Ansicht",
           "Axonometrie des Baukörpers", "Bilder (PNG) für Exposé und Präsentation"),
          ("bericht.txt", "ergebnis.md", "bebauungsplan_*.png", "plaene.pdf", "lageplan.png",
           "schnitt.png", "ansicht.png", "axonometrie.png"), empfohlen=True),
    Paket("profi", "Profi", 69, "Für Planer und Weiterbearbeitung",
          ("Alles aus Standard", "3D-Modell IFC (BIM) mit Geschoßen und Flächen",
           "DXF für CAD mit Layern je Bauteil"),
          ("*",)),
)}

KENNZAHLEN = ("Bauplatzfläche m²", "Bebaute Fläche m²", "Gebäudehöhe m", "Vollgeschoße",
              "BGF m²", "Nutzfläche m²", "Wohnungen", "Pflichtstellplätze", "Freifläche m²", "Bäume")

app = FastAPI(title="Bebauungsstudie Wien")
app.mount("/static", StaticFiles(directory=HIER / "static"), name="static")
vorlagen = Jinja2Templates(directory=HIER / "templates")
vorlagen.env.globals.update(anbieter=ANBIETER, demo=not STRIPE_KEY)


# ---------------------------------------------------------------- Aufträge

@dataclass
class Auftrag:
    id: str
    paket: str
    adresse: str
    email: str
    grundstuecke: str = ""
    status: str = "offen"  # offen -> bezahlt -> rechnet -> fertig | fehler
    erstellt: float = field(default_factory=time.time)
    meldung: str = ""

    @property
    def ordner(self) -> Path:
        return DATEN / self.id

    def speichern(self) -> None:
        self.ordner.mkdir(parents=True, exist_ok=True)
        (self.ordner / "auftrag.json").write_text(json.dumps(asdict(self), ensure_ascii=False))

    @classmethod
    def laden(cls, aid: str) -> "Auftrag":
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", aid):
            raise HTTPException(404)
        f = DATEN / aid / "auftrag.json"
        if not f.exists():
            raise HTTPException(404)
        return cls(**json.loads(f.read_text()))


def _rechnen(a: Auftrag) -> None:
    a.status = "rechnet"
    a.speichern()
    ziel = a.ordner / "ergebnis"
    try:
        if DEMO_ORDNER:
            time.sleep(2)
            shutil.copytree(DEMO_ORDNER, ziel, dirs_exist_ok=True)
        else:
            cmd = [sys.executable, str(REPO / "scripts" / "studie_adresse.py"), a.adresse, str(ziel)]
            if a.grundstuecke:
                cmd += ["--grundstuecke", a.grundstuecke]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                               env={**os.environ, "PYTHONPATH": str(REPO / "src")})
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "Fehler")
        if not (ziel / "ergebnis.md").exists():
            raise RuntimeError("kein Ergebnis erzeugt")
        a.status = "fertig"
        _sende_mail(a)
    except Exception as e:  # noqa: BLE001
        a.status, a.meldung = "fehler", f"{type(e).__name__}: {e}"
    a.speichern()


def starte_berechnung(a: Auftrag) -> None:
    a.status = "bezahlt"
    a.speichern()
    threading.Thread(target=_rechnen, args=(a,), daemon=True).start()


def _sende_mail(a: Auftrag) -> None:
    """Platzhalter: hier später den Download-Link per E-Mail schicken (z. B. SMTP)."""
    link = f"{BASIS_URL}/auftrag/{a.id}"
    (a.ordner / "mail.txt").write_text(
        f"An: {a.email}\nBetreff: Ihre Bebauungsstudie {a.adresse}\n\n"
        f"Ihre Bebauungsstudie ist fertig: {link}\n", encoding="utf-8")


def erlaubte_dateien(a: Auftrag) -> list[Path]:
    ziel = a.ordner / "ergebnis"
    if not ziel.exists():
        return []
    muster = PAKETE[a.paket].dateien
    alle = sorted(p for p in ziel.iterdir() if p.is_file() and not p.name.startswith("fluchtlinien_roh"))
    return [p for p in alle if any(p.match(m) for m in muster)]


def lies_kennzahlen(a: Auftrag) -> tuple[list[tuple[str, str, str]], dict[str, str], list[str]]:
    """Kennzahlen (Name, Wert, Quelle), Standortdaten und Hinweise aus ergebnis.md."""
    f = a.ordner / "ergebnis" / "ergebnis.md"
    if not f.exists():
        return [], {}, []
    text = f.read_text(encoding="utf-8")
    werte = []
    for z in text.splitlines():
        m = re.match(r"^(.+?): (.+?)\s+\[(.+?)\]", z)
        if m and m.group(1) in KENNZAHLEN:
            werte.append((m.group(1), m.group(2), m.group(3)))
    standort = {}
    for key, label in (("Widmung", "Widmung"), ("Bauklasse", "Bauklasse"), ("Bauweise", "Bauweise"),
                       ("Grundstück", "Grundstück"), ("Schutzzone", "Schutzzone")):
        m = re.search(rf"^- {key}: (.+)$", text, re.M)
        if m:
            standort[label] = m.group(1)
    hinweise = []
    if "Hinweise:" in text:
        teil = text.split("Hinweise:", 1)[1].split("```", 1)[0]
        hinweise = [z[2:] for z in teil.splitlines() if z.startswith("- ")]
    return werte, standort, hinweise


# ---------------------------------------------------------------- Seiten

@app.get("/", response_class=HTMLResponse)
def startseite(request: Request):
    return vorlagen.TemplateResponse(request, "start.html", {"pakete": PAKETE.values()})


@app.get("/bestellen", response_class=HTMLResponse)
def bestellen_formular(request: Request, paket: str = "standard"):
    if paket not in PAKETE:
        paket = "standard"
    return vorlagen.TemplateResponse(request, "bestellen.html",
                                     {"pakete": PAKETE.values(), "gewaehlt": paket, "fehler": None})


@app.post("/bestellen")
def bestellen(request: Request, paket: str = Form(...), adresse: str = Form(...),
              email: str = Form(...), grundstuecke: str = Form(""), agb: str = Form("")):
    fehler = None
    if paket not in PAKETE:
        fehler = "Bitte ein Paket wählen."
    elif len(adresse.strip()) < 5 or "wien" not in adresse.lower() and not re.search(r"\b1\d{2}0\b", adresse):
        fehler = "Bitte eine Wiener Adresse mit Postleitzahl eingeben, z. B. „Olbrichgasse 9, 1120 Wien“."
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
        fehler = "Bitte eine gültige E-Mail-Adresse eingeben."
    elif not agb:
        fehler = "Bitte AGB und Hinweis zur Vorabschätzung bestätigen."
    if fehler:
        return vorlagen.TemplateResponse(
            request, "bestellen.html",
            {"pakete": PAKETE.values(), "gewaehlt": paket, "fehler": fehler,
             "adresse": adresse, "email": email, "grundstuecke": grundstuecke}, status_code=400)

    a = Auftrag(id=secrets.token_urlsafe(18), paket=paket, adresse=adresse.strip(),
                email=email.strip(), grundstuecke=grundstuecke.strip())
    a.speichern()
    if not STRIPE_KEY:  # Demo-Modus
        starte_berechnung(a)
        return RedirectResponse(f"/auftrag/{a.id}", status_code=303)
    return RedirectResponse(_stripe_checkout(a), status_code=303)


@app.get("/auftrag/{aid}", response_class=HTMLResponse)
def auftrag(request: Request, aid: str):
    a = Auftrag.laden(aid)
    werte, standort, hinweise = lies_kennzahlen(a) if a.status == "fertig" else ([], {}, [])
    return vorlagen.TemplateResponse(request, "auftrag.html", {
        "a": a, "paket": PAKETE[a.paket], "werte": werte, "standort": standort,
        "hinweise": hinweise, "dateien": erlaubte_dateien(a) if a.status == "fertig" else [],
        "bilder": [p for p in erlaubte_dateien(a) if p.suffix == ".png"] if a.status == "fertig" else []})


@app.get("/auftrag/{aid}/datei/{name}")
def datei(aid: str, name: str):
    a = Auftrag.laden(aid)
    for p in erlaubte_dateien(a):
        if p.name == name:
            return FileResponse(p, filename=p.name)
    raise HTTPException(404)


@app.get("/auftrag/{aid}/alles.zip")
def alles_zip(aid: str):
    a = Auftrag.laden(aid)
    dateien = erlaubte_dateien(a)
    if a.status != "fertig" or not dateien:
        raise HTTPException(404)
    z = a.ordner / f"bebauungsstudie_{a.paket}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in dateien:
            zf.write(p, p.name)
    return FileResponse(z, filename=f"Bebauungsstudie_{re.sub(r'[^A-Za-z0-9]+', '_', a.adresse)}.zip")


@app.get("/impressum", response_class=HTMLResponse)
def impressum(request: Request):
    return vorlagen.TemplateResponse(request, "rechtliches.html", {"titel": "Impressum"})


@app.get("/agb", response_class=HTMLResponse)
def agb(request: Request):
    return vorlagen.TemplateResponse(request, "rechtliches.html", {"titel": "AGB"})


@app.get("/datenschutz", response_class=HTMLResponse)
def datenschutz(request: Request):
    return vorlagen.TemplateResponse(request, "rechtliches.html", {"titel": "Datenschutz"})


# ---------------------------------------------------------------- Stripe

def _stripe_checkout(a: Auftrag) -> str:
    import httpx
    p = PAKETE[a.paket]
    r = httpx.post("https://api.stripe.com/v1/checkout/sessions", auth=(STRIPE_KEY, ""), data={
        "mode": "payment",
        "customer_email": a.email,
        "client_reference_id": a.id,
        "line_items[0][quantity]": 1,
        "line_items[0][price_data][currency]": "eur",
        "line_items[0][price_data][unit_amount]": p.preis_eur * 100,
        "line_items[0][price_data][product_data][name]": f"Bebauungsstudie {p.name}: {a.adresse}",
        "invoice_creation[enabled]": "true",
        "success_url": f"{BASIS_URL}/auftrag/{a.id}",
        "cancel_url": f"{BASIS_URL}/bestellen?paket={a.paket}",
    }, timeout=20)
    r.raise_for_status()
    return r.json()["url"]


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    import hashlib
    import hmac
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")
    teile = dict(t.split("=", 1) for t in sig.split(",") if "=" in t)
    erwartet = hmac.new(STRIPE_WEBHOOK_SECRET.encode(), f"{teile.get('t', '')}.".encode() + body,
                        hashlib.sha256).hexdigest()
    if not STRIPE_WEBHOOK_SECRET or not hmac.compare_digest(erwartet, teile.get("v1", "")):
        raise HTTPException(400, "Signatur ungültig")
    ev = json.loads(body)
    if ev.get("type") == "checkout.session.completed":
        a = Auftrag.laden(ev["data"]["object"]["client_reference_id"])
        if a.status == "offen":
            starte_berechnung(a)
    return {"ok": True}
