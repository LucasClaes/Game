import array
import math
import threading
import pygame

_RATE = 44100

# ── note constants (Hz) ────────────────────────────────────────────────────────
_D2, _E2, _G2               = 73,  82,  98
_A2, _C3, _E3, _G3          = 110, 131, 165, 196
_A3, _B3, _C4, _D4          = 220, 247, 262, 294
_E4, _F4, _G4, _A4, _B4     = 330, 349, 392, 440, 494
_R                           = 0   # rest

# ── track definitions ─────────────────────────────────────────────────────────
# Each track: 16 quarter-note beats. Melody = triangle wave, Bass = square wave.
# Lengths must match: sum(beats) must equal same total for melody and bass.

_TRACKS = [
    # ── "Neon Run" — 140 BPM, driving A minor ─────────────────────────────────
    dict(bpm=140, melody=[
        (_E4,1), (_G4,1), (_A4,1), (_G4,1),
        (_E4,1), (_D4,.5), (_C4,.5), (_E4,1), (_R,1),
        (_A3,1), (_C4,1), (_D4,1), (_E4,1),
        (_G4,2), (_E4,1), (_A3,1),
    ], bass=[
        (_A2,1), (_A2,1), (_E2,1), (_A2,1),
        (_A2,1), (_G2,1), (_E2,1), (_G2,1),
        (_A2,1), (_A2,1), (_C3,1), (_E3,1),
        (_A2,2), (_E2,2),
    ]),

    # ── "Shadow March" — 105 BPM, slower, foreboding ──────────────────────────
    dict(bpm=105, melody=[
        (_A3,1.5), (_B3,.5), (_C4,2),
        (_E4,1.5), (_D4,.5), (_C4,1), (_B3,1),
        (_A3,1.5), (_G3,.5), (_A3,1), (_C4,1),
        (_E4,2), (_A3,2),
    ], bass=[
        (_A2,1), (_C3,1), (_E3,1), (_A2,1),
        (_A2,1), (_G2,1), (_C3,1), (_G2,1),
        (_A2,1), (_E3,1), (_A2,1), (_E2,1),
        (_A2,2), (_E2,2),
    ]),

    # ── "Speed Blitz" — 165 BPM, fast arpeggios ───────────────────────────────
    dict(bpm=165, melody=[
        (_A3,.5), (_C4,.5), (_E4,.5), (_G4,.5), (_A4,1), (_G4,.5), (_E4,.5),
        (_D4,.5), (_F4,.5), (_E4,.5), (_D4,.5), (_C4,1), (_A3,1),
        (_B3,.5), (_D4,.5), (_E4,.5), (_G4,.5), (_A4,1), (_G4,.5), (_E4,.5),
        (_A4,2), (_E4,1), (_A4,1),
    ], bass=[
        (_A2,.5), (_A2,.5), (_E2,.5), (_A2,.5), (_A2,.5), (_E2,.5), (_A2,.5), (_E2,.5),
        (_D2,.5), (_D2,.5), (_A2,.5), (_D2,.5), (_D2,.5), (_A2,.5), (_D2,.5), (_A2,.5),
        (_A2,.5), (_A2,.5), (_E2,.5), (_A2,.5), (_A2,.5), (_E2,.5), (_A2,.5), (_E2,.5),
        (_A2,2), (_E2,2),
    ]),
]


# ── waveform + envelope helpers ────────────────────────────────────────────────

def _note_buf(freq: float, n: int, wave: str, vol: float) -> list:
    if n <= 0:
        return []
    if freq == _R:
        return [0] * n
    atk = max(100, int(n * 0.05))
    rel = max(200, int(n * 0.20))
    inc = freq / _RATE
    # Chorus detuning for melody (two oscillators slightly apart)
    inc2 = (freq * 1.007) / _RATE if wave == 'tri' else inc
    buf = []
    for i in range(n):
        t  = (i * inc)  % 1
        t2 = (i * inc2) % 1
        if wave == 'tri':
            s  = 2 * abs(2 * t  - 1) - 1
            s2 = 2 * abs(2 * t2 - 1) - 1
            s  = s * 0.72 + s2 * 0.28   # chorus blend
        else:
            s = 1.0 if t < 0.5 else -1.0
        if i < atk:
            env = i / atk
        elif i >= n - rel:
            env = max(0.0, (n - i) / rel)
        else:
            env = 1.0
        buf.append(int(s * 32767 * vol * env))
    return buf


def _build_track(td: dict) -> list:
    sps = _RATE * 60.0 / td['bpm']  # samples per quarter-note

    def expand(notes, wave, vol):
        buf = []
        for freq, beats in notes:
            buf.extend(_note_buf(freq, int(beats * sps), wave, vol))
        return buf

    mel = expand(td['melody'], 'tri', 0.30)
    bas = expand(td['bass'],   'sq',  0.18)
    length = max(len(mel), len(bas))
    mel += [0] * (length - len(mel))
    bas += [0] * (length - len(bas))
    return [max(-32767, min(32767, m + b)) for m, b in zip(mel, bas)]


def _build_music() -> pygame.mixer.Sound:
    gap = [0] * int(_RATE * 0.4)   # 0.4 s silence between tracks
    all_samples: list[int] = []
    for i, td in enumerate(_TRACKS):
        all_samples.extend(_build_track(td))
        if i < len(_TRACKS) - 1:
            all_samples.extend(gap)
    return pygame.mixer.Sound(buffer=array.array('h', all_samples))


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
        self._music_channel: pygame.mixer.Channel | None = None
        self._enabled = False

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
        # Generate music in background — avoids delaying startup by ~1-2s
        threading.Thread(target=self._start_music, daemon=True).start()

    def _start_music(self):
        try:
            music = _build_music()
            ch = pygame.mixer.Channel(7)
            ch.play(music, loops=-1)
            ch.set_volume(0.15)
            self._music_channel = ch
        except Exception:
            pass

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
