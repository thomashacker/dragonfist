import numpy as np
import pygame

import sound


def test_midi():
    assert sound.midi("A4") == 69 and sound.midi("C4") == 60 and sound.midi("C#5") == 73


def test_all_sounds_render():
    for p in [sound.BASE | p for p in sound.DEFAULTS.values()] +              [sound.BASE | dict(wave=w, slide=-12, vibrato=0.5, lofi=2, vol=1) for w in sound.WAVES]:
        y = sound.render(p)
        n = len([x for x in p["notes"] if x])
        assert len(y) == int(sound.SR * p["ms"] / 1000) + int(sound.SR * p["gap"] / 1000) * (n - 1)
        assert np.isfinite(y).all() and 0.01 < np.abs(y).max() <= 1


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
