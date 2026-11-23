"""Синтез звука и чиптюн-музыки на numpy (без внешних файлов)."""

import math

import numpy as np
import pygame

SR = 44100


def _wave(phase, kind):
    if kind == "sq":
        return np.where((phase % 1.0) < 0.5, 1.0, -1.0)
    if kind == "tri":
        return 4.0 * np.abs((phase % 1.0) - 0.5) - 1.0
    if kind == "saw":
        return 2.0 * (phase % 1.0) - 1.0
    return np.sin(phase * 2.0 * np.pi)


def tone(f0, f1, dur, kind="sq", vol=0.3, decay=18.0, attack=0.003):
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    if abs(f1 - f0) < 1e-6:
        phase = f0 * t
    else:
        freq = f0 * (f1 / f0) ** (t / dur)
        phase = np.cumsum(freq) / SR
    env = np.minimum(1.0, t / attack) * np.exp(-t * decay)
    return _wave(phase, kind) * env * vol


def noise(dur, vol=0.35, decay=25.0, smooth=2):
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    w = np.random.uniform(-1.0, 1.0, n)
    if smooth > 1:
        k = np.ones(smooth) / smooth
        w = np.convolve(w, k, mode="same")
    env = np.exp(-t * decay)
    return w * env * vol


def seq(*parts):
    return np.concatenate([np.asarray(p) for p in parts])


