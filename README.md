# dragonfist
repo for the dragonfist project

## Setup
```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

## Pico
```
mpremote cp pico/main.py :main.py + reset
```
Serial protocol (115200, one line per message):
- `S <mask>` channel states every 50 ms, bit i = channel i, 1 = beam received
- `E <ch> <0|1> <t_us>` on every change
- `H <vbus> <vsys_mV> <temp_dC> <scan_hz> <uptime_ms>` every 500 ms
- `I <fw> <uid> <n_a> <n_b>` every 2 s

## Monitor
```
python monitor/monitor.py [--port COM6] [--abstand 200] [--fullscreen] [--demo] [--mute]
```

Keys: `M` marker, `R` reset counters, `S` sound, `F` fullscreen, `ESC` quit.

Punch: first A break starts, first B break stops, counted once all beams are clear for 30 ms. Speed = `--abstand` (mm, A to B) / dt.

## Runs
Every monitor session writes `runs/<timestamp>/`: `raw.log` (all serial lines, host time), `events.csv` (breaks with Pico µs timestamps and duration, glitch < 3 ms), `health.csv`, `punches.csv`, `summary.json` (updated every 5 s).
```
python monitor/report.py [run] [--events N]
```
