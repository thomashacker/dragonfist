"""
Anzeige für das Schlag-Messgerät (läuft auf dem Jetson, Vollbild auf dem 7"-Display).

  python3 anzeige.py            # mit Pico (USB) und Arcade-Knöpfen
  python3 anzeige.py --sim      # ohne Hardware: Q/P = Schlag links/rechts, X = ungültig
  python3 anzeige.py --fenster  # nicht im Vollbild (zum Testen am PC)

Knöpfe: ◀ ▶ wählen, OK bestätigen, START starten, Zurück zurück.
Tastatur geht immer mit: Pfeile, Enter = OK, Leertaste = START, Rücktaste/Esc = Zurück.
"""
import argparse
import array
import json
import math
import os
import queue
import time
from pathlib import Path

import pygame

import quellen

ORDNER = Path(__file__).parent
BREITE, HOEHE = 1024, 600                      # 7"-Display
STANDARD = {
    "dauer_s": 20,                             # Meiste Schläge: Intervall
    "versuche": 3,                             # Schnellster Schlag: gültige Versuche
    "kalibrierung": 1.00,                      # Faktor aus dem Ball-Falltest
    "altersgruppen": ["bis 6", "7 – 9", "10 – 12", "13 – 17", "Erwachsene"],
    "gamepad": {"ZURUECK": 0, "LINKS": 1, "START": 2, "RECHTS": 3, "OK": 4},
}
FARBE = {"hg": (10, 14, 20), "raster": (22, 32, 44), "rahmen": (40, 210, 255), "text": (220, 235, 245),
         "gruen": (60, 255, 140), "rot": (255, 70, 70), "gelb": (255, 210, 60), "grau": (120, 135, 150)}
MODI = {"schnell": "Schnellster Schlag", "meiste": "Meiste Schläge"}
VERGLEICHE = [(0, "Schnecke"), (6, "Spaziergang"), (12, "Jogger"), (18, "Fahrrad"), (25, "Mofa"),
              (32, "Rennrad"), (38, "schneller als Usain Bolt!"), (45, "Rennpferd")]
ALPHABET = list("ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ") + [" ", "-"]


