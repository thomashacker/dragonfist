"""
Spielt die Rohdaten eines Laufs (runs/<lauf>/raw.log) durch die Schlag-Logik und zeigt, was sie daraus macht.
python monitor/analyse.py runs/<lauf>                    Blöcke: Treffer/Fehlschläge je Hand, Anschläge auf Ebene A
python monitor/analyse.py runs/<lauf> --von 186 --bis 190   dazu jedes Ereignis als Liste
python monitor/analyse.py runs/<lauf> --bild zeit.png       Zeitstrahl aller Strahlen mit erkannten Schlägen
--logik datei.py  andere Punch-Implementierung zum Vergleich
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from monitor import NAME, A  # noqa: E402

N_A, N = len(A), len(NAME)
PAUSE_S = 3


def laden(lauf):
    """raw.log: alles, was der Pico geschickt hat (E-Flanken und S-Status), mit Ankunftszeit."""
    ev, st, marken = [], [], []
    for z in (Path(lauf) / "raw.log").read_text(encoding="utf-8", errors="ignore").splitlines():
        p = z.split()
        if len(p) < 2:
            continue
        t = float(p[0])
        if p[1] == "E" and len(p) == 5:
            ev.append((t, int(p[2]), int(p[3]), int(p[4])))
        elif p[1] == "S" and len(p) == 3:
            st.append((t, int(p[2], 16)))
        elif p[1] == "#" and p[2] != "PUNCH":
            marken.append((t, " ".join(p[2:])))
    return ev, st, marken


def logik(datei=None):
    if not datei:
        import punch
        return punch.Punch
    spec = importlib.util.spec_from_file_location("punch_x", datei)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.Punch


def abspielen(ev, st, Punch, dist=200, fps=60):
    """Wie live: Flanken und Status in Ankunftsreihenfolge, dazwischen ein tick je Bildschirm-Frame."""
    p, out = Punch(N_A, N, dist), []
    zeilen = sorted([(t, 0, x) for t, *x in ev] + [(t, 1, m) for t, m in st], key=lambda z: z[:2])
    frame = zeilen[0][0] if zeilen else 0
    for t, art, x in zeilen:
        while frame + 1 / fps <= t:
            frame += 1 / fps
            out += [r | {"t": frame} for r in p.tick(frame)]
        if art:
            p.status(x, t)
        else:
            p.edge(*x, t)
    if zeilen:
        out += [r | {"t": frame} for r in p.tick(frame + 1)]
    return out


def bloecke(ev):
    b, s = [], 0
    for k in range(1, len(ev) + 1):
        if k == len(ev) or ev[k][0] - ev[k - 1][0] > PAUSE_S:
            b.append((ev[s][0], ev[k - 1][0]))
            s = k
    return b


def b_eintritte(ev, t0, t1, ruhe=0.02):
    """Unabhängige Zählung: in Ebene B taucht eine neue Gruppe auf (kein Nachbarstrahl gebrochen oder gerade erst frei)."""
    low, frei, n = 0, {}, 0
    for t, i, v, _ in ev:
        if i < N_A or not t0 <= t <= t1:
            continue
        nach = [k for k in (i - 1, i, i + 1) if N_A <= k < N]
        if v == 0:
            n += not any(low >> k & 1 or t - frei.get(k, -9) < ruhe for k in nach)
            low |= 1 << i
        else:
            low &= ~(1 << i)
            frei[i] = t
    return n


def bericht(ev, res, marken):
    print(f"{'Block':>15} {'Dauer':>6} {'Treffer':>8} {'L':>4} {'R':>4} {'Fehl':>5} {'km/h Ø':>7} {'B-Eintritte':>12}")
    for t0, t1 in bloecke(ev):
        r = [x for x in res if t0 - 0.1 <= x["t"] <= t1 + 1.5]
        ok = [x for x in r if x["ok"]]
        vs = [x["v"] for x in ok if x["v"]]
        v = sum(vs) * 3.6 / len(vs) if vs else 0
        print(f"{t0:7.1f}–{t1:7.1f} {t1 - t0:5.1f}s {len(ok):8} {sum(x['hand'] == 'L' for x in ok):4} "
              f"{sum(x['hand'] == 'R' for x in ok):4} {len(r) - len(ok):5} {v:7.1f} {b_eintritte(ev, t0, t1):12}")
        for tm, m in marken:
            if t0 - 5 <= tm <= t1 + 5:
                print(f"{'':16}# {tm:.1f} {m}")
    ok = [x for x in res if x["ok"]]
    print(f"gesamt: {len(ok)} Treffer, {len(res) - len(ok)} Fehlschläge "
          + ", ".join(f"{m} {sum(x['msg'] == m for x in res)}" for m in sorted({x["msg"] for x in res if not x["ok"]})))
    start = None
    for tm, m in marken:
        if m.startswith("AUFNAHME START"):
            start = tm
        elif m.startswith("AUFNAHME ENDE") and start is not None:
            w = dict(x.split("=") for x in m.split()[2:])
            ok = [x for x in res if x["ok"] and start <= x["t"] <= tm + 0.5]
            nl = sum(x["hand"] == "L" for x in ok)
            print(f"Aufnahme {start:.1f}–{tm:.1f}s: gezählt {w['gezaehlt']:>3} · live {w['erkannt']:>3} · "
                  f"jetzt {len(ok):>3} (L{nl} R{len(ok) - nl}) · B-Eintritte {b_eintritte(ev, start, tm)}")
            start = None


def liste(ev, res, t0, t1):
    z = [(t, f"  {NAME[i]:3} {'ZU ' if v == 0 else 'auf'}") for t, i, v, _ in ev if t0 <= t <= t1]
    z += [(x["t"], f">>> {x['hand']} {x['msg']}" + (f" {x['v'] * 3.6:.1f} km/h" if x["v"] else ""))
          for x in res if t0 <= x["t"] <= t1]
    for t, s in sorted(z):
        print(f"{t:9.4f} {s}")


def bild(ev, res, t0, t1, datei, px_s=500, zeile_s=2.0):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    f = pygame.font.SysFont("dejavusansmono,consolas,monospace", 13)
    rh, kopf = 14, 26
    n_z = max(1, int((t1 - t0) // zeile_s + 1))
    zh = kopf + N * rh + 34
    s = pygame.Surface((int(zeile_s * px_s) + 60, n_z * zh))
    s.fill((12, 12, 14))
    reihen = list(range(N_A, N)) + list(range(N_A))           # B oben, A unten
    farbe = {"L": (255, 150, 60), "R": (90, 170, 255)}
    offen = {}
    balken = []
    for t, i, v, _ in ev:
        if v == 0:
            offen[i] = t
        elif i in offen:
            balken.append((i, offen.pop(i), t))
    balken += [(i, a, t1) for i, a in offen.items()]
    for z in range(n_z):
        za, y0 = t0 + z * zeile_s, z * zh
        x = lambda t: 50 + (t - za) * px_s
        for k, i in enumerate(reihen):
            y = y0 + kopf + k * rh
            s.blit(f.render(NAME[i], True, (150, 150, 150)), (6, y))
            pygame.draw.line(s, (35, 35, 40), (50, y + rh // 2), (s.get_width(), y + rh // 2))
        for tt in range(int(za * 10), int((za + zeile_s) * 10) + 1):
            xx = x(tt / 10)
            pygame.draw.line(s, (50, 50, 55) if tt % 10 else (90, 90, 95), (xx, y0 + kopf), (xx, y0 + kopf + N * rh))
            tt % 10 == 0 and s.blit(f.render(f"{tt / 10:.0f}s", True, (150, 150, 150)), (xx + 2, y0 + 6))
        for i, a, b in balken:
            if b < za or a > za + zeile_s:
                continue
            k = reihen.index(i)
            pygame.draw.rect(s, (220, 220, 220), (x(max(a, za)), y0 + kopf + k * rh + 2,
                                                  max(1, (min(b, za + zeile_s) - max(a, za)) * px_s), rh - 4))
        for r in res:
            if za <= r["t"] <= za + zeile_s:
                c = farbe[r["hand"]] if r["ok"] else (230, 50, 50)
                pygame.draw.line(s, c, (x(r["t"]), y0 + kopf), (x(r["t"]), y0 + kopf + N * rh), 2)
                txt = f"{r['hand']} {r['v'] * 3.6:.0f}" if r["ok"] else f"{r['hand']} {r['msg'][:5]}"
                s.blit(f.render(txt, True, c), (x(r["t"]) + 3, y0 + kopf + N * rh + 4))
    pygame.image.save(s, str(datei))
    print("->", datei)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lauf")
    ap.add_argument("--von", type=float)
    ap.add_argument("--bis", type=float)
    ap.add_argument("--bild")
    ap.add_argument("--logik")
    ap.add_argument("--abstand", type=float, default=200)
    a = ap.parse_args()
    ev, st, marken = laden(a.lauf)
    res = abspielen(ev, st, logik(a.logik), a.abstand)
    bericht(ev, res, marken)
    if a.von is not None:
        t1 = a.bis if a.bis is not None else a.von + 2
        a.bild or liste(ev, res, a.von, t1)
        a.bild and bild(ev, res, a.von, t1, a.bild)


if __name__ == "__main__":
    main()
