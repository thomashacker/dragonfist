import math
import socket
import subprocess
import threading
import time

import pygame

PRUEF_S = 10


class Netz:
    """Prüft im Hintergrund, ob Internet da ist und in welchem WLAN der Jetson hängt."""

    def __init__(self):
        self.online, self.ssid = None, None
        threading.Thread(target=self._lauf, daemon=True).start()

    def _lauf(self):
        while True:
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
            time.sleep(PRUEF_S)


def symbol(s, pos, an, an_col, aus_col):
    x, y = pos
    col = an_col if an else aus_col
    for k, r in enumerate((10, 19, 28)):
        pygame.draw.arc(s, col, (x - r, y - r, 2 * r, 2 * r), math.radians(45), math.radians(135), 4)
    pygame.draw.circle(s, col, (x, y - 2), 4)
    if not an:
        pygame.draw.line(s, aus_col, (x - 20, y - 28), (x + 20, y + 4), 4)
