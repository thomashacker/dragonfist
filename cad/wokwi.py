"""
Erzeugt ein Wokwi-Projekt (Simulation im Browser, wokwi.com) aus der Pinbelegung:
  wokwi/diagram.json  – Pico + je ein Taster pro Empfänger (Taster gedrückt = Strahl unterbrochen)
  wokwi/main.py       – MicroPython-Messlogik zum Testen (A, dann B -> Geschwindigkeit)
Wird von build.py mit aufgerufen. Die Tasten auf der Tastatur stehen in TASTEN.
"""
import json
from pathlib import Path

import elektronik as E
import modell as M
import parameter as P

ZIEL = Path(__file__).parent / "wokwi"
TASTEN = {"A": "123456789", "B": "asdfghjkl"}      # Ebene A: Zahlenreihe, Ebene B: mittlere Buchstabenreihe


def _sensoren():
    nummer = {"A": 0, "B": 0}
    liste = []
    for p in E.pin_belegung():
        nummer[p["ebene"]] += 1
        n = nummer[p["ebene"]]
        liste.append({**p, "name": f"{p['ebene']}{n}", "taste": TASTEN[p["ebene"]][n - 1]})
    return liste


def diagram():
    teile = [{"type": "wokwi-pi-pico", "id": "pico", "top": 0, "left": 0,
              "attrs": {"env": "micropython-20231227-v1.22.0"}}]
    verbindungen = []
    zeile = {"A": 0, "B": 0}
    for s in _sensoren():
        e = s["ebene"]
        links = e == "A"
        teile.append({"type": "wokwi-pushbutton", "id": f"btn{s['name']}",
                      "top": -60 + zeile[e] * 48, "left": -230 if links else 160,
                      "attrs": {"color": "red" if links else "blue", "key": s["taste"], "bounce": "0",
                                "label": f"{s['name']} ({s['x_mm']:+d}) Taste {s['taste']}"}})
        zeile[e] += 1
        seite = "r" if links else "l"
        verbindungen.append([f"btn{s['name']}:1.{seite}", f"pico:GP{s['gpio']}", "gold", []])
        verbindungen.append([f"btn{s['name']}:2.{seite}", "pico:GND.8" if links else "pico:GND.3", "black", []])
    # LED-Streifen links und rechts (WS2812B) als senkrechte NeoPixel-Reihe
    for sd, links, x in (("links", True, -420), ("rechts", False, 380)):
        teile.append({"type": "wokwi-neopixel-matrix", "id": f"led_{sd}", "top": -120, "left": x,
                      "attrs": {"rows": str(M.led_anzahl()), "cols": "1"}})
        verbindungen.append([f"led_{sd}:DIN", f"pico:GP{P.GPIO_LED[sd]}", "green", []])
        verbindungen.append([f"led_{sd}:VCC", "pico:VBUS", "red", []])
        verbindungen.append([f"led_{sd}:GND", "pico:GND.6", "black", []])
    return {"version": 1, "author": "VVD Schlag-Messgerät (automatisch erzeugt)", "editor": "wokwi",
            "parts": teile, "connections": verbindungen, "dependencies": {}}


