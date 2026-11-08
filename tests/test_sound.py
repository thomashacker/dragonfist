import numpy as np
import pygame
import pytest

import sound


def test_midi():
    assert sound.midi("A4") == 69 and sound.midi("C4") == 60 and sound.midi("C#5") == 73


@pytest.mark.parametrize("name", list(sound.DEFAULTS))
def test_defaults_render(name):
    p = sound.BASE | sound.DEFAULTS[name]
    y = sound.render(p)
    n = len([x for x in p["notes"] if x])
    assert len(y) == int(sound.SR * p["ms"] / 1000) + int(sound.SR * p["gap"] / 1000) * (n - 1)
    assert np.isfinite(y).all() and np.abs(y).max() <= 1
    assert np.abs(y).max() > 0.01


@pytest.mark.parametrize("wave", sound.WAVES)
def test_waves_and_effects(wave):
    y = sound.render(sound.BASE | dict(wave=wave, slide=-12, vibrato=0.5, lofi=2, vol=1))
    assert np.isfinite(y).all() and np.abs(y).max() <= 1
    assert len(np.unique(np.round(y * 127))) <= 255


def test_sfx_builds_all():
    pygame.mixer.init(44100, -16, 1, 256)
    try:
        s = sound.Sfx()
        assert set(s.snd) == set(sound.DEFAULTS)
        s.volume(0.5)
        s.play("treffer")
        s.play("gibtsnicht")
    finally:
        pygame.mixer.quit()
