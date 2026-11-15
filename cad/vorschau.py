"""
Vorschaubilder ohne zusätzliche Programme:  python vorschau.py
Legt PNGs in ausgabe/bilder/ ab.
"""
from pathlib import Path

import numpy as np
import pyvista as pv

import modell as M
import parameter as P

BILDER = Path(__file__).parent / "ausgabe" / "bilder"
BILDER.mkdir(parents=True, exist_ok=True)


def netz(form, toleranz):
    verts, tris = form.tessellate(toleranz, 0.3)
    v = np.array([(p.X, p.Y, p.Z) for p in verts])
    f = np.hstack([[3, a, b, c] for a, b, c in tris])
    return pv.PolyData(v, f)


def bild(teile, datei, titel, richtung, toleranz=1.0, boden=None, groesse=(1400, 1100), zoom=1.0, kanten=True):
    p = pv.Plotter(off_screen=True, window_size=groesse)
    p.set_background("white")
    for t in teile:
        rgb = tuple(t.color)[:3] if t.color else (0.7, 0.7, 0.7)
        p.add_mesh(netz(t, toleranz), color=rgb, smooth_shading=False,
                   show_edges=False, specular=0.1)
        if kanten:
            p.add_mesh(netz(t, toleranz).extract_feature_edges(40), color=(0.15, 0.15, 0.15), line_width=1)
    if boden:
        x0, x1, y0, y1 = boden
        p.add_mesh(pv.Plane(center=((x0 + x1) / 2, (y0 + y1) / 2, -1), direction=(0, 0, 1),
                            i_size=x1 - x0, j_size=y1 - y0), color=(0.88, 0.88, 0.9))
    p.add_text(titel, font_size=14, color="black")
    p.camera_position = "xz"
    p.camera.azimuth, p.camera.elevation = 0, 0
    b = p.bounds
    mitte = np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2])
    p.camera.focal_point = mitte
    p.camera.position = mitte + np.array(richtung) / np.linalg.norm(richtung) * 5000
    p.camera.up = (0, 0, 1)
    p.reset_camera()
    p.camera.zoom(zoom)
    p.screenshot(str(BILDER / datei))
    p.close()
    print("->", BILDER / datei)


if __name__ == "__main__":
    kind, _ = M.aufbau_kinder()
    erw, _ = M.aufbau_erwachsene()
    boden = (-700, 900, -650, 750)
    schraeg = (-0.9, -1.4, 0.6)
    bild(kind.children, "aufbau_kinder.png", f"Aufbau Kinder (Fenstermitte {P.KIND_FENSTERMITTE / 10:.0f} cm)", schraeg, 2.0, boden, kanten=False)
    bild(erw.children, "aufbau_erwachsene.png", f"Aufbau Erwachsene (Fenstermitte {P.ERW_FENSTERMITTE / 10:.0f} cm)", schraeg, 2.0, boden,
         kanten=False)
    bild(kind.children, "aufbau_kinder_vorne.png", "Aufbau Kinder – Sicht des Kindes", (0, -1, 0.05), 2.0, boden,
         kanten=False)

    rahmen = [t for t in M.rahmen() if not t.label.startswith("Schwimmnudel")]
    bild(rahmen, "rahmen_schraeg.png", "Rahmen ohne Schwimmnudeln – rot = IR-Strahlen", (-1, -1.6, 0.8), 0.5)
    schnitt = [t for t in rahmen if not t.label.startswith(("Seitenbrett", "LED", "Winkel"))]
    bild(schnitt, "rahmen_seite.png", "Seitenansicht ohne Seitenbrett: Ebenen A / B / C (Kind schlägt von links)",
         (1, 0, 0), 0.5)

    for f in BILDER.glob("leiste_*.png"):
        f.unlink()
    stuecke = M.zerteilen(M.sensorplatte())
    for i, s in enumerate(stuecke):
        M.teil(s, "", ("druck", "druck_c")[i % 2])
    bild(stuecke, "platte_oben.png", f"Sensorplatte ({len(stuecke)} Stücke) – Strahlseite", (-0.6, -1, 1.2),
         0.1, groesse=(1400, 900))
    bild(stuecke, "platte_unten.png", "Sensorplatte – Brettseite: Taschen und Kabelkerben",
         (-0.6, -1, -1.2), 0.1, groesse=(1400, 900))
    bild([M.teil(M.testblock(), "", "druck")], "testblock.png", "Prototyp-Testblock (2x drucken)",
         (-0.6, -1, 0.9), 0.1, groesse=(1200, 800))
