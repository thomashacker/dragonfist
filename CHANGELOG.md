# Changelog

Every pull request to `main` bumps `VERSION` and adds an entry here.
Format: [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), versions: [SemVer](https://semver.org/lang/de/).

## [0.2.0] – 2026-11-21

### Added
- Jetson kiosk: app starts after power-on (GDM autologin + systemd user service, restarts on crash)
- Auto-update: polls `origin/main` every 2 min, pulls, installs requirements, runs the tests, restarts the app; rolls back if the tests fail
- `VERSION` file, shown on the title screen
- `CHANGELOG.md`

### Changed
- Title menu: two large square tiles side by side, START and EINSTELLUNGEN
- START opens a second tile menu with STORY and ARENA; ARENA modes as tiles
- Calibration moved into the settings
- Larger fonts and controls everywhere for the 7" display

## [0.1.0] – 2026-11-15

### Added
- Pico sensor firmware with serial protocol (`S`, `E`, `H`, `I`)
- Live monitor with punch detection, speed, sounds and run logging
- App: intro, title menu, arena, settings, calibration, simulated punches, synth sounds
- Tests for punch detection, parser, run log, synth, all scenes and performance budgets
- Parametric build123d CAD model under `cad/`
