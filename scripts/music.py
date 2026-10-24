"""Background tracks synthesised from scratch (no samples), so the demo video carries no third-party music rights."""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
SR = 44100
LENGTH = 30.0
rng = np.random.default_rng(3)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, (lo, hi), "band", fs=SR, output="sos"), x)


def env(n, a, r, sustain=1.0):
    e = np.full(n, sustain)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na) * sustain if na < n else np.linspace(0, 1, n) * sustain
    nr = min(n, int(r * SR))
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


class Mix:
    def __init__(self):
        self.dry = np.zeros((int(LENGTH * SR) + SR * 4, 2))
        self.wet = np.zeros_like(self.dry)

    def add(self, at, sig, gain=1.0, pan=0.0, send=0.0):
        i = int(at * SR)
        if i >= len(self.dry):
            return
        sig = sig[: len(self.dry) - i] * gain
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        st = np.stack([sig * l, sig * r], -1) * np.sqrt(2)
        self.dry[i:i + len(sig)] += st
        if send:
            self.wet[i:i + len(sig)] += st * send

    def render(self, decay=0.7, wet_gain=0.35, duck=None):
        n = int(2.8 * SR)
        t = np.arange(n) / SR
        ir = np.stack([rng.normal(0, 1, n), rng.normal(0, 1, n)], -1) * np.exp(-t / decay)[:, None]
        ir = np.stack([lp(ir[:, 0], 6000), lp(ir[:, 1], 6000)], -1) / np.sqrt(n * decay / 2.8)
        wet = np.stack([fftconvolve(self.wet[:, c], ir[:, c])[: len(self.wet)] for c in (0, 1)], -1)
        out = self.dry + wet * wet_gain
        if duck is not None:
            out *= duck[: len(out), None]
        out = out[: int(LENGTH * SR)]
        out *= env(len(out), 0.02, 2.5)[:, None]
        out = np.tanh(out * 1.2) / np.tanh(1.2)
        return out / np.max(np.abs(out)) * 0.89


# ---------- instruments ----------

def kick(soft=False):
    t = tt(0.45)
    f = 45 + 110 * np.exp(-t / 0.035)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.16 if soft else 0.22))
    click = hp(rng.normal(0, 1, len(t)), 3000) * np.exp(-t / 0.004) * 0.25
    return s + (0 if soft else click)


def clap():
    t = tt(0.3)
    n = bp(rng.normal(0, 1, len(t)), 900, 5000)
    e = np.exp(-t / 0.09)
    for d in (0.0, 0.011, 0.022):
        e = np.maximum(e, (t >= d) * np.exp(-np.maximum(t - d, 0) / 0.006) * 1.2)
    return n * e


def hat(open_=False):
    t = tt(0.25 if open_ else 0.06)
    return hp(rng.normal(0, 1, len(t)), 7500) * np.exp(-t / (0.08 if open_ else 0.014))


def snare_soft():
    t = tt(0.25)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    return lp(bp(rng.normal(0, 1, len(t)), 1200, 6000), 4500) * np.exp(-t / 0.08) * 0.8 + body * 0.5


def pluck(m, dur=0.6, bright=1.0):
    f, t = hz(m), tt(dur)
    s = np.zeros_like(t)
    for k in range(1, 40):
        if f * k > 12000:
            break
        s += np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (4 + k * 2.2 / bright))
    return s * env(len(t), 0.002, 0.08)


def saw(f, t, detune=0.0):
    return 2 * ((f * (1 + detune) * t + rng.random()) % 1) - 1


def pad(notes, dur, cutoff=1800, voices=5, spread=0.012):
    t = tt(dur)
    s = np.zeros_like(t)
    for m in notes:
        for v in range(voices):
            s += saw(hz(m), t, (v - (voices - 1) / 2) * spread / voices)
    return lp(s / (len(notes) * voices), cutoff, 2) * env(len(t), 0.35, 0.6)


def keys(m, dur):
    f, t = hz(m), tt(dur)
    tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.4)
    bell = 0.18 * np.sin(2 * np.pi * 7.02 * f * t) * np.exp(-t / 0.06) if f * 7 < 16000 else 0
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    return (tone + bell) * np.exp(-t / 1.6) * trem * env(len(t), 0.004, 0.3)


def bass(m, dur, grit=0.25):
    f, t = hz(m), tt(dur)
    s = np.sin(2 * np.pi * f * t) + grit * lp(saw(f, t), 600)
    return s * env(len(t), 0.005, 0.06)


def riser(dur):
    t = tt(dur)
    n = rng.normal(0, 1, len(t))
    out = np.zeros_like(n)
    seg = len(t) // 24
    for i in range(24):
        a, b = i * seg, (i + 1) * seg if i < 23 else len(t)
        out[a:b] = bp(n, 300 + 7000 * (i / 23) ** 2, 700 + 9000 * (i / 23) ** 2)[a:b]
    return out * (t / dur) ** 2


def sidechain(bpm, depth=0.6, first_bar=0):
    beat = 60 / bpm
    n = int((LENGTH + 4) * SR)
    t = np.arange(n) / SR
    ph = (t % beat) / beat
    d = 1 - depth * np.exp(-ph * 9)
    d[t < first_bar * 4 * beat] = 1
    return d


# ---------- tracks ----------

PROG = [[53, 57, 60, 64], [55, 59, 62, 64], [52, 55, 59, 62], [57, 60, 64, 67]]  # Fmaj7 G6 Em7 Am7
ROOTS = [41, 43, 40, 45]


