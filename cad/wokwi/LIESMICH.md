# Wokwi-Simulation

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
| A1 | -150 mm | GP0 | `1` |
| A2 | -95 mm | GP3 | `2` |
| A3 | -40 mm | GP6 | `3` |
| A4 | +40 mm | GP9 | `4` |
| A5 | +95 mm | GP12 | `5` |
| A6 | +150 mm | GP15 | `6` |
| B1 | -165 mm | GP28 | `a` |
| B2 | -110 mm | GP27 | `s` |
| B3 | -55 mm | GP26 | `d` |
| B4 | +0 mm | GP21 | `f` |
| B5 | +55 mm | GP20 | `g` |
| B6 | +110 mm | GP18 | `h` |
| B7 | +165 mm | GP17 | `j` |
