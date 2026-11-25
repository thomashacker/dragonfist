import math
import socket
import subprocess
import threading
import time

import pygame

from splash import STATE

PRUEF_S = 10
WLAN = "802-11-wireless"


def _nmcli(*args, timeout=5):
    return subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout)


class Netz:
    """Prüft im Hintergrund, ob Internet da ist und in welchem WLAN der Jetson hängt; wechselt gespeicherte WLANs."""

    def __init__(self):
        self.online, self.ssid, self.profile, self.meldung, self.update = None, None, [], None, None
        threading.Thread(target=self._lauf, daemon=True).start()

    def _profile(self):
        try:
            zeilen = _nmcli("-t", "-f", "NAME,TYPE", "con", "show").stdout.splitlines()
        except (OSError, subprocess.SubprocessError):
            return []
        return [n.replace(r"\:", ":") for n, typ in (z.rsplit(":", 1) for z in zeilen if ":" in z) if typ == WLAN]

    def verbinden(self, name):
        self._befehl("verbinde …", "con", "up", "id", name)

    def trennen(self):
        """WLAN aus, bis wieder eins gewählt wird (zum Testen ohne Internet)."""
        try:
            dev = next(d for d, t in (z.rsplit(":", 1) for z in _nmcli("-t", "-f", "DEVICE,TYPE", "dev").stdout.split())
                       if t == "wifi")
        except (OSError, subprocess.SubprocessError, StopIteration, ValueError):
            self.meldung = "fehlgeschlagen"
            return
        self._befehl("trenne …", "dev", "disconnect", dev)

    def _befehl(self, meldung, *args):
        if self.meldung not in ("verbinde …", "trenne …"):
            self.meldung = meldung
            threading.Thread(target=self._ausfuehren, args=args, daemon=True).start()

    def _ausfuehren(self, *args):
        try:
            ok = _nmcli(*args, timeout=45).returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
        self.meldung = None if ok else "fehlgeschlagen"
        self._pruefen()

    def _pruefen(self):
        try:
            socket.create_connection(("1.1.1.1", 53), 2).close()
            self.online = True
        except OSError:
            self.online = False
        try:
            self.ssid = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True,
                                       timeout=2).stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            self.ssid = None
        self.profile = self._profile()
        try:
            self.update = (STATE / "verfuegbar").read_text(encoding="utf-8").strip() or None
        except OSError:
            self.update = None

    def installieren(self):
        """Update sofort holen, auch wenn Auto-Update aus ist; der Update-Dienst startet die App danach neu."""
        try:
            STATE.mkdir(parents=True, exist_ok=True)
            (STATE / "jetzt").touch()
            subprocess.Popen(["systemctl", "--user", "start", "--no-block", "dragonfist-update.service"])
            return True
        except OSError:
            return False

    def _lauf(self):
        while True:
            self._pruefen()
            time.sleep(PRUEF_S)


def symbol(s, pos, an, an_col, aus_col):
    x, y = pos
    col = an_col if an else aus_col
    for k, r in enumerate((10, 19, 28)):
        pygame.draw.arc(s, col, (x - r, y - r, 2 * r, 2 * r), math.radians(45), math.radians(135), 4)
    pygame.draw.circle(s, col, (x, y - 2), 4)
    if not an:
        pygame.draw.line(s, aus_col, (x - 20, y - 28), (x + 20, y + 4), 4)
