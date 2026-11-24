"""
Wertet alle Schlag-Aufnahmen aus (Zeilen '# AUFNAHME START/ENDE' in runs/*/raw.log) und vergleicht
gezählte Wahrheit, Live-Erkennung, heutige Logik und die unabhängige B-Zählung.
python monitor/aufnahmen.py runs                   alle Läufe im Ordner
python monitor/aufnahmen.py runs --logik neu.py    andere Punch-Implementierung zum Vergleich
"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse  # noqa: E402


def aufnahmen(lauf, Punch, dist=200):
    ev, st, marken = analyse.laden(lauf)
    if not any(m.startswith("AUFNAHME START") for _, m in marken):
        return []
    res, out, start = analyse.abspielen(ev, st, Punch, dist), [], None
    for tm, m in marken:
        if m.startswith("AUFNAHME START"):
            start, kopf = tm, dict(x.split("=") for x in m.split()[2:] if "=" in x)
        elif m.startswith("AUFNAHME ENDE") and start is not None:
            w, ende = dict(x.split("=") for x in m.split()[2:]), min(tm, start + float(kopf.get("dauer", 1e9)))
            ok = [x for x in res if x["ok"] and start <= x["t"] <= ende]
            v = [x["v"] * 3.6 for x in ok if x["v"]]
            out.append(dict(lauf=Path(lauf).name, person=kopf.get("person", "?"), art=kopf.get("art", "?"),
                            gezaehlt=int(w["gezaehlt"]), live=int(w["erkannt"]), jetzt=len(ok),
                            l=sum(x["hand"] == "L" for x in ok), b=analyse.b_eintritte(ev, start, ende),
                            fehl=sum(not x["ok"] for x in res if start <= x["t"] <= ende),
                            tempo=len(v) / len(ok) if ok else 0.0, median=statistics.median(v) if v else 0.0,
                            vmax=max(v, default=0.0)))
            start = None
    return out


def tabelle(zeilen):
    print(f"{'Lauf':<20} {'P':>2} {'Art':<11} {'gezählt':>7} {'live':>5} {'jetzt':>5} {'Abw':>5} {'L/R':>7} "
          f"{'B':>4} {'Fehl':>4} {'Tempo':>6} {'Median':>6} {'Max':>5}")
    for z in zeilen:
        abw = (z["jetzt"] - z["gezaehlt"]) / z["gezaehlt"] * 100 if z["gezaehlt"] else 0
        print(f"{z['lauf'][:20]:<20} {z['person']:>2} {z['art'][:11]:<11} {z['gezaehlt']:7} {z['live']:5} "
              f"{z['jetzt']:5} {abw:+4.0f}% {z['l']:3}/{z['jetzt'] - z['l']:<3} {z['b']:4} {z['fehl']:4} "
              f"{z['tempo']:6.0%} {z['median']:6.1f} {z['vmax']:5.1f}")
    if not zeilen:
        print("keine Aufnahmen gefunden")
        return
    g, j = sum(z["gezaehlt"] for z in zeilen), sum(z["jetzt"] for z in zeilen)
    print(f"\n{len(zeilen)} Aufnahmen · gezählt {g} · erkannt {j} ({(j - g) / g * 100 if g else 0:+.1f} %) · "
          f"Fehler je Aufnahme Ø {statistics.mean(abs(z['jetzt'] - z['gezaehlt']) for z in zeilen):.1f} · "
          f"mit Tempo Ø {statistics.mean(z['tempo'] for z in zeilen):.0%}")
    for art in sorted({z["art"] for z in zeilen}):
        zz = [z for z in zeilen if z["art"] == art]
        g, j = sum(z["gezaehlt"] for z in zz), sum(z["jetzt"] for z in zz)
        print(f"  {art:<11} {len(zz):2}× · {j}/{g} erkannt · mit Tempo {statistics.mean(z['tempo'] for z in zz):.0%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ordner", nargs="+")
    ap.add_argument("--logik")
    ap.add_argument("--abstand", type=float, default=200)
    a = ap.parse_args()
    Punch = analyse.logik(a.logik)
    laeufe = sorted({p.parent for o in a.ordner for p in Path(o).glob("**/raw.log")})
    tabelle([z for lauf in laeufe for z in aufnahmen(lauf, Punch, a.abstand)])


if __name__ == "__main__":
    main()
