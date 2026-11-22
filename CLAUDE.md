# Arbeitsweise

Wartung nach dem Skill `schmuhlsche-skills` (Teil `software.md`). Kurzfassung:

## Jede Code-Änderung

1. Problem am echten Lauf beziffern: `runs/<lauf>/raw.log` vom Gerät holen,
   `python monitor/analyse.py <lauf> [--von s --bis s]` nachspielen, gegen die B-Eintritte vergleichen.
   Schlag-Aufnahmen mit gezählter Wahrheit: `python monitor/aufnahmen.py runs` (vorher `scp -r jetson:dragonfist/runs .`).
2. Kleinste Änderung, die die Ursache trifft.
3. Test, der ohne Fix fehlschlägt. Fehler aus echten Daten: Lauf nach `tests/data/<name>/raw.log`
   plus Replay-Test mit Grenzen.
4. `pytest -q` grün, Replay aller `tests/data/*` nicht schlechter (Treffer, Anteil mit Tempo, Median, Höchstwert).
5. Branch → PR mit `VERSION` + `CHANGELOG.md` → squash-merge → `ssh jetson 'cd ~/dragonfist && bash deploy/update.sh'`.
6. Auf dem Jetson prüfen: Dienst aktiv, Version, neuer Lauf schreibt Logs, Highscores und Einstellungen erhalten.

## Regeln

- Optionale Ergebnisfelder (`v`, `vb`, `dt` können `None` sein) in jedem Verbraucher abfangen.
- Physikalische Grenzen statt Fantasiewerten: lieber zählen ohne Tempo.
- Dauerhafte Dateien nur über `runlog.schreiben` (atomar).
- Serieller Eingang: nur komplette Zeilen verarbeiten.
- Tests: den niedrigsten Test behalten, der den Fehler fängt; gleiche Fälle parametrisieren;
  langsame Tests mit `pytest --durations=12` finden und beheben.
- Code-Audit (Checkliste in `software.md`) vor jedem Einsatz und an Meilensteinen.
- Öffentliches Repo: keine KI-Attribution, keine privaten Daten, wenige Kommentare, schlanker Code.
