"""Schwarzer Bildschirm mit Status, solange die App nicht läuft (Boot, Update, Neustart)."""
import signal
import sys
import time
from pathlib import Path

STATE = Path.home() / ".local" / "state" / "dragonfist"
STATUS, LOCK = STATE / "status", STATE / "app.lock"


def status():
    try:
        if time.time() - STATUS.stat().st_mtime < 900:
            return STATUS.read_text(encoding="utf-8").strip() or None
    except OSError:
        pass


def hold_lock():
    """Die App hält die Sperre, sobald ihr Fenster steht; der Splash versteckt sich dann."""
    try:
        import fcntl
        STATE.mkdir(parents=True, exist_ok=True)
        f = open(LOCK, "w")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except (ImportError, OSError):
        return None


def app_running():
    f = hold_lock()
    if f:
        f.close()
    return f is None


def main():
    import pygame
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "monitor"))
    from monitor import font
    pygame.display.init()
    pygame.font.init()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    gross, klein, win = font(46), font(22), None
    while True:
        laeuft = app_running()
        if win:
            pygame.event.pump()
        if laeuft and win and pygame.key.get_focused():      # liegt über der App -> weg
            pygame.display.quit()
            pygame.display.init()
            win = None
        elif not laeuft and not win:
            win = pygame.display.set_mode((1024, 600), pygame.FULLSCREEN | pygame.SCALED)
            pygame.display.set_caption("DRAGONFIST")
            pygame.mouse.set_visible(False)
        if win:                                              # bleibt hinter der App liegen
            win.fill((0, 0, 0))
            for f, t, y, c in ((gross, "DRAGONFIST", 270, (120, 120, 120)),
                               (klein, status() or "STARTET …", 330, (90, 230, 130))):
                img = f.render(t, True, c)
                win.blit(img, img.get_rect(center=(512, y)))
            pygame.display.flip()
        time.sleep(0.25)


if __name__ == "__main__":
    main()
