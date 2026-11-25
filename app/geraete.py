"""Selbsttest: welche erwartete Hardware fehlt gerade? Billig genug für jeden Frame, Ergebnis gilt 3 s."""
from pathlib import Path

from pico import NAME

PRUEF_S = 3.0


def _datei(pfad, *worte):
    """None, wenn es die Datei nicht gibt (kein Linux): dann gilt das Gerät als nicht prüfbar, nicht als fehlend."""
    try:
        text = Path(pfad).read_text(errors="ignore").lower()
    except OSError:
        return None
    return any(w in text for w in worte)


ERWARTET = (
    ("LAUTSPRECHER", lambda app: _datei("/proc/asound/cards", "usb-audio")),
    ("TOUCH", lambda app: _datei("/proc/bus/input/devices", "touch")),
    ("JOYSTICK", lambda app: bool(app.input.pads)),
)


class Geraete:
    def __init__(self):
        self.t, self.liste = -PRUEF_S, []

    def fehlt(self, app, now):
        if app.sim:
            return []
        if now - self.t >= PRUEF_S:
            self.t = now
            fehlt = [] if app.st.live(now) else ["PICO"]
            fehlt += [name for name, da in ERWARTET if da(app) is False]
            if not fehlt:
                with app.st.lock:
                    fehlt = [NAME[i] for i, c in enumerate(app.st.ch) if c.dead(now)]
            self.liste = fehlt
        return self.liste

    def text(self, app, now):
        f = self.fehlt(app, now)
        return "ALLE DA" if not f else "FEHLT: " + ", ".join(f)
