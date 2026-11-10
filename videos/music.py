"""Original cinematic/military-style background score, synthesized with numpy.

No samples or third-party music: low drone, staccato string ostinato, taiko-like
hits, brass-like chord pads, risers and impacts, arranged against cue times.

    from music import render
    render(path, duration, cues)   # cues: dict name -> seconds (see CUES below)
"""
from __future__ import annotations

import wave

import numpy as np

SR = 48000
BPM = 96
BEAT = 60 / BPM
rng = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def saw(f, t, harmonics=14, bright=0.18):
    """Band-limited, softened sawtooth (additive, rolled-off harmonics)."""
    out = np.zeros_like(t)
    for n in range(1, harmonics + 1):
        if f * n > SR / 2.2:
            break
        out += np.sin(2 * np.pi * f * n * t) / n * np.exp(-bright * (n - 1))
    return out


def env_adsr(n, a, d, s, r, sustain_len):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    e = np.zeros(n)
    i = 0
    seg = min(a, n); e[:seg] = np.linspace(0, 1, seg, endpoint=False); i = seg
    seg = min(d, n - i); e[i:i + seg] = np.linspace(1, s, seg, endpoint=False); i += seg
    hold = max(0, min(int(sustain_len * SR) - i, n - i)); e[i:i + hold] = s; i += hold
    seg = min(r, n - i); e[i:i + seg] = np.linspace(s, 0, seg); i += seg
    return e


def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(buf) or i + len(sig) <= 0:
        return
    j = min(len(buf), i + len(sig))
    buf[max(i, 0):j] += gain * sig[max(0, -i):j - i]