class Audio:
    def __init__(self):
        self.ok = pygame.mixer.get_init() is not None
        self.muted = False
        self.music_on = True
        self.sfx = {}
        self.music = None
        if not self.ok:
            return
        try:
            self._build()
        except Exception as exc:  # звук не критичен для игры
            print("audio disabled:", exc)
            self.ok = False

    # ---------------------------------------------------------------- sfx
    def _build(self):
        self.sfx["shoot"] = self._make(tone(640, 210, 0.10, "sq", 0.20, 30))
        self.sfx["shoot_power"] = self._make(tone(860, 240, 0.12, "sq", 0.20, 26))
        self.sfx["brick"] = self._make(noise(0.09, 0.42, 45, 2))
        self.sfx["steel"] = self._make(tone(1900, 1550, 0.06, "sq", 0.16, 60))
        self.sfx["hit"] = self._make(seq(noise(0.10, 0.30, 32, 3),
                                         tone(150, 70, 0.12, "tri", 0.14, 30)))
        self.sfx["boom"] = self._make(seq(noise(0.42, 0.50, 9, 4),
                                          tone(130, 38, 0.40, "tri", 0.35, 7)))
        self.sfx["bigboom"] = self._make(seq(noise(0.85, 0.60, 4.5, 6),
                                             tone(92, 28, 0.80, "tri", 0.42, 4.5)))
        self.sfx["pickup"] = self._make(seq(
            tone(660, 660, 0.06, "sq", 0.16, 8),
            tone(880, 880, 0.06, "sq", 0.16, 8),
            tone(1320, 1320, 0.10, "sq", 0.16, 7)))
        self.sfx["life"] = self._make(seq(
            tone(523, 523, 0.07, "sq", 0.17, 8),
            tone(784, 784, 0.07, "sq", 0.17, 8),
            tone(1046, 1046, 0.07, "sq", 0.17, 8),
            tone(1568, 1568, 0.14, "sq", 0.15, 6)))
        self.sfx["over"] = self._make(seq(
            tone(392, 392, 0.20, "sq", 0.18, 4),
            tone(330, 330, 0.20, "sq", 0.18, 4),
            tone(262, 262, 0.20, "sq", 0.18, 4),
            tone(196, 196, 0.55, "tri", 0.22, 3)))
        self.sfx["clear"] = self._make(seq(
            tone(523, 523, 0.10, "sq", 0.16, 6),
            tone(659, 659, 0.10, "sq", 0.16, 6),
            tone(784, 784, 0.10, "sq", 0.16, 6),
            tone(1046, 1046, 0.30, "sq", 0.16, 3.5)))
        self.sfx["pause"] = self._make(seq(
            tone(880, 880, 0.05, "sq", 0.13, 12),
            tone(660, 660, 0.07, "sq", 0.13, 10)))
        self.sfx["shield"] = self._make(tone(280, 940, 0.24, "tri", 0.20, 4))
        self.sfx["thud"] = self._make(tone(90, 60, 0.08, "tri", 0.18, 30))

        if self.music_on:
            self.music = self._make(self._build_music(), vol=0.62)

    def _make(self, samples, vol=1.0):
        a = np.clip(np.asarray(samples, dtype=np.float64) * vol, -1.0, 1.0)
        a = (a * 32767 * 0.85).astype(np.int16)
        return pygame.sndarray.make_sound(np.ascontiguousarray(a))

    # -------------------------------------------------------------- музыка
    def _build_music(self):
        bpm = 132.0
        step = 60.0 / bpm / 2.0
        total = 64
        buf = np.zeros(int(SR * step * total) + SR // 2)

        # 4 мотива по 8 шагов, повторяются с вариацией
        lead_bars = [
            [69, 0, 72, 0, 76, 0, 74, 0],
            [69, 0, 72, 76, 0, 79, 76, 0],
            [65, 0, 69, 0, 72, 0, 71, 0],
            [64, 0, 67, 0, 71, 0, 69, 0],
        ]
        bass_bars = [
            [45, 45, 45, 0, 52, 0, 45, 0],
            [45, 45, 45, 0, 52, 0, 45, 0],
            [41, 41, 41, 0, 48, 0, 41, 0],
            [43, 43, 43, 0, 50, 0, 43, 0],
        ]
        lead = lead_bars * 2
        bass = bass_bars * 2

        for bar in range(8):
            for i in range(8):
                idx = bar * 8 + i
                start = idx * step
                ln = lead[bar][i]
                if ln:
                    self._add(buf, start, step * 0.92,
                              440.0 * 2 ** ((ln - 69) / 12.0), "sq", 0.085, 5.0)
                bn = bass[bar][i]
                if bn:
                    self._add(buf, start, step * 0.95,
                              440.0 * 2 ** ((bn - 69) / 12.0), "tri", 0.16, 4.0)
            # барабаны
            for i in (0, 4):
                idx = bar * 8 + i
                self._add(buf, idx * step, 0.13, 120.0, "sine_kick", 0.30, 20.0)
            for i in range(0, 8, 2):
                idx = bar * 8 + i
                self._add(buf, idx * step, 0.035, 0.0, "hat", 0.12, 70.0)

        # мягкие края петли
        fade = int(SR * 0.02)
        buf[:fade] *= np.linspace(0, 1, fade)
        buf[-fade:] *= np.linspace(1, 0, fade)
        return buf

    def _add(self, buf, start, dur, freq, kind, vol, decay):
        i0 = int(start * SR)
        n = min(int(dur * SR), len(buf) - i0)
        if n <= 0:
            return
        t = np.arange(n) / SR
        env = np.minimum(1.0, t / 0.004) * np.exp(-t * decay)
        if kind == "hat":
            w = np.random.uniform(-1, 1, n)
            w = np.diff(w, prepend=0.0) * 0.5
        elif kind == "sine_kick":
            f = 120.0 * (45.0 / 120.0) ** (t / max(dur, 1e-6))
            w = np.sin(np.cumsum(f) / SR * 2 * np.pi)
        else:
            w = _wave(freq * t, kind)
        buf[i0:i0 + n] += w * env * vol

    # ------------------------------------------------------------- команды
    def play(self, name):
        if not self.ok or self.muted:
            return
        snd = self.sfx.get(name)
        if snd is not None:
            snd.play()

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            pygame.mixer.stop()
        elif self.ok and self.music_on and self.music is not None:
            self.music.play(loops=-1)

    def toggle_music(self):
        if not self.ok:
            return
        self.music_on = not self.music_on
        if self.music is None:
            return
        if self.music_on and not self.muted:
            self.music.play(loops=-1)
        else:
            self.music.stop()

    def start_music(self):
        if self.ok and self.music_on and not self.muted and self.music is not None:
            self.music.play(loops=-1)
