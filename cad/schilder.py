"""
Schilder: DRAGONFIST vorne am Pult, "schmuhlsches wissen" (Instrument Serif) unten vorne an der Kiste,
VietVoDao-Logo aus den SVG-Ebenen in logo/ (wird in die Deckel graviert). Alles Erhabene liegt über
SCHILD_BODEN: Boden weiß drucken, ab dieser Höhe auf Schwarz wechseln.
Schild-Koordinaten: Rückseite auf z=0, Ansicht von +z.
"""
import functools
import subprocess
from pathlib import Path

import contourpy
import numpy as np
from build123d import Align, Face, Pos, RectangleRounded, Rot, Text, Wire, extrude
from PIL import Image

import parameter as P
from modell import teil

HIER = Path(__file__).resolve().parent
LOGO = HIER / "logo"
RASTER = HIER / "ausgabe" / "logo_raster"
SCHRIFT = HIER / "schrift" / "InstrumentSerif-Regular.ttf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
SVG_B, SVG_H = 772, 750
FAKTOR = 3                                     # Rasterauflösung je SVG-Einheit
MITTE, RADIUS = (386.5, 374.5), 299.5          # äußerer Ring (SVG-Einheiten)


def _rastern(name, svg_text):
    """SVG mit Edge headless rendern -> Bool-Array (schwarz)."""
    RASTER.mkdir(parents=True, exist_ok=True)
    svg, html, png = (RASTER / f"{name}.{e}" for e in ("svg", "html", "png"))
    svg.write_text(svg_text, encoding="utf-8")
    w, h = SVG_B * FAKTOR, SVG_H * FAKTOR
    html.write_text(f'<html><body style="margin:0;background:#fff"><img src="{svg.as_uri()}" '
                    f'style="width:{w}px;height:{h}px;display:block"></body></html>', encoding="utf-8")
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--allow-file-access-from-files", f"--window-size={w},{h}", f"--screenshot={png}", html.as_uri()],
                   check=True, capture_output=True, timeout=120)
    return np.array(Image.open(png).convert("L"))[:h, :w] < 128


@functools.lru_cache(maxsize=None)
def _ebenen():
    """[(sichtbar, verdeckt)] je Ebene, von unten nach oben."""
    tinte, flaeche = [], []
    for i in range(1, 5):
        svg = (LOGO / f"Logo 3D Outline - Layer {i}.svg").read_text(encoding="utf-8")
        ohne_grund = svg.replace(f'<rect width="{SVG_B}" height="{SVG_H}" fill="white"/>', "", 1)
        tinte.append(_rastern(f"ebene{i}", svg))
        flaeche.append(_rastern(f"ebene{i}_flaeche", ohne_grund.replace('fill="white"', 'fill="black"')))
    deckt = np.zeros_like(tinte[0])
    sichtbar = [None] * 4
    for i in range(3, -1, -1):
        sichtbar[i] = tinte[i] & ~deckt
        deckt |= flaeche[i] | tinte[i]
    return sichtbar


def _rdp(p, eps):
    if len(p) < 4:
        return p
    a, b = p[0], p[-1]
    u, v = b - a, p - a
    d = np.abs(u[0] * v[:, 1] - u[1] * v[:, 0]) / (np.linalg.norm(u) or 1)
    i = int(np.argmax(d))
    if d[i] <= eps:
        return np.array([a, b])
    return np.vstack([_rdp(p[:i + 1], eps)[:-1], _rdp(p[i:], eps)])


def _ring(p, eps):
    p = p[:-1] if np.allclose(p[0], p[-1]) else p
    k = len(p) // 2
    q = np.vstack([_rdp(p[:k + 1], eps)[:-1], _rdp(np.vstack([p[k:], p[:1]]), eps)[:-1]])
    return q if len(q) >= 3 else None


def _flaechen(maske, mm_je_px):
    """Bool-Raster -> Faces (Schild-Koordinaten, Mitte des Logos im Ursprung)."""
    z = np.pad(maske.astype(float), 1)
    gen = contourpy.contour_generator(z=z, fill_type=contourpy.FillType.OuterOffset)
    polys, offsets = gen.filled(0.5, 1.5)
    cx, cy = MITTE[0] * FAKTOR + 1, MITTE[1] * FAKTOR + 1
    faces = []
    for pts, off in zip(polys, offsets):
        ringe = []
        for a, b in zip(off[:-1], off[1:]):
            r = _ring(pts[a:b], 0.6)
            if r is not None:
                ringe.append(Wire.make_polygon([((x - cx) * mm_je_px, (cy - y) * mm_je_px) for x, y in r], close=True))
        if ringe:
            faces.append(Face(ringe[0], ringe[1:]))
    return faces


@functools.lru_cache(maxsize=None)
def logo_flaechen(d):
    """Sichtbare Linien aller Ebenen als Faces, Durchmesser d, Mitte im Ursprung."""
    m = _ebenen()
    return tuple(_flaechen(m[0] | m[1] | m[2] | m[3], d / 2 / RADIUS / FAKTOR))


def _schild(txt, schrift, breite, hoehe, text_h, rand=3):
    platte = extrude(RectangleRounded(breite, hoehe, rand), amount=P.SCHILD_BODEN)
    t = Text(txt, 10, font_path=str(schrift), align=(Align.CENTER, Align.CENTER))
    bb = t.bounding_box()
    k = min((breite - 2 * rand - 4) / bb.size.X, text_h / bb.size.Y)
    t = Text(txt, 10 * k, font_path=str(schrift), align=(Align.CENTER, Align.CENTER))
    return platte + Pos(0, 0, P.SCHILD_BODEN) * extrude(t, amount=P.SCHILD_TEXT)


def dragonfist():
    return _schild("DRAGONFIST", P.SCHILD_DRAGONFIST_SCHRIFT, *P.SCHILD_DRAGONFIST)


def schmuhl():
    return _schild("schmuhlsches wissen", SCHRIFT, *P.SCHILD_SCHMUHL)


def druckteile():
    return [("Schild_DRAGONFIST", dragonfist()), ("Schild_schmuhlsches_wissen", schmuhl())]


def am_pult():
    """DRAGONFIST vorne am Pult (Pult-Koordinaten)."""
    return [teil(Pos(0, 0, P.SCHILD_DRAGONFIST_Z) * Rot(90, 0, 0) * dragonfist(), "Schild DRAGONFIST", "deckel")]


def an_kiste(aussen_w):
    """schmuhlsches wissen rechts außen an der Kiste, unten vorne in der Ecke (Rahmen-Koordinaten)."""
    b, h, _ = P.SCHILD_SCHMUHL
    r = P.SCHILD_SCHMUHL_RAND
    lage = Pos(aussen_w / 2, r + b / 2, r + h / 2) * Rot(0, 90, 0) * Rot(0, 0, 90)
    return [teil(lage * schmuhl(), "Schild schmuhlsches wissen", "deckel")]
