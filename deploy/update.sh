#!/bin/bash
if [ -z "$DF_COPY" ]; then
  t=$(mktemp)
  cp "$0" "$t"
  DF_COPY=1 DF_ROOT="$(cd "$(dirname "$0")/.." && pwd)" exec bash "$t"
fi
trap 'rm -f "$0"' EXIT
cd "$DF_ROOT" || exit 1
LOG=$HOME/.local/state/dragonfist/update.log
mkdir -p "$(dirname "$LOG")"
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

[ -e "$HOME/.dragonfist-noupdate" ] && exit 0
git fetch -q origin main 2>/dev/null || exit 0
old=$(git rev-parse HEAD)
new=$(git rev-parse origin/main)
[ "$old" = "$new" ] && exit 0

req=$(git diff --name-only "$old" "$new" -- requirements.txt requirements-dev.txt)
git reset -q --hard "$new"
[ -n "$req" ] && .venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt >> "$LOG" 2>&1

if SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -x -p no:cacheprovider > /tmp/dragonfist-tests.log 2>&1; then
  systemctl --user daemon-reload
  systemctl --user restart dragonfist.service
  log "update ${old:0:7} -> ${new:0:7} v$(cat VERSION)"
else
  git reset -q --hard "$old"
  [ -n "$req" ] && .venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt >> "$LOG" 2>&1
  log "tests failed on ${new:0:7}, stayed on ${old:0:7}: $(tail -1 /tmp/dragonfist-tests.log)"
fi
