import array
import math
import os
import pygame

_RATE = 44100

MUSIC_TRACKS = {
    "menu":          "assets/music/menu.mp3",
    "combat":        "assets/music/combat.mp3",
    "shop":          "assets/music/shop.mp3",
    "levelcomplete": "assets/music/levelcomplete.mp3",
    "gameover":      "assets/music/gameover.mp3",
}


# ── SFX helpers ────────────────────────────────────────────────────────────────

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


# ── AudioManager ───────────────────────────────────────────────────────────────

class AudioManager:
    def __init__(self):
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        self._current_track: str | None = None
        self._pending_music: str | None = None
        self._fade_timer: float = 0.0
        self._music_vol: float = 0.4
        self._sfx_vol: float = 1.0
        self._vol_target: float | None = None
        self._vol_speed: float = 0.0
        self._vol_pause_at_zero: bool = False

    def load(self):
        s = self._sounds
        s['shoot']       = _square(880,  0.07, vol=0.22)
        s['melee']       = _square(130,  0.10, vol=0.32)
        s['enemy_die']   = _square(75,   0.16, vol=0.38)
        s['player_hurt'] = _square(190,  0.20, vol=0.42)
        s['coin']        = _sine(1320,   0.07, vol=0.28)
        s['level_up']    = _sine(660,    0.30, vol=0.38)
        s['boss_roar']   = _square(50,   0.40, vol=0.48)
        s['game_over']   = _sine(100,    0.70, vol=0.42)
        self._enabled = True
        self._apply_sfx_volume()

    def play_music(self, track: str, fade_ms: int = 800) -> None:
        if not self._enabled or track == self._current_track:
            return
        path = MUSIC_TRACKS.get(track)
        if not path or not os.path.exists(path):
            return
        self._current_track = track
        self._pending_music = path
        self._fade_timer = fade_ms / 1000.0
        self._vol_target = None  # cancel any volume fade in progress
        pygame.mixer.music.unpause()  # ensure not paused before fadeout
        pygame.mixer.music.set_volume(self._music_vol)
        pygame.mixer.music.fadeout(fade_ms)

    def update(self, dt: float) -> None:
        if self._pending_music:
            self._fade_timer -= dt
            if self._fade_timer <= 0:
                try:
                    pygame.mixer.music.load(self._pending_music)
                    pygame.mixer.music.set_volume(self._music_vol)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
                self._pending_music = None

        if self._vol_target is not None:
            cur = pygame.mixer.music.get_volume()
            diff = self._vol_target - cur
            step = self._vol_speed * dt
            if abs(diff) <= step:
                pygame.mixer.music.set_volume(self._vol_target)
                if self._vol_pause_at_zero and self._vol_target == 0.0:
                    pygame.mixer.music.pause()
                    self._vol_pause_at_zero = False
                self._vol_target = None
            else:
                pygame.mixer.music.set_volume(cur + (1 if diff > 0 else -1) * step)

    def fade_to_vol(self, target: float, duration: float, pause_at_zero: bool = False):
        if not self._enabled:
            return
        if duration <= 0:
            pygame.mixer.music.set_volume(target)
            if pause_at_zero and target == 0.0:
                pygame.mixer.music.pause()
            return
        cur = pygame.mixer.music.get_volume()
        self._vol_target = target
        self._vol_speed = abs(target - cur) / duration
        self._vol_pause_at_zero = pause_at_zero

    def play(self, name: str):
        if not self._enabled:
            return
        snd = self._sounds.get(name)
        if snd:
            snd.play()

    def stop_music(self):
        pygame.mixer.music.fadeout(800)
        self._current_track = None
        self._pending_music = None

    def set_music_volume(self, vol: float):
        self._music_vol = max(0.0, min(1.0, vol))
        pygame.mixer.music.set_volume(self._music_vol)

    def set_sfx_volume(self, vol: float):
        self._sfx_vol = max(0.0, min(1.0, vol))
        self._apply_sfx_volume()

    def _apply_sfx_volume(self):
        for snd in self._sounds.values():
            snd.set_volume(self._sfx_vol)


audio = AudioManager()
