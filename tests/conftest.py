import os
import sys
from argparse import Namespace
from pathlib import Path

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "monitor")]


@pytest.fixture
def app(tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "CFG_FILE", tmp_path / "settings.json")
    a = main.App(Namespace(sim=True, port=None, abstand=None, fullscreen=False, mute=True, no_log=True,
                           runs=str(tmp_path)))
    a.running = True
    yield a
    a.stop.set()
    pygame.quit()
