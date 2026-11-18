"""
Kollisionsprüfung des Gesamtmodells:  python pruefen.py
Prüft jedes Paar fester Bauteile, ob sie sich durchdringen (Volumen > 1 mm³).
Gewollte Überschneidungen (Schraube steckt im Holz, Pfosten in der Hülse ...) stehen in ERLAUBT.
"""
import itertools

import elektronik as E
import modell as M
import pult as PU

# Teile, die sich berühren/durchdringen dürfen (Präfixe der Bauteilnamen)
ERLAUBT = [
    ("Schraube", ""),                                   # Schrauben stecken in Holz und Druckteilen
    ("IR-Strahl", ""), ("Ader", ""), ("Zuleitung", ""), ("USB-Kabel", ""), ("5-V-Netzteil", ""), ("19-V-Netzteil", ""),
    ("Schwimmnudel", ""), ("Trennung Ebene A", ""),     # weich, darf drücken
    ("Seitenbrett", "Brett"),                          # Stoß an Stoß
    ("Sensorplatte Teil 1", "Sensorplatte Teil 2"),     # Schwalbenschwanz
    ("Deckel Teil 1", "Deckel Teil 2"),
    ("Pult Boden", "Pult Gehäuse"),
    ("Schild", "Pult Gehäuse"), ("Schild", "Seitenbrett"),
]


def erlaubt(a, b):
    for x, y in ERLAUBT:
        if (a.startswith(x) and b.startswith(y)) or (b.startswith(x) and a.startswith(y)):
            return True
    return False


def pruefen():
    teile = M.rahmen() + E.schrauben() + E.elektronik() + PU.pult_teile()
    teile = [t for t in teile if not t.label.startswith(("IR-Strahl",))]
    befunde = []
    boxen = [(t, t.bounding_box()) for t in teile]
    for (a, ba), (b, bb) in itertools.combinations(boxen, 2):
        if erlaubt(a.label, b.label):
            continue
        if (ba.max.X < bb.min.X or bb.max.X < ba.min.X or ba.max.Y < bb.min.Y or bb.max.Y < ba.min.Y
                or ba.max.Z < bb.min.Z or bb.max.Z < ba.min.Z):
            continue
        try:
            v = (a & b).volume
        except Exception:                                # noqa: BLE001 – Geometriefehler als Befund melden
            v = -1
        if v > 1 or v < 0:
            befunde.append((a.label, b.label, v))
    return befunde


if __name__ == "__main__":
    b = pruefen()
    if not b:
        print("OK  keine ungewollten Überschneidungen")
    for x, y, v in sorted(b, key=lambda e: -e[2]):
        print(f"!!  {x}  <->  {y}:  {v:.0f} mm³" if v >= 0 else f"??  {x} <-> {y}: nicht prüfbar")
