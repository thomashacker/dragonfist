# Changelog

Every pull request to `main` bumps `VERSION` and adds an entry here.
Format: [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), versions: [SemVer](https://semver.org/lang/de/).

## [0.5.0] – 2026-11-22

### Added
- Splash service: black screen with "STARTET …" / update status whenever the app is not running, so the desktop stays hidden on boot, update and restart
- Update banner in the app while an update installs
- install.sh sets a black desktop and hides desktop icons and dock

### Fixed
- App and monitor stop the Pico reader thread before exit (no more core dump on stop)

## [0.4.1] – 2026-11-22

### Changed
- CAD wiring (Steckplan, pins.json, Wokwi) follows the B3 → GP22, B5 → GP14 move

## [0.4.0] – 2026-11-21

### Added
- Channels stuck at "interrupted" for more than 5 s are marked DEFEKT and ignored by punch detection; they recover automatically once they see light again

## [0.3.2] – 2026-11-21

### Changed
- Sensor B3 moved from GP26 to GP22, B5 from GP20 to GP14 (wiring fault on the old breadboard rows); Pico firmware must be re-flashed

## [0.3.1] – 2026-11-21

### Changed
- Sign "schmuhlsches wissen" 116 mm wide with two Ø3 mm screw holes for 2.5×16 pan-head screws

## [0.3.0] – 2026-11-21

### Added
- Background music: title theme in menus, action theme in modes, silence during calibration and intro
- Music follows volume and TON setting

## [0.2.2] – 2026-11-21

### Changed
- Mouse cursor hidden while the app runs

## [0.2.1] – 2026-11-21

### Changed
- Bundled font DejaVu Sans Mono Bold (`app/assets/fonts/`, Bitstream Vera license) for app and monitor, same look on PC and Jetson, close to the Wiremod console font
- Title tiles show only START and EINSTELLUNGEN

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