def lowpass(x, cutoff):
    """Gentle FFT lowpass (cosine roll-off)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    roll = np.clip((f - cutoff) / cutoff, 0, 1)
    X *= 0.5 * (1 + np.cos(np.pi * roll)) * (f < 2 * cutoff)
    return np.fft.irfft(X, len(x))


def taiko(gain=1.0, length=1.2, pitch=58):
    t = np.arange(int(length * SR)) / SR
    f = pitch * (1 + 0.9 * np.exp(-t * 28))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5)
    noise = lowpass(rng.standard_normal(len(t)), 900) * np.exp(-t * 30) * 0.6
    return gain * (body + noise)


def tick(gain=0.25):
    t = np.arange(int(0.06 * SR)) / SR
    n = rng.standard_normal(len(t))
    n = n - lowpass(n, 5000)  # highpass
    return gain * n * np.exp(-t * 70)


def impact(gain=1.0):
    t = np.arange(int(3.5 * SR)) / SR
    sub = np.sin(2 * np.pi * (38 + 40 * np.exp(-t * 6)) * t) * np.exp(-t * 1.6)
    crack = lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-t * 9) * 0.5
    tail = lowpass(rng.standard_normal(len(t)), 400) * np.exp(-t * 1.2) * 0.35
    return gain * (sub + crack + tail)


def riser(length, gain=0.35):
    t = np.arange(int(length * SR)) / SR
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    # sweep by blending progressively brighter lowpassed noise
    steps = 8
    for k in range(steps):
        band = lowpass(n, 300 * 2 ** (k * 0.6))
        w = np.clip(1 - np.abs(t / length * (steps - 1) - k), 0, 1)
        out += band * w
    return gain * out * (t / length) ** 2


def chord_pad(notes, length, gain=0.12, cutoff=1400):
    t = np.arange(int(length * SR)) / SR
    sig = np.zeros_like(t)
    for m in notes:
        for det in (-0.07, 0.0, 0.08):  # detuned unison
            sig += saw(hz(m + det), t, harmonics=10, bright=0.32)
    sig = lowpass(sig, cutoff)
    return gain * sig * env_adsr(len(t), 0.8, 0.5, 0.85, 1.2, length - 1.2)


def ostinato_note(m, gain=0.16):
    length = BEAT / 4 * 0.95
    t = np.arange(int(length * SR)) / SR
    sig = saw(hz(m), t, harmonics=12, bright=0.25) + 0.5 * saw(hz(m - 12), t, harmonics=8, bright=0.3)
    return gain * sig * np.exp(-t * 18)


# D minor progression (Dm Bb F C), two bars each, as MIDI chords
PROG = [[50, 53, 57, 62], [46, 50, 53, 58], [45, 48, 53, 57], [48, 52, 55, 60]]
ROOTS = [38, 34, 41, 36]
OST_PATTERN = [0, 0, 12, 0, 0, 0, 7, 0, 0, 0, 12, 0, 3, 0, 7, 0]


def render(path, duration, cues):
    n = int((duration + 0.5) * SR)
    L = np.zeros(n); R = np.zeros(n)
    mono = np.zeros(n)
    c = cues
    bar = 4 * BEAT

    def intensity(t):
        # 0 calm, 1 pulse, 2 drive, 3 full
        if t < c["search"]: return 0
        if t < c["lock"]: return 1
        if t < c["build_card"]: return 2
        if t < c["demo"]: return 0
        if t < c["alarm"]: return 1
        if t < c["celebrate"]: return 3
        return -1  # resolve

    # low drone throughout (fades in/out)
    t_all = np.arange(n) / SR
    drone = (saw(hz(26), t_all, 6, 0.5) + 0.6 * saw(hz(33), t_all, 6, 0.5))
    drone = lowpass(drone, 220) * 0.10
    fade = np.clip(t_all / 3, 0, 1) * np.clip((duration - t_all) / 4, 0, 1)
    mono += drone * fade

    # chords per two bars
    t = 0.0; k = 0
    while t < c["celebrate"]:
        lvl = intensity(t)
        if lvl >= 0:
            g = [0.05, 0.08, 0.11, 0.14][lvl]
            pad = chord_pad(PROG[k % 4], 2 * bar + 1.0, gain=g, cutoff=900 + 400 * lvl)
            add(L, t, pad, 1.0); add(R, t, pad * 0.9, 1.0)
        t += 2 * bar; k += 1

    # ostinato 16ths
    step = BEAT / 4
    t = c["search"]; i = 0
    while t < c["celebrate"]:
        lvl = intensity(t)
        if lvl >= 1:
            root = ROOTS[int(t // (2 * bar)) % 4] + 12
            g = [0, 0.10, 0.14, 0.17][lvl]
            note = ostinato_note(root + OST_PATTERN[i % 16], g)
            pan = 0.35 if i % 2 else -0.35
            add(L, t, note, 1 - pan); add(R, t, note, 1 + pan)
        t += step; i += 1

    # percussion
    t = c["search"]; b = 0
    while t < c["celebrate"]:
        lvl = intensity(t)
        if lvl >= 2:
            pos = b % 16  # 16 eighths = 2 bars
            if pos in (0, 6, 8, 11, 12):
                add(mono, t, taiko(0.55 if pos in (0, 8) else 0.35))
            if lvl == 3 and pos in (14, 15):
                add(mono, t, taiko(0.3, pitch=80))
        if lvl >= 1:
            add(mono, t, tick(0.10 if b % 2 else 0.16))
        t += BEAT / 2; b += 1

    # risers into hits, impacts on cues
    for name, g in (("demo", 0.8), ("alarm", 1.0), ("drone", 0.7), ("celebrate", 1.0)):
        add(mono, c[name] - 2.5, riser(2.5, 0.25))
        add(mono, c[name], impact(g))
    add(mono, c["lock"], impact(0.7))
    add(mono, 0.0, impact(0.5))

    # resolve: D major swell for the celebration and outro
    res = chord_pad([50, 54, 57, 62, 66], duration - c["celebrate"] + 0.5, gain=0.16, cutoff=1800)
    add(L, c["celebrate"], res); add(R, c["celebrate"], res * 0.95)
    hi = chord_pad([62, 66, 69, 74], duration - c["celebrate"] + 0.5, gain=0.06, cutoff=2600)
    add(L, c["celebrate"] + 0.3, hi * 0.8); add(R, c["celebrate"] + 0.3, hi)

    L += mono; R += mono
    st = np.stack([L, R], 1)[: int(duration * SR)]
    # soft master: normalize, gentle tanh saturation, final fade
    st /= np.max(np.abs(st)) + 1e-9
    st = np.tanh(st * 1.6) / np.tanh(1.6)
    tf = np.arange(len(st)) / SR
    st *= np.clip((duration - tf) / 2.5, 0, 1)[:, None]
    pcm = (st * 0.89 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