def tech():
    bpm, mix = 118, Mix()
    beat = 60 / bpm
    bar = 4 * beat
    for b in range(int(LENGTH / bar) + 1):
        t0, ch = b * bar, PROG[b % 4]
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[2] + 12, ch[1] + 12, ch[3] + 12, ch[2] + 24]
        for i, m in enumerate(arp):
            mix.add(t0 + i * beat / 2, pluck(m, 0.7, 0.8 if b < 2 else 1.1), 0.16, (-0.35, 0.35)[i % 2], 0.5)
        if b >= 1:
            mix.add(t0, pad([n + 12 for n in ch], bar + 0.4, 1500), 0.22, 0, 0.6)
        if b >= 2:
            for i in range(4):
                mix.add(t0 + i * beat, kick(True), 0.55)
                mix.add(t0 + i * beat + beat / 2, hat(), 0.07, 0.25)
            for i in (1, 3):
                mix.add(t0 + i * beat, snare_soft(), 0.18, 0, 0.25)
            mix.add(t0, bass(ROOTS[b % 4], beat * 1.8), 0.32)
            mix.add(t0 + beat * 2.5, bass(ROOTS[b % 4], beat * 1.3), 0.26)
    return mix.render(decay=0.9, wet_gain=0.45, duck=sidechain(bpm, 0.35, 2))


def energy():
    bpm, mix = 126, Mix()
    beat = 60 / bpm
    bar = 4 * beat
    prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    roots = [45, 41, 48, 43]
    drop = 4
    for b in range(int(LENGTH / bar) + 1):
        t0, ch = b * bar, prog[b % 4]
        on = b >= drop
        mix.add(t0, pad([n + 12 for n in ch] + [ch[0] + 24], bar + 0.3, 3200 if on else 900, 7, 0.02), 0.3, 0, 0.35)
        lead = [ch[0] + 24, ch[2] + 12, ch[1] + 24, ch[2] + 12] * 4
        for i, m in enumerate(lead):
            if on or i % 2 == 0:
                mix.add(t0 + i * beat / 4, pluck(m, 0.25, 1.6), 0.09 if on else 0.06, (-0.3, 0.3)[i % 2], 0.3)
        if b < 2:
            continue
        for i in range(4):
            if on or b == 3:
                mix.add(t0 + i * beat, kick(), 0.8)
            mix.add(t0 + i * beat + beat / 2, hat(open_=on), 0.08 if on else 0.05, 0.2)
            if on:
                for s in (0.25, 0.75):
                    mix.add(t0 + (i + s) * beat, hat(), 0.04, -0.3)
        if on:
            for i in (1, 3):
                mix.add(t0 + i * beat, clap(), 0.3, 0, 0.3)
            for i in range(4):
                mix.add(t0 + (i + 0.5) * beat, bass(roots[b % 4], beat * 0.45, 0.6), 0.42)
        if b == drop - 1:
            mix.add(t0, riser(bar), 0.18, 0, 0.4)
    return mix.render(decay=0.6, wet_gain=0.3, duck=sidechain(bpm, 0.65, drop))


def lofi():
    bpm, mix = 84, Mix()
    beat = 60 / bpm
    bar = 4 * beat
    swing = beat / 2 * 0.62
    prog = [[50, 53, 57, 60, 64], [55, 59, 62, 65], [48, 52, 55, 59, 62], [45, 48, 52, 55]]  # Dm9 G7 Cmaj9 Am7
    roots = [38, 43, 36, 45]
    for b in range(int(LENGTH / bar) + 1):
        t0, ch = b * bar, prog[b % 4]
        for j, m in enumerate(ch):
            mix.add(t0 + j * 0.012, keys(m + 12, bar * 0.6), 0.13, (j - 2) * 0.15, 0.4)
        for j, m in enumerate(ch[1:4]):
            mix.add(t0 + beat * 2 + swing + j * 0.01, keys(m + 12, beat * 1.4), 0.08, 0.2, 0.4)
        if b >= 1:
            mix.add(t0, kick(True), 0.6)
            mix.add(t0 + beat * 2 + swing, kick(True), 0.45)
            for i in (1, 3):
                mix.add(t0 + i * beat, lp(snare_soft(), 3000), 0.3, 0, 0.2)
            for i in range(4):
                mix.add(t0 + i * beat, lp(hat(), 9000), 0.05, 0.3)
                mix.add(t0 + i * beat + swing, lp(hat(), 9000), 0.03, 0.3)
            mix.add(t0, bass(roots[b % 4], beat * 1.6, 0.1), 0.38)
            mix.add(t0 + beat * 2.5, bass(roots[b % 4] + 7, beat * 1.2, 0.1), 0.28)
    out = mix.render(decay=1.1, wet_gain=0.4)
    n = len(out)
    crackle = (rng.random(n) > 0.9993) * rng.normal(0, 0.35, n)
    vinyl = lp(hp(rng.normal(0, 0.012, n) + crackle, 800), 5000)
    wow = 1 + 0.002 * np.sin(2 * np.pi * 0.5 * np.arange(n) / SR)
    out = np.stack([lp(out[:, c], 7000) * wow for c in (0, 1)], -1) + vinyl[:, None]
    return out / np.max(np.abs(out)) * 0.89


TRACKS = {"tech": tech, "energy": energy, "lofi": lofi}

if __name__ == "__main__":
    out = ROOT / "build/music"
    out.mkdir(parents=True, exist_ok=True)
    for name in sys.argv[1:] or TRACKS:
        wavfile.write(out / f"{name}.wav", SR, (TRACKS[name]() * 32767).astype(np.int16))
        print(out / f"{name}.wav")
