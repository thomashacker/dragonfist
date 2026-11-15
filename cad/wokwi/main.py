# Messlogik-Prototyp für den Pico (MicroPython). Automatisch erzeugt von wokwi.py –
# Pinbelegung und Ebenenabstand kommen aus parameter.py. Läuft in Wokwi und auf dem echten Pico.
#
# Strahl frei = Pin HIGH (interner Pull-up), Strahl unterbrochen = LOW.
# Gültiger Schlag: Seite in Ebene A unterbrochen, danach B innerhalb von FENSTER_US.
# Der nächste Schlag dieser Seite zählt erst, wenn die Faust wieder vor A ist (A frei).
from machine import Pin
import neopixel
import time

ABSTAND_MM = 200          # Ebene A -> B
LED_PINS = {"left": 16, "right": 19}
LED_ANZAHL = 19
HELLIGKEIT = 0.35       # begrenzt den Strom (volle Helligkeit: 2.3 A)
BLINK_US = 200_000            # so lange leuchtet die Rückmeldung
FENSTER_US = 300_000          # max. Zeit von A bis B
ENTPRELL_US = 1_500           # Unterbrechung muss so lange stabil sein
MIN_MS = 1.0                  # langsamer = Durchschieben, zählt nicht

A_LINKS = [0, 3, 6]
A_RECHTS = [9, 12, 15]
B_STRAHLEN = [(28, -165), (27, -110), (26, -55), (21, 0), (20, 55), (18, 110), (17, 165)]       # (GPIO, Position in mm) – B wird pro Strahl ausgewertet


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


streifen = {s: neopixel.NeoPixel(Pin(p), LED_ANZAHL) for s, p in LED_PINS.items()}
aus_um = {"left": None, "right": None}


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
    print("{" + ", ".join(teile) + "}")
    if werte.get("type") == "punch":              # grün = gültig, rot = ungültig, auf der Seite des Schlags
        leuchten(werte["side"], (0, 255, 0) if werte["valid"] else (255, 0, 0))


a = {"left": Ebene(A_LINKS), "right": Ebene(A_RECHTS)}
b = [(Ebene([g]), x) for g, x in B_STRAHLEN]
zustand = {"left": "bereit", "right": "bereit"}
t_a = {"left": 0, "right": 0}
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
