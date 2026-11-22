# Changelog

Every pull request to `main` bumps `VERSION` and adds an entry here.
Format: [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), versions: [SemVer](https://semver.org/lang/de/).

## [0.13.1] – 2026-11-22

### Added
- Saving a result offers all names from the highscores (most recent first) for a one-press pick; "+ NEUER NAME" opens the letter entry

## [0.13.0] – 2026-11-22

### Added
- Mode ZEIT: pick a time limit (10/20/30/60 s), 5 s countdown, the last 5 s are counted down with ticks; then the training stats
- Mode SCHLÄGE: pick a punch count (10/20/50/100); the clock starts with the first punch and stops at the last
- Mode REAKTION: pick rounds and punches per combo; after a random pause a beep sounds, measured is the time until the combo is through plane B; punching before the beep is a false start and the round repeats
- Highscore tabs TRAINING, ZEIT, SCHLÄGE, REAKTION, each with its own columns and ranking (punches per second, or reaction time)
- Punch results carry the times the fist entered plane A and plane B (`ta_s`, `tb_s`)
- Sounds: tick, los, piep, ende

### Removed
- Hidden ARENA placeholder menu

## [0.12.1] – 2026-11-22

### Added
- Settings: MUSIK on/off mutes only the background music; sound effects stay on

### Fixed
- Settings rows shrink to fit the screen (the last row was cut off)

## [0.12.0] – 2026-11-22

### Added
- Punch recording: choose person (1–9) and punch type (free, slow, fast, left only, right only, arm forward, cross); both are logged, the choice is kept for the next round
- `monitor/aufnahmen.py`: evaluates all recordings in one go (counted truth, live, current logic, B entries, share with speed, median, max; totals per punch type)

### Fixed
- Hand labels could flip for a whole training: two fists in the window are now ordered by position, and each hand's learned position stays on its half
- Retraction speeds above 40 km/h are treated as measurement errors like forward speeds

### Changed
- `monitor/pico.py` holds the device side (channels, protocol, state, serial reader); `monitor/monitor.py` keeps the monitor view
- Menus render at 30 fps, play scenes at 60 fps (less CPU and heat on the Jetson)

## [0.11.2] – 2026-11-22

### Added
- CLAUDE.md: maintenance workflow (replay real runs, failing test first, release and on-device check) and code rules

## [0.11.1] – 2026-11-22

### Fixed
- Serial reader joins lines split by the read timeout instead of parsing the halves as two broken lines
- Settings, highscores and summary.json are written atomically (temp file + rename), so a power cut never leaves a half-written file

### Changed
- Tests: no SCALED renderer under the dummy video driver (suite 18 s → 10 s); redundant tests merged (83 → 66), new tests for split serial lines and atomic writes

## [0.11.0] – 2026-11-22

### Added
- Title screen shows a Wi-Fi symbol: green with the network name when online, grey and crossed out when offline (checked every 10 s in the background)

## [0.10.1] – 2026-11-22

### Fixed
- Bogus speeds up to 82 km/h: an arm already in plane A that slides one beam sideways (neighbour beam freed < 6 ms before) no longer starts a new punch timer; the punch counts without a speed
- Speeds above 40 km/h are treated as measurement errors: the punch counts without a speed

## [0.10.0] – 2026-11-22

### Changed
- START offers only TRAINING for now; STORY and ARENA are hidden

## [0.9.3] – 2026-11-22

### Fixed
- The app writes `summary.json` every 5 s during a run, not only on exit

## [0.9.2] – 2026-11-22

### Fixed
- Double counts: a B beam next to an already broken B beam belongs to the same fist, so one punch through two neighbouring B beams is no longer split between two fists (real training: 92 counted for 93 B entries instead of 99)
- A forearm crossing plane A while another fist is in B no longer ends as a red miss
- A re-punch with an implausibly short time (> 36 km/h) counts without a speed instead of a bogus value

## [0.9.1] – 2026-11-22

### Fixed
- App crashed when a punch counted without a measurable speed (arm stayed in A and pushed through B again); such punches now count everywhere but stay out of speed values

## [0.9.0] – 2026-11-22

### Changed
- Punch detection tracks fists instead of fixed left/right halves: a fist is at most two A beams wide, a B beam belongs to the nearest fist, the hand follows the other fist and each hand's learned position. Diagonal punches through the middle no longer cause a false miss on the other side, and fast alternating punches are no longer merged (real recording at ~7 punches/s: 106 instead of 72 detected, 53/53 left/right)
- A fist that pulls back out of B while the arm stays in A and pushes through B again counts as a new punch
- A short wipe through A without reaching B (< 80 ms) is ignored instead of counted as a miss

### Added
- Settings → SCHLAG-AUFNAHME: punch for 15/30/60 s, then enter how many punches you really did; both go into the run log
- `monitor/analyse.py`: replays a run log through the punch logic like the live app, with block summary, independent B-entry count, per-recording comparison, event list and timeline image
- Regression test replaying a real fast training block

## [0.8.0] – 2026-11-22

### Added
- Training mode (START → TRAINING): endless, no limits, ends with ZURÜCK; live time, punches and last speed per hand
- Animated result pages in a loop: training time, punches (total, left, right, misses), punches per second curve with average and peak, speed curve out and back with averages and maximum, punch paths through the window with accuracy to the centre and spread per hand
- Save with an arcade name entry or discard; highscore table per discipline, reachable from the main menu
- Punch results carry retraction speed and the beams broken on each plane

## [0.7.0] – 2026-11-22

### Changed
- Punch detection runs per side: left and right hand are tracked independently and can punch at the same time; the middle B beam counts only for a side already in its A phase
- Mode screens count test punches per hand

### Added
- Pico firmware 3: takes LED commands from the app (`L <rrggbb> <rrggbb>`, `T` rainbow); falls back to its own colours 3 s after the last command
- LEDs dance in the menus; in modes each side shows its phase: off, orange A broken, green B broken, blue punch counted on retraction, red miss
- A sound for each phase

## [0.6.0] – 2026-11-22

### Added
- Pico firmware 2: WS2812B strips on GP16/GP19, fed piecewise through PIO so beam sampling never blocks (boot fill, dim red idle, side lights up while a beam on that side is broken, 35 % brightness)
- Pico hardware watchdog (8 s): a hung program restarts the board
- Reader wakes a silent Pico (Ctrl-C, Ctrl-B, Ctrl-D) after 3 s without data and reopens the port after two tries

## [0.5.1] – 2026-11-22

### Fixed
- Splash stays fullscreen behind the app, so a restart shows no desktop at all; stops at once on SIGTERM

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