def main_py():
    s = _sensoren()
    a_links = [x["gpio"] for x in s if x["ebene"] == "A" and x["x_mm"] < 0]
    a_rechts = [x["gpio"] for x in s if x["ebene"] == "A" and x["x_mm"] > 0]
    b = [(x["gpio"], x["x_mm"]) for x in s if x["ebene"] == "B"]
    return f'''# Messlogik-Prototyp für den Pico (MicroPython). Automatisch erzeugt von wokwi.py –
# Pinbelegung und Ebenenabstand kommen aus parameter.py. Läuft in Wokwi und auf dem echten Pico.
#
# Strahl frei = Pin HIGH (interner Pull-up), Strahl unterbrochen = LOW.
# Gültiger Schlag: Seite in Ebene A unterbrochen, danach B innerhalb von FENSTER_US.
# Der nächste Schlag dieser Seite zählt erst, wenn die Faust wieder vor A ist (A frei).
from machine import Pin
import neopixel
import time

ABSTAND_MM = {P.EBENENABSTAND_AB}          # Ebene A -> B
LED_PINS = {{"left": {P.GPIO_LED['links']}, "right": {P.GPIO_LED['rechts']}}}
LED_ANZAHL = {M.led_anzahl()}
HELLIGKEIT = {P.LED_HELLIGKEIT}       # begrenzt den Strom (volle Helligkeit: {E.led_strom_a():.1f} A)
BLINK_US = 200_000            # so lange leuchtet die Rückmeldung
FENSTER_US = 300_000          # max. Zeit von A bis B
ENTPRELL_US = 1_500           # Unterbrechung muss so lange stabil sein
MIN_MS = 1.0                  # langsamer = Durchschieben, zählt nicht

A_LINKS = {a_links}
A_RECHTS = {a_rechts}
B_STRAHLEN = {b}       # (GPIO, Position in mm) – B wird pro Strahl ausgewertet


def eingaenge(liste):
    return [Pin(g, Pin.IN, Pin.PULL_UP) for g in liste]


class Ebene:
    """Entprellter Zustand 'irgendein Strahl der Gruppe unterbrochen'."""

    def __init__(self, pins):
        self.pins = eingaenge(pins)
        self.zu = False
        self.roh = False
        self.seit = time.ticks_us()

    def lesen(self, jetzt):
        roh = any(p.value() == 0 for p in self.pins)
        if roh != self.roh:
            self.roh, self.seit = roh, jetzt
        if roh != self.zu and time.ticks_diff(jetzt, self.seit) >= ENTPRELL_US:
            self.zu = roh
            return "zu" if roh else "auf"
        return None


streifen = {{s: neopixel.NeoPixel(Pin(p), LED_ANZAHL) for s, p in LED_PINS.items()}}
aus_um = {{"left": None, "right": None}}


def leuchten(seite, farbe):
    f = tuple(int(c * HELLIGKEIT) for c in farbe)
    streifen[seite].fill(f)
    streifen[seite].write()
    aus_um[seite] = time.ticks_add(time.ticks_us(), BLINK_US) if farbe != (0, 0, 0) else None


def melden(**werte):
    teile = []
    for k, v in werte.items():
        teile.append('"%s": %s' % (k, ('"%s"' % v) if isinstance(v, str) else
                                   ("true" if v is True else "false" if v is False else v)))
    print("{{" + ", ".join(teile) + "}}")
    if werte.get("type") == "punch":              # grün = gültig, rot = ungültig, auf der Seite des Schlags
        leuchten(werte["side"], (0, 255, 0) if werte["valid"] else (255, 0, 0))


a = {{"left": Ebene(A_LINKS), "right": Ebene(A_RECHTS)}}
b = [(Ebene([g]), x) for g, x in B_STRAHLEN]
zustand = {{"left": "bereit", "right": "bereit"}}
t_a = {{"left": 0, "right": 0}}
melden(type="start", abstand_mm=ABSTAND_MM, fenster_ms=FENSTER_US // 1000)

while True:
    jetzt = time.ticks_us()
    for s in aus_um:
        if aus_um[s] is not None and time.ticks_diff(jetzt, aus_um[s]) >= 0:
            leuchten(s, (0, 0, 0))
    # B pro Strahl: so löst auch die zweite Faust ein eigenes Ereignis aus, wenn die erste noch drin ist
    b_neu = [x for strahl, x in b if strahl.lesen(jetzt) == "zu"]
    for seite in ("left", "right"):
        e = a[seite].lesen(jetzt)
        if zustand[seite] == "bereit" and e == "zu":
            zustand[seite], t_a[seite] = "laeuft", jetzt
        elif zustand[seite] == "laeuft":
            if e == "auf":                                   # wieder raus, ohne B zu erreichen
                melden(type="punch", side=seite, valid=False, reason="stopped_between", t_us=jetzt)
                zustand[seite] = "bereit"
            elif time.ticks_diff(jetzt, t_a[seite]) > FENSTER_US:
                melden(type="punch", side=seite, valid=False, reason="too_slow", t_us=jetzt)
                zustand[seite] = "warten"
        elif zustand[seite] == "warten" and not a[seite].zu:
            zustand[seite] = "bereit"                         # zurückgezogen bis vor A
    for x in b_neu:
        # B gehört zu einer Seite, die noch auf B wartet – bevorzugt die Seite, auf der der Strahl liegt,
        # sonst die, die am längsten in A ist
        offen = [s for s in ("left", "right") if zustand[s] == "laeuft"]
        if offen:
            passend = [s for s in offen if x != 0 and (s == "left") == (x < 0)]
            seite = min(passend or offen, key=lambda s: t_a[s])
            dt = time.ticks_diff(jetzt, t_a[seite])
            v = ABSTAND_MM / dt * 1000                       # mm/µs -> m/s
            if v < MIN_MS:
                melden(type="punch", side=seite, valid=False, reason="too_slow", t_us=jetzt)
            else:
                melden(type="punch", side=seite, valid=True, speed_ms=round(v, 2),
                       speed_kmh=round(v * 3.6, 1), t_us=jetzt)
            zustand[seite] = "warten"
'''


def export():
    ZIEL.mkdir(exist_ok=True)
    (ZIEL / "diagram.json").write_text(json.dumps(diagram(), indent=2, ensure_ascii=False), encoding="utf-8")
    (ZIEL / "main.py").write_text(main_py(), encoding="utf-8")
    tasten = "\n".join(f"| {s['name']} | {s['x_mm']:+d} mm | GP{s['gpio']} | `{s['taste']}` |" for s in _sensoren())
    (ZIEL / "LIESMICH.md").write_text(f"""# Wokwi-Simulation

*Automatisch erzeugt von `build.py`.*

## Öffnen
1. https://wokwi.com → **New Project** → **Raspberry Pi Pico** → **MicroPython**.
2. Tab **diagram.json**: alles ersetzen durch den Inhalt von `diagram.json` aus diesem Ordner.
3. Tab **main.py**: alles ersetzen durch `main.py` aus diesem Ordner.
4. Grünen **Start**-Knopf drücken, unten erscheint die Ausgabe.

Simuliert wird der Pico (RP2040) – Pinbelegung und MicroPython-Code sind beim Pico 2 gleich.

## Bedienung
Jeder Taster ist ein Empfänger: **gedrückt = Strahl unterbrochen**. In die Simulation klicken,
dann über die Tastatur (mehrere gleichzeitig möglich):

- **Gültiger Schlag:** z. B. `2` halten, kurz danach `s` drücken, beide loslassen.
- **Zwischen A und B gestoppt:** `2` drücken und loslassen, ohne B.
- **Fuchteln:** `2` halten, `s` tippen, `s` nochmal tippen – zählt nur einmal, erst `2` loslassen.

Die LED-Streifen links/rechts blinken **grün** bei einem gültigen, **rot** bei einem ungültigen Schlag.
Die Geschwindigkeit ist hier natürlich die deiner Finger, nicht die einer Faust.

| Sensor | Position | Pin | Taste |
|---|---|---|---|
{tasten}
""", encoding="utf-8")
    print(f"Wokwi -> {ZIEL}")


if __name__ == "__main__":
    export()
