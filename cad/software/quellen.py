"""
Ereignisquellen für die Anzeige. Alles landet als dict in einer gemeinsamen Warteschlange:
  {"type": "punch", "side": "left", "valid": True, "speed_ms": 5.1, ...}   – vom Pico (oder simuliert)
  {"type": "knopf", "name": "START"}                                       – Arcade-Knöpfe / Tastatur
Knopfnamen: ZURUECK, LINKS, START, RECHTS, OK (Reihenfolge wie auf dem Pult).
"""
import json
import queue
import random
import threading
import time

KNOEPFE = ["ZURUECK", "LINKS", "START", "RECHTS", "OK"]


class PicoQuelle(threading.Thread):
    """Liest JSON-Zeilen vom Pico über USB-Seriell. Sucht den Port selbst und verbindet neu,
    wenn das Kabel kurz weg war."""

    def __init__(self, ziel: queue.Queue, port=None):
        super().__init__(daemon=True)
        self.ziel, self.port = ziel, port
        self.verbunden = False

    def _port_finden(self):
        if self.port:
            return self.port
        from serial.tools import list_ports
        for p in list_ports.comports():
            if p.vid == 0x2E8A or "ACM" in p.device or "Pico" in (p.description or ""):   # 0x2E8A = Raspberry Pi
                return p.device
        return None

    def run(self):
        import serial
        while True:
            port = self._port_finden()
            if not port:
                self.verbunden = False
                time.sleep(1)
                continue
            try:
                with serial.Serial(port, 115200, timeout=1) as s:
                    self.verbunden = True
                    for zeile in s:
                        try:
                            ereignis = json.loads(zeile.decode("utf-8", "replace"))
                        except ValueError:
                            continue
                        if isinstance(ereignis, dict) and ereignis.get("type") == "punch":
                            self.ziel.put(ereignis)
            except (OSError, serial.SerialException):
                self.verbunden = False
                time.sleep(1)


class SimQuelle:
    """Schläge per Tastatur, für Tests ohne Hardware:
    Q = links, P = rechts (gültig, zufällige Geschwindigkeit), X = ungültig."""

    def __init__(self, ziel: queue.Queue):
        self.ziel = ziel
        self.verbunden = True

    def schlag(self, seite, gueltig=True, kmh=None):
        kmh = kmh if kmh is not None else random.uniform(12, 38)
        e = {"type": "punch", "side": seite, "valid": gueltig}
        if gueltig:
            e.update(speed_ms=round(kmh / 3.6, 2), speed_kmh=round(kmh, 1))
        else:
            e["reason"] = "stopped_between"
        self.ziel.put(e)


def tastatur_knopf(taste, pygame):
    """Tastatur als Ersatz für die Arcade-Knöpfe."""
    return {pygame.K_BACKSPACE: "ZURUECK", pygame.K_ESCAPE: "ZURUECK", pygame.K_LEFT: "LINKS",
            pygame.K_SPACE: "START", pygame.K_RIGHT: "RECHTS", pygame.K_RETURN: "OK"}.get(taste)


def gamepad_knopf(nummer, belegung):
    """Gamepad-Knopf (USB-Encoder) -> Name; Belegung aus den Einstellungen (Knopfnummer je Name)."""
    for name, n in belegung.items():
        if n == nummer:
            return name
    return None