def laden(datei, standard):
    try:
        return {**standard, **json.loads((ORDNER / datei).read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(standard)


def speichern(datei, daten):
    (ORDNER / datei).write_text(json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8")


def vergleich(kmh):
    text = VERGLEICHE[0][1]
    for grenze, t in VERGLEICHE:
        if kmh >= grenze:
            text = t
    return text


class Toene:
    """Erzeugt die Töne selbst (keine Sounddateien nötig)."""

    def __init__(self):
        self.ok = False
        try:
            pygame.mixer.init(22050, -16, 1)
            self.ok = True
        except pygame.error:
            return
        self.t = {"tick": self._ton(880, 90), "los": self._ton(1320, 350), "treffer": self._ton(1600, 60),
                  "fehler": self._ton(220, 200), "ende": self._ton(660, 600), "klick": self._ton(1200, 25, 0.2)}

    @staticmethod
    def _ton(freq, ms, laut=0.4):
        n = int(22050 * ms / 1000)
        daten = array.array("h", (int(32767 * laut * math.sin(2 * math.pi * freq * i / 22050) *
                                      min(1, (n - i) / 400)) for i in range(n)))
        return pygame.mixer.Sound(buffer=daten.tobytes())

    def __call__(self, name):
        if self.ok:
            self.t[name].play()


class App:
    def __init__(self, sim=False, uhr=time.monotonic):
        self.uhr = uhr
        self.cfg = laden("einstellungen.json", STANDARD)
        self.liste = laden("rangliste.json", {"eintraege": []})["eintraege"]
        self.ereignisse = queue.Queue()
        self.quelle = quellen.SimQuelle(self.ereignisse) if sim else quellen.PicoQuelle(self.ereignisse)
        if not sim:
            self.quelle.start()
        self.sim = sim
        self.toene = Toene()
        self.schrift = {g: pygame.font.Font(None, g) for g in (24, 32, 44, 64, 96, 200)}
        logo = ORDNER / "logo.png"
        self.logo = pygame.image.load(str(logo)).convert_alpha() if logo.exists() else None
        self.zustand, self.auswahl = "menu", 0
        self.modus, self.name, self.buchstabe, self.gruppe = "schnell", "", 0, 0
        self.ergebnisse, self.ungueltig, self.letzter, self.t0 = [], 0, None, 0
        self.ansicht_modus, self.ansicht_gruppe = "schnell", 0
        self.cfg_zeile = 0

    # ------------------------------------------------------------------ Eingaben
    def knopf(self, name):
        self.toene("klick")
        getattr(self, f"_knopf_{self.zustand}", lambda n: None)(name)

    def _knopf_menu(self, n):
        punkte = ["schnell", "meiste", "rangliste", "einstellungen"]
        if n in ("LINKS", "RECHTS"):
            self.auswahl = (self.auswahl + (1 if n == "RECHTS" else -1)) % len(punkte)
        elif n in ("OK", "START"):
            wahl = punkte[self.auswahl]
            if wahl in MODI:
                self.modus, self.name, self.buchstabe = wahl, "", 0
                self.zustand = "name"
            else:
                self.zustand = wahl

    def _knopf_name(self, n):
        if n == "LINKS":
            self.buchstabe = (self.buchstabe - 1) % len(ALPHABET)
        elif n == "RECHTS":
            self.buchstabe = (self.buchstabe + 1) % len(ALPHABET)
        elif n == "OK" and len(self.name) < 10:
            self.name += ALPHABET[self.buchstabe]
        elif n == "ZURUECK":
            if self.name:
                self.name = self.name[:-1]
            else:
                self.zustand = "menu"
        elif n == "START" and self.name.strip():
            self.zustand = "gruppe"

    def _knopf_gruppe(self, n):
        g = len(self.cfg["altersgruppen"])
        if n in ("LINKS", "RECHTS"):
            self.gruppe = (self.gruppe + (1 if n == "RECHTS" else -1)) % g
        elif n in ("OK", "START"):
            self.zustand = "bereit"
        elif n == "ZURUECK":
            self.zustand = "name"

    def _knopf_bereit(self, n):
        if n == "START":
            self.zustand, self.t0 = "countdown", self.uhr()
            self.ergebnisse, self.ungueltig, self.letzter = [], 0, None
            self._tick = 4
        elif n == "ZURUECK":
            self.zustand = "gruppe"

    def _knopf_schnell(self, n):
        if n == "ZURUECK":
            self._fertig()

    _knopf_meiste = _knopf_schnell

    def _knopf_ergebnis(self, n):
        if n in ("OK", "START", "ZURUECK"):
            self.zustand = "menu"

    def _knopf_rangliste(self, n):
        g = len(self.cfg["altersgruppen"])
        if n in ("LINKS", "RECHTS"):
            self.ansicht_gruppe = (self.ansicht_gruppe + (1 if n == "RECHTS" else -1)) % g
        elif n in ("OK", "START"):
            self.ansicht_modus = "meiste" if self.ansicht_modus == "schnell" else "schnell"
        elif n == "ZURUECK":
            self.zustand = "menu"

    def _knopf_einstellungen(self, n):
        zeilen = self._cfg_zeilen()
        key, werte = zeilen[self.cfg_zeile]
        if n in ("LINKS", "RECHTS"):
            i = min(range(len(werte)), key=lambda k: abs(werte[k] - self.cfg[key]))
            self.cfg[key] = werte[max(0, min(len(werte) - 1, i + (1 if n == "RECHTS" else -1)))]
        elif n == "OK":
            self.cfg_zeile = (self.cfg_zeile + 1) % len(zeilen)
        elif n in ("ZURUECK", "START"):
            speichern("einstellungen.json", self.cfg)
            self.zustand = "menu"

    @staticmethod
    def _cfg_zeilen():
        return [("dauer_s", [10, 15, 20, 30, 45, 60]), ("versuche", [1, 3, 5]),
                ("kalibrierung", [round(0.80 + i * 0.01, 2) for i in range(41)])]

    def schlag(self, e):
        if self.zustand not in ("schnell", "meiste"):
            return
        if not e.get("valid"):
            self.ungueltig += 1
            self.letzter = ("ungültig", self.uhr())
            self.toene("fehler")
            return
        kmh = float(e.get("speed_kmh", e.get("speed_ms", 0) * 3.6)) * self.cfg["kalibrierung"]
        self.ergebnisse.append(kmh)
        self.letzter = (kmh, self.uhr())
        self.toene("treffer")
        if self.zustand == "schnell" and len(self.ergebnisse) >= self.cfg["versuche"]:
            self._ende_um = self.uhr() + 2.0                    # letzten Wert noch kurz zeigen

    # ------------------------------------------------------------------ Ablauf
    def update(self):
        while not self.ereignisse.empty():
            self.schlag(self.ereignisse.get())
        jetzt = self.uhr()
        if self.zustand == "countdown":
            rest = 3 - int(jetzt - self.t0)
            if rest != self._tick:
                self._tick = rest
                self.toene("tick" if rest > 0 else "los")
            if jetzt - self.t0 >= 3.6:
                self.zustand, self.t0, self._ende_um = self.modus, jetzt, None
        elif self.zustand == "meiste" and jetzt - self.t0 >= self.cfg["dauer_s"]:
            self._fertig()
        elif self.zustand == "schnell" and getattr(self, "_ende_um", None) and jetzt >= self._ende_um:
            self._fertig()

    def _fertig(self):
        self.toene("ende")
        wert = (max(self.ergebnisse) if self.ergebnisse else 0) if self.modus == "schnell" else len(self.ergebnisse)
        gruppe = self.cfg["altersgruppen"][self.gruppe]
        eintrag = {"name": self.name.strip(), "gruppe": gruppe, "modus": self.modus, "wert": round(wert, 1),
                   "ungueltig": self.ungueltig, "zeit": time.strftime("%Y-%m-%d %H:%M")}
        if wert > 0:
            self.liste.append(eintrag)
            speichern("rangliste.json", {"eintraege": self.liste})
        self.letztes_ergebnis = eintrag
        self.platz = 1 + sum(1 for e in self.liste if e["modus"] == self.modus and e["gruppe"] == gruppe
                             and e["wert"] > wert)
        self.zustand = "ergebnis"
        self.ansicht_modus, self.ansicht_gruppe = self.modus, self.gruppe

    # ------------------------------------------------------------------ Zeichnen
    def text(self, f, t, farbe, pos, mitte=True, groesse=None):
        s = self.schrift[groesse or 32].render(str(t), True, FARBE.get(farbe, farbe))
        r = s.get_rect(center=pos) if mitte else s.get_rect(topleft=pos)
        f.blit(s, r)
        return r

    def rahmen(self, f, r, farbe="rahmen", dicke=3):
        pygame.draw.rect(f, FARBE[farbe], r, dicke, border_radius=6)
        for ex, ey in ((r.left, r.top), (r.right, r.top), (r.left, r.bottom), (r.right, r.bottom)):
            pygame.draw.circle(f, FARBE["grau"], (ex, ey), 5)            # „Schrauben“ wie bei Wire-Mod

    def hintergrund(self, f):
        f.fill(FARBE["hg"])
        for x in range(0, BREITE, 32):
            pygame.draw.line(f, FARBE["raster"], (x, 0), (x, HOEHE))
        for y in range(0, HOEHE, 32):
            pygame.draw.line(f, FARBE["raster"], (0, y), (BREITE, y))
        if self.logo:
            l = pygame.transform.smoothscale(self.logo, (320, int(320 * self.logo.get_height() / self.logo.get_width())))
            l.set_alpha(40)
            f.blit(l, l.get_rect(center=(BREITE // 2, HOEHE // 2)))
        else:
            self.text(f, "VIET VO DAO", (30, 42, 56), (BREITE // 2, HOEHE // 2 + 20), groesse=200)
        status = "SIMULATION (Q / P / X)" if self.sim else ("Pico verbunden" if self.quelle.verbunden
                                                           else "Pico NICHT verbunden")
        farbe = "gelb" if self.sim else ("gruen" if self.quelle.verbunden else "rot")
        pygame.draw.circle(f, FARBE[farbe], (BREITE - 210, 22), 7)
        self.text(f, status, farbe, (BREITE - 195, 12), mitte=False, groesse=24)
        self.text(f, "VVD SCHLAG-MESSER", "rahmen", (20, 10), mitte=False, groesse=32)

    def fusszeile(self, f, t):
        self.text(f, t, "grau", (BREITE // 2, HOEHE - 22), groesse=24)

    def draw(self, f):
        self.hintergrund(f)
        getattr(self, f"_zeichne_{self.zustand}")(f)

    def _zeichne_menu(self, f):
        punkte = ["Schnellster Schlag", "Meiste Schläge", "Rangliste", "Einstellungen"]
        self.text(f, "Was wollen wir machen?", "text", (BREITE // 2, 110), groesse=44)
        for i, p in enumerate(punkte):
            r = pygame.Rect(0, 0, 210, 150)
            r.center = (BREITE // 2 + (i - 1.5) * 235, 300)
            aktiv = i == self.auswahl
            pygame.draw.rect(f, (18, 40, 56) if aktiv else (16, 22, 30), r, border_radius=6)
            self.rahmen(f, r, "gelb" if aktiv else "rahmen", 4 if aktiv else 2)
            for k, wort in enumerate(p.split(" ")):
                self.text(f, wort, "gelb" if aktiv else "text", (r.centerx, r.centery - 18 + k * 36), groesse=32)
        self.fusszeile(f, "◀ ▶ wählen   ·   OK / START öffnen")

    def _zeichne_name(self, f):
        self.text(f, MODI[self.modus], "rahmen", (BREITE // 2, 80), groesse=44)
        self.text(f, "Wie heißt du?", "text", (BREITE // 2, 150), groesse=44)
        r = pygame.Rect(0, 0, 620, 110)
        r.center = (BREITE // 2, 270)
        self.rahmen(f, r)
        blink = "_" if int(self.uhr() * 2) % 2 == 0 else " "
        self.text(f, self.name + blink, "gruen", r.center, groesse=96)
        for k in (-2, -1, 0, 1, 2):
            z = ALPHABET[(self.buchstabe + k) % len(ALPHABET)]
            self.text(f, z if z != " " else "␣", "gelb" if k == 0 else "grau",
                      (BREITE // 2 + k * 90, 420), groesse=96 if k == 0 else 64)
        self.fusszeile(f, "◀ ▶ Buchstabe   ·   OK übernehmen   ·   Zurück löschen   ·   START fertig")

    def _zeichne_gruppe(self, f):
        self.text(f, f"Hallo {self.name.strip()}!", "gruen", (BREITE // 2, 120), groesse=64)
        self.text(f, "Welche Altersgruppe?", "text", (BREITE // 2, 210), groesse=44)
        r = pygame.Rect(0, 0, 460, 120)
        r.center = (BREITE // 2, 340)
        self.rahmen(f, r, "gelb")
        self.text(f, f"◀  {self.cfg['altersgruppen'][self.gruppe]}  ▶", "gelb", r.center, groesse=64)
        self.fusszeile(f, "◀ ▶ wählen   ·   OK weiter")

    def _zeichne_bereit(self, f):
        self.text(f, MODI[self.modus], "rahmen", (BREITE // 2, 110), groesse=64)
        info = (f"{self.cfg['versuche']} Schläge – der schnellste zählt" if self.modus == "schnell"
                else f"{self.cfg['dauer_s']} Sekunden – so viele gültige Schläge wie möglich")
        self.text(f, info, "text", (BREITE // 2, 200), groesse=32)
        self.text(f, "Arm ganz durchstrecken und zurück in die Deckung!", "grau", (BREITE // 2, 250), groesse=32)
        puls = 1 + 0.05 * math.sin(self.uhr() * 6)
        r = pygame.Rect(0, 0, int(380 * puls), int(120 * puls))
        r.center = (BREITE // 2, 400)
        pygame.draw.rect(f, (20, 60, 35), r, border_radius=10)
        self.rahmen(f, r, "gruen", 4)
        self.text(f, "START drücken", "gruen", r.center, groesse=64)

    def _zeichne_countdown(self, f):
        rest = 3 - int(self.uhr() - self.t0)
        self.text(f, str(rest) if rest > 0 else "LOS!", "gelb" if rest > 0 else "gruen",
                  (BREITE // 2, HOEHE // 2), groesse=200)

    def _letzter_schlag(self, f, y):
        if not self.letzter or self.uhr() - self.letzter[1] > 1.5:
            return
        wert = self.letzter[0]
        if wert == "ungültig":
            self.text(f, "Ungültig – Faust ganz durch und zurück!", "rot", (BREITE // 2, y), groesse=44)

    def _zeichne_schnell(self, f):
        n = len(self.ergebnisse)
        self.text(f, f"Versuch {min(n + 1, self.cfg['versuche'])} von {self.cfg['versuche']}", "text",
                  (BREITE // 2, 70), groesse=44)
        r = pygame.Rect(0, 0, 700, 300)
        r.center = (BREITE // 2, 280)
        self.rahmen(f, r)
        if self.letzter and self.letzter[0] != "ungültig":
            kmh = self.letzter[0]
            self.text(f, f"{kmh:.1f}", "gruen", (r.centerx - 60, r.centery - 30), groesse=200)
            self.text(f, "km/h", "gruen", (r.right - 110, r.centery + 10), groesse=64)
            self.text(f, f"so schnell wie: {vergleich(kmh)}", "gelb", (r.centerx, r.bottom - 40), groesse=44)
        else:
            self.text(f, "Schlag!", "grau", r.center, groesse=96)
        if self.ergebnisse:
            self.text(f, "Bester: " + f"{max(self.ergebnisse):.1f} km/h", "text", (BREITE // 2, 480), groesse=44)
        self._letzter_schlag(f, 530)

    def _zeichne_meiste(self, f):
        rest = max(0.0, self.cfg["dauer_s"] - (self.uhr() - self.t0))
        anteil = rest / self.cfg["dauer_s"]
        balken = pygame.Rect(60, 70, BREITE - 120, 30)
        pygame.draw.rect(f, (30, 40, 50), balken, border_radius=6)
        voll = balken.copy()
        voll.width = int(balken.width * anteil)
        pygame.draw.rect(f, FARBE["gruen"] if anteil > 0.3 else FARBE["rot"], voll, border_radius=6)
        self.text(f, f"{rest:4.1f} s", "text", (BREITE // 2, 130), groesse=44)
        r = pygame.Rect(0, 0, 520, 280)
        r.center = (BREITE // 2, 320)
        self.rahmen(f, r)
        self.text(f, str(len(self.ergebnisse)), "gruen", (r.centerx, r.centery - 20), groesse=200)
        self.text(f, "gültige Schläge", "gruen", (r.centerx, r.bottom - 35), groesse=44)
        self.text(f, f"ungültig: {self.ungueltig}", "rot", (BREITE // 2, 500), groesse=44)
        self._letzter_schlag(f, 545)

    def _zeichne_ergebnis(self, f):
        e = self.letztes_ergebnis
        self.text(f, f"Super, {e['name']}!", "gruen", (BREITE // 2, 90), groesse=64)
        r = pygame.Rect(0, 0, 640, 230)
        r.center = (BREITE // 2, 270)
        self.rahmen(f, r, "gelb")
        if self.modus == "schnell":
            self.text(f, f"{e['wert']:.1f} km/h", "gelb", (r.centerx, r.centery - 25), groesse=96)
            self.text(f, f"so schnell wie: {vergleich(e['wert'])}", "text", (r.centerx, r.bottom - 40), groesse=44)
        else:
            self.text(f, f"{int(e['wert'])} Schläge", "gelb", (r.centerx, r.centery - 25), groesse=96)
            self.text(f, f"in {self.cfg['dauer_s']} s  ·  ungültig: {e['ungueltig']}", "text",
                      (r.centerx, r.bottom - 40), groesse=44)
        self.text(f, f"Platz {self.platz} in „{e['gruppe']}“", "rahmen", (BREITE // 2, 450), groesse=64)
        self.fusszeile(f, "OK = zurück zum Menü")

    def _zeichne_rangliste(self, f):
        gruppe = self.cfg["altersgruppen"][self.ansicht_gruppe]
        self.text(f, f"Rangliste: {MODI[self.ansicht_modus]}", "rahmen", (BREITE // 2, 75), groesse=44)
        self.text(f, f"◀  {gruppe}  ▶", "gelb", (BREITE // 2, 125), groesse=44)
        eintraege = sorted((e for e in self.liste if e["modus"] == self.ansicht_modus and e["gruppe"] == gruppe),
                           key=lambda e: -e["wert"])[:8]
        r = pygame.Rect(0, 0, 700, 360)
        r.center = (BREITE // 2, 345)
        self.rahmen(f, r)
        if not eintraege:
            self.text(f, "Noch keine Einträge", "grau", r.center, groesse=44)
        for i, e in enumerate(eintraege):
            y = r.top + 30 + i * 42
            farbe = "gelb" if i == 0 else "text"
            self.text(f, f"{i + 1}.", farbe, (r.left + 30, y), mitte=False, groesse=44)
            self.text(f, e["name"], farbe, (r.left + 100, y), mitte=False, groesse=44)
            wert = f"{e['wert']:.1f} km/h" if self.ansicht_modus == "schnell" else f"{int(e['wert'])} Schläge"
            self.text(f, wert, "gruen", (r.right - 220, y), mitte=False, groesse=44)
        self.fusszeile(f, "◀ ▶ Altersgruppe   ·   OK Modus wechseln   ·   Zurück")

    def _zeichne_einstellungen(self, f):
        self.text(f, "Einstellungen", "rahmen", (BREITE // 2, 80), groesse=64)
        namen = {"dauer_s": "Dauer „Meiste Schläge“", "versuche": "Versuche „Schnellster Schlag“",
                 "kalibrierung": "Kalibrierfaktor (Ball-Test)"}
        einheit = {"dauer_s": " s", "versuche": "", "kalibrierung": ""}
        for i, (key, _) in enumerate(self._cfg_zeilen()):
            aktiv = i == self.cfg_zeile
            y = 200 + i * 90
            r = pygame.Rect(120, y - 35, BREITE - 240, 70)
            self.rahmen(f, r, "gelb" if aktiv else "rahmen", 3 if aktiv else 1)
            self.text(f, namen[key], "gelb" if aktiv else "text", (r.left + 20, y - 18), mitte=False, groesse=44)
            wert = f"{self.cfg[key]:.2f}" if key == "kalibrierung" else str(self.cfg[key])
            self.text(f, f"◀ {wert}{einheit[key]} ▶" if aktiv else wert + einheit[key], "gruen",
                      (r.right - 150, y), groesse=44)
        self.fusszeile(f, "OK nächste Zeile   ·   ◀ ▶ ändern   ·   Zurück speichern")


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("--sim", action="store_true")
    arg.add_argument("--fenster", action="store_true")
    a = arg.parse_args()
    pygame.init()
    flags = 0 if a.fenster else pygame.FULLSCREEN
    bild = pygame.display.set_mode((0, 0) if not a.fenster else (BREITE, HOEHE), flags)
    pygame.display.set_caption("VVD Schlag-Messer")
    pygame.mouse.set_visible(a.fenster)
    leinwand = pygame.Surface((BREITE, HOEHE))
    app = App(sim=a.sim)
    pads = []
    pygame.joystick.init()
    uhr = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type == pygame.JOYDEVICEADDED:
                pads.append(pygame.joystick.Joystick(ev.device_index))
            if ev.type == pygame.JOYBUTTONDOWN:
                n = quellen.gamepad_knopf(ev.button, app.cfg["gamepad"])
                if n:
                    app.knopf(n)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F12:                    # Notausgang
                    return
                n = quellen.tastatur_knopf(ev.key, pygame)
                if n:
                    app.knopf(n)
                elif app.sim and ev.key in (pygame.K_q, pygame.K_p, pygame.K_x):
                    app.quelle.schlag("left" if ev.key == pygame.K_q else "right", ev.key != pygame.K_x)
        app.update()
        app.draw(leinwand)
        pygame.transform.smoothscale(leinwand, bild.get_size(), bild)
        pygame.display.flip()
        uhr.tick(60)


if __name__ == "__main__":
    main()
