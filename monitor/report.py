import argparse
import csv
import json
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?", help="Ordner oder Name, sonst der neueste")
    ap.add_argument("--events", type=int, default=0, help="letzte N Ereignisse zeigen")
    a = ap.parse_args()
    d = Path(a.run) if a.run and Path(a.run).is_dir() else (RUNS / a.run if a.run else
                                                             max(RUNS.iterdir(), key=lambda p: p.name))
    s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    h = s["health"]
    print(f"{s['run']}  {s['start']}  {s['dauer_s']} s  port {s['port']}  pico {s['pico']}")
    print(f"zeilen {s['zeilen']}  kaputt {s['fehlerhafte_zeilen']}  verbindungen {s['verbindungen']}  "
          f"lücken {s['stream_luecken']} (max {s['max_luecke_s']} s)  vbus-ausfälle {s['vbus_ausfaelle']}")
    print(f"vsys {h['vsys']}  temp {h['temp']}  scan {h['scan']}  marker {[m['t'] for m in s['marker']]}")
    print(f"\n{'kanal':6}{'gp':>4}{'erk':>5}{'brüche':>8}{'glitch':>8}{'min ms':>9}{'mittel':>9}{'max ms':>9}")
    for name, k in s["kanaele"].items():
        b = k["bruch_ms"]
        print(f"{name:6}{k['gp']:>4}{'ja' if k['erkannt'] else '–':>5}{k['brueche']:>8}{k['glitches']:>8}"
              f"{b['min'] if b['min'] is not None else '–':>9}{b['mittel'] if b['mittel'] is not None else '–':>9}"
              f"{b['max']:>9}{'  OFFEN' if k['offen'] else ''}")

    pu = s.get("schlaege")
    if pu:
        print(f"
schläge {pu['ok']}  verworfen {pu['verworfen']}  max {pu['max_km_h']} km/h  mittel {pu['mittel_km_h']} km/h")

    warn = []
    if s["fehlerhafte_zeilen"]:
        warn.append(f"{s['fehlerhafte_zeilen']} kaputte zeilen")
    if s["stream_luecken"]:
        warn.append(f"{s['stream_luecken']} lücken im datenstrom")
    if s["verbindungen"] > 1:
        warn.append(f"{s['verbindungen'] - 1} reconnects")
    if s["vbus_ausfaelle"]:
        warn.append("vbus ausgefallen")
    if h["vsys"][0] is not None and h["vsys"][0] < 4.4:
        warn.append(f"vsys tief ({h['vsys'][0]} V)")
    warn += [f"{n}: {k['glitches']} glitches" for n, k in s["kanaele"].items() if k["glitches"]]
    print("\n" + ("WARNUNG: " + "; ".join(warn) if warn else "keine auffälligkeiten"))

    if a.events:
        with open(d / "events.csv", encoding="utf-8") as f:
            rows = list(csv.reader(f))[1:]
        print()
        for r in rows[-a.events:]:
            print("  ".join(r))


if __name__ == "__main__":
    main()
