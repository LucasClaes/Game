import array
import math
import pygame

_RATE = 44100


def _sine(freq: float, dur: float, vol: float = 0.5) -> pygame.mixer.Sound:
    n = int(dur * _RATE)
    buf = array.array('h', [
        int(math.sin(2 * math.pi * freq * i / _RATE) * 32767 * vol)
        for i in range(n)
    ])
    return pygame.mixer.Sound(buffer=buf)


def _square(freq: float, dur: float, vol: float = 0.3) -> pygame.mixer.Sound:
    n = int(dur * _RATE)
    buf = array.array('h', [
        int((1 if (i * freq / _RATE) % 1 < 0.5 else -1) * 32767 * vol)
        for i in range(n)
    ])
    return pygame.mixer.Sound(buffer=buf)


def _make_loop() -> pygame.mixer.Sound:
    """Short arcade melody that loops as background music."""
    beat = _RATE * 60 // 130  # 130 BPM
    # Simple minor-ish progression: A3 C4 E4 G4 F4 E4 D4 A3
    notes = [220, 261, 329, 392, 349, 329, 293, 220]
    bufs: list[int] = []
    for freq in notes:
        n = beat
        # Square wave + soft sine overtone for a retro synth feel
        for i in range(n):
            sq  = 1 if (i * freq / _RATE) % 1 < 0.5 else -1
            sin = math.sin(2 * math.pi * freq * i / _RATE)
            fade = min(1.0, min(i, n - i) / (n * 0.04 + 1))
            sample = int((sq * 0.6 + sin * 0.4) * 32767 * 0.20 * fade)
            bufs.append(sample)
    return pygame.mixer.Sound(buffer=array.array('h', bufs))


class AudioManager:
    def __init__(self):
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._music_channel: pygame.mixer.Channel | None = None
        self._enabled = False

    def load(self):
        s = self._sounds
        s['shoot']       = _square(880,  0.07, vol=0.22)
        s['melee']       = _square(130,  0.10, vol=0.32)
        s['enemy_die']   = _square(75,   0.16, vol=0.38)
        s['player_hurt'] = _square(190,  0.20, vol=0.42)
        s['coin']        = _sine(1320,  0.07, vol=0.28)
        s['level_up']    = _sine(660,   0.30, vol=0.38)
        s['boss_roar']   = _square(50,   0.40, vol=0.48)
        s['game_over']   = _sine(100,   0.70, vol=0.42)
        self._music_channel = pygame.mixer.Channel(7)
        music = _make_loop()
        self._music_channel.play(music, loops=-1)
        self._music_channel.set_volume(0.15)
        self._enabled = True

    def play(self, name: str):
        if not self._enabled:
            return
        snd = self._sounds.get(name)
        if snd:
            snd.play()

    def stop_music(self):
        if self._music_channel:
            self._music_channel.stop()

    def set_music_volume(self, vol: float):
        if self._music_channel:
            self._music_channel.set_volume(vol)


audio = AudioManager()
