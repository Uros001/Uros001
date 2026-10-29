"""Synthesized ambience and spot effects, laid out from the EDL. No recorded or third-party audio.

  python3 sfx.py <out_ambience.wav> <out_fx.wav>
"""
import os, sys, math, random
import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from film import core, edl
from film.shots import Plate, Archive, Diptych, Sequence, DocPage

SR = 48000
rng = np.random.default_rng(11)


def pink(n, ch=2):
    X = np.fft.rfft(rng.normal(0, 1, (n, ch)), axis=0)
    f = np.arange(X.shape[0])
    f[0] = 1
    X /= np.sqrt(f)[:, None]
    y = np.fft.irfft(X, n, axis=0)
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def brown(n, ch=2):
    y = np.cumsum(rng.normal(0, 1, (n, ch)), axis=0)
    y = signal.lfilter([1, -1], [1, -0.995], y, axis=0)
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos')
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def lp(x, hi, order=2):
    sos = signal.butter(order, hi / (SR / 2), 'low', output='sos')
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def lfo(n, rate, depth, base=1.0, seed=0):
    t = np.arange(n) / SR
    r = np.random.default_rng(seed)
    v = np.zeros(n)
    for k in range(3):
        v += np.sin(2 * math.pi * rate * (0.6 + 0.6 * k) * t + r.uniform(0, 6.28)) / (k + 1)
    v = v / 1.83
    return (base + depth * v).astype(np.float32)[:, None]


def norm(x, peak=0.5):
    return (x / (np.abs(x).max() + 1e-9) * peak).astype(np.float32)


# ------------------------------------------------------------------ ambience beds
def bed_water(n):
    base = lp(brown(n), 500) * 0.6 + bp(pink(n), 300, 1200) * 0.12 * lfo(n, 0.15, 0.5, 1.0, 1)
    out = base.copy()
    t = 0
    while t < n:
        L = int(rng.uniform(0.12, 0.45) * SR)
        if t + L >= n:
            break
        burst = bp(rng.normal(0, 1, (L, 2)).astype(np.float32), rng.uniform(250, 500), rng.uniform(900, 1800))
        env = np.sin(np.linspace(0, math.pi, L)) ** 2
        pan = rng.uniform(-0.7, 0.7)
        burst *= env[:, None] * np.array([1 - pan, 1 + pan], np.float32) * rng.uniform(0.15, 0.4)
        out[t:t + L] += burst
        t += int(rng.uniform(0.4, 1.8) * SR)
    return norm(out, 0.5)


def bed_wind(n, cold=False):
    g = lfo(n, 0.06, 0.45, 0.8, 3)
    body = bp(pink(n), 250, 1800) * g + lp(brown(n), 200) * 0.4
    hiss = bp(pink(n), 3500, 9000) * 0.25 * lfo(n, 0.11, 0.6, 0.6, 4)
    out = body + hiss
    if cold:
        for k in range(3):
            fc = rng.uniform(600, 1100)
            whistle = bp(pink(n), fc * 0.97, fc * 1.03, order=3) * 5.0 * lfo(n, 0.05 + 0.03 * k, 0.9, 0.4, 7 + k) ** 2
            out += whistle
    return norm(out, 0.5)


def bed_room(n):
    return norm(lp(brown(n), 260) + bp(pink(n), 2000, 6000) * 0.02, 0.35)


def bed_fire(n):
    roar = lp(brown(n), 180) * 0.8 * lfo(n, 0.4, 0.3, 1.0, 9)
    out = roar.copy()
    t = 0
    while t < n - SR:
        L = int(rng.uniform(0.004, 0.03) * SR)
        c = bp(rng.normal(0, 1, (L, 2)).astype(np.float32), rng.uniform(900, 2500), rng.uniform(3000, 7000), order=1)
        c *= np.exp(-np.linspace(0, 6, L))[:, None] * rng.uniform(0.3, 1.2)
        out[t:t + L] += c
        t += int(rng.exponential(0.11) * SR) + 1
    return norm(out, 0.5)


def bed_tone(n):
    """Very soft low tone under maps and graphics."""
    return norm(lp(brown(n), 140), 0.3)


BEDS = {}


def bed(kind, n):
    key = kind
    if key not in BEDS:
        m = int(60 * SR)
        BEDS[key] = {'water': bed_water, 'wind': bed_wind, 'cold': lambda m: bed_wind(m, True), 'room': bed_room,
                     'fire': bed_fire, 'tone': bed_tone}[kind](m)
    b = BEDS[key]
    reps = int(math.ceil(n / len(b))) + 1
    off = rng.integers(0, len(b))
    return np.tile(b, (reps, 1))[off:off + n]


ARCH_BEDS = {           # archival stills: the place in the picture, kept low under the narration
    'catlin_canoe_race': [('water', -8), ('wind', -16)],
    'catlin_herds_crossing': [('water', -9), ('wind', -12)],
    'hornaday_shop': [('room', -9)],
    'hornaday_bison_group': [('room', -9)],
    'muybridge_gallop_sheet': [('room', -12)],
    'zoo_cow_and_calf': [('wind', -13)],
    'zoo_bison_2014': [('wind', -12)],
    'upton_red_river_carts': [('wind', -12)],
    'tavernier_slaughtered_for_the_hide': [('wind', -10)],
    'tavernier_curing_hides_and_bones': [('wind', -10)],
    'nyzp_nucleus_of_the_buffalo_herd': [('wind', -14)],
    'hbc_fort_vancouver_mess': [('wind', -13), ('water', -22)],
    'hbc_fort_colville_officers_house': [('wind', -12)],
    'hbc_fort_colville_huts': [('wind', -11)],
}
ARCH_BISON = ('catlin_yellowstone_chase', 'catlin_herds_crossing', 'catlin_bulls_running_season', 'catlin_winter_chase',
              'nyzp_nucleus_of_the_buffalo_herd')


def arch_key(sh):
    return os.path.basename(getattr(sh, 'path', '')).rsplit('.', 1)[0]


def clip_beds(c):
    """[(kind, gain dB)] for a clip, from its shot."""
    sh = c['shot']
    if isinstance(sh, Archive):
        return ARCH_BEDS.get(arch_key(sh), [('wind', -10)])
    if isinstance(sh, (Diptych, Sequence)):
        return [('room', -12), ('wind', -22)]
    if isinstance(sh, DocPage):                 # a printed page: only the quiet of a room
        return [('room', -10), ('cold', -26)]
    if isinstance(sh, Plate):
        n = sh.name
        fam, cam = n.split('_')[0], n.split('_')[1]
        if fam == 'dock':
            return [('water', -6), ('wind', -16)]
        if fam == 'camp':
            out = [('wind', -9)]
            if cam == 'K2':
                out.append(('fire', -5))
            if cam == 'R3b':
                out = [('wind', -11)]
            return out
        if fam == 'fort':
            return [('cold', -7)] if cam in ('F1', 'F2') else [('wind', -10), ('water', -18)]
        if fam == 'plain':
            return [('wind', -7)]
        if fam == 'desk':
            return [('room', -8), ('cold', -24)]
        if fam == 'store':
            return [('room', -8), ('wind', -20)]
    return [('tone', -14)]


# ------------------------------------------------------------------ spot effects
def thud():
    L = int(0.45 * SR)
    t = np.arange(L) / SR
    s = np.sin(2 * math.pi * (95 * np.exp(-t * 6) + 55) * t) * np.exp(-t * 11)
    n = lp(rng.normal(0, 1, (L, 1)).astype(np.float32), 1800)[:, 0] * np.exp(-t * 40) * 0.5
    y = (s + n)[:, None] * np.array([1, 1], np.float32)
    return norm(y, 0.6)


def scratch(dur):
    L = int(dur * SR)
    x = bp(rng.normal(0, 1, (L, 2)).astype(np.float32), 2500, 7000)
    env = np.abs(np.sin(np.linspace(0, math.pi * rng.uniform(3, 7), L))) ** 0.5 * np.sin(np.linspace(0, math.pi, L))
    return norm(x * env[:, None], 0.35)


def whoosh(dur=0.9, up=True):
    L = int(dur * SR)
    x = pink(L)
    out = np.zeros_like(x)
    steps = 24
    for k in range(steps):
        a, b = k * L // steps, (k + 1) * L // steps
        f = 300 * (12 ** (k / steps if up else 1 - k / steps))
        out[a:b] = bp(x, f * 0.7, min(f * 1.6, 20000))[a:b]
    env = np.sin(np.linspace(0, math.pi, L)) ** 2
    return norm(out * env[:, None], 0.4)


def tick():
    L = int(0.03 * SR)
    t = np.arange(L) / SR
    y = np.sin(2 * math.pi * 2400 * t) * np.exp(-t * 300)
    return norm(np.c_[y, y].astype(np.float32), 0.25)


def squeal(dur):
    """Ungreased wooden axle: irregular stick-slip squeal (Red River carts were famous for it)."""
    L = int(dur * SR)
    t = np.arange(L) / SR
    f = 700 + 260 * np.sin(2 * math.pi * 0.7 * t + rng.uniform(0, 6)) + 120 * np.sin(2 * math.pi * 3.1 * t)
    ph = np.cumsum(2 * math.pi * f / SR)
    y = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.2 * np.sin(3.01 * ph))
    am = np.clip(np.sin(2 * math.pi * 0.9 * t + rng.uniform(0, 6)) * 1.5 + rng.normal(0, 0.15, L), 0, 1)
    am = signal.lfilter([0.002], [1, -0.998], am)
    y = y * am / (am.max() + 1e-9)
    y = bp(np.c_[y, y * 0.9].astype(np.float32), 400, 4000)
    return norm(y, 0.3)


def _distance(y, wet=0.85, tail=2.6, lp_hz=3500):
    n = int(tail * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)).astype(np.float32) * np.exp(-t * 6.9 / tail)[:, None]
    ir = lp(ir, 2500)
    ir /= np.sqrt((ir ** 2).sum(0))
    out = np.zeros((len(y) + n - 1, 2), np.float32)
    for c in range(2):
        out[:, c] = signal.fftconvolve(y[:, c], ir[:, c])
    out[:len(y)] = out[:len(y)] * wet + y * (1 - wet)
    return lp(out, lp_hz)


def loon(dur=3.2):
    """Common loon 'wail': a slow rising-falling glide with vibrato, heard across water."""
    L = int(dur * SR)
    t = np.arange(L) / SR
    u = t / dur
    f = 620 + 300 * np.sin(np.pi * np.clip(u * 1.25, 0, 1)) ** 0.7 - 120 * np.clip((u - 0.75) / 0.25, 0, 1)
    f = f + 9 * np.sin(2 * np.pi * 5.2 * t) * np.clip(u * 3, 0, 1)
    ph = np.cumsum(2 * np.pi * f / SR)
    y = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    env = np.clip(u / 0.12, 0, 1) ** 1.5 * np.clip((1 - u) / 0.2, 0, 1)
    y = (y * env)[:, None] * np.array([1.0, 0.9], np.float32)
    return norm(_distance(y.astype(np.float32), 0.8, 3.0, 3000), 0.35)


def bison_grunt(dur=0.9):
    L = int(dur * SR)
    t = np.arange(L) / SR
    f0 = 78 + 10 * np.sin(2 * np.pi * 1.3 * t) + rng.normal(0, 2, L).cumsum() * 0.002
    ph = np.cumsum(2 * np.pi * f0 / SR)
    buzz = signal.sawtooth(ph) * (0.6 + 0.4 * np.sin(2 * np.pi * 24 * t))
    y = buzz[:, None].astype(np.float32) * np.array([1, 1], np.float32)
    y = bp(y, 120, 900) + bp(rng.normal(0, 1, (L, 2)).astype(np.float32), 200, 1200) * 0.15
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.8
    return norm(_distance(y * env[:, None], 0.6, 1.5, 1800), 0.4)


def place(buf, y, t, gain_db=0.0, pan=0.0):
    i = int(t * SR)
    if i < 0 or i >= len(buf):
        return
    j = min(len(buf), i + len(y))
    g = 10 ** (gain_db / 20)
    pg = np.array([1 - max(0, pan), 1 + min(0, pan)], np.float32)
    buf[i:j] += y[: j - i] * g * pg


def main():
    out_amb, out_fx = sys.argv[1], sys.argv[2]
    clips = edl.resolved()
    total = core.timing()['total']
    N = int(total * SR)
    amb = np.zeros((N, 2), np.float32)
    fx = np.zeros((N, 2), np.float32)
    XF = 0.8
    for c in clips:
        t0 = max(0.0, c['start'] - XF / 2)
        t1 = min(total, c['end'] + XF / 2)
        n = int((t1 - t0) * SR)
        env = np.ones(n, np.float32)
        k = int(XF * SR)
        env[:k] = np.linspace(0, 1, k) if c['start'] > 0.5 else 1
        env[-k:] *= np.linspace(1, 0, k)
        for kind, gdb in clip_beds(c):
            y = bed(kind, n) * (10 ** (gdb / 20))
            i = int(t0 * SR)
            amb[i:i + n] += y[: len(amb) - i] * env[: len(amb) - i, None]
        sh = c['shot']
        d = c['end'] - c['start']
        if isinstance(sh, Plate):
            if sh.name == 'camp_K1':
                t = c['start'] + 0.6
                while t < c['end'] - 0.3:
                    place(fx, thud(), t, -10 + rng.uniform(-2, 1), rng.uniform(-0.2, 0.2))
                    t += rng.uniform(1.0, 1.5)
            if sh.name == 'desk_W2':
                t = c['start'] + 0.4
                while t < c['end'] - 0.6:
                    dd = rng.uniform(0.25, 0.8)
                    place(fx, scratch(dd), t, -16, 0.1)
                    t += dd + rng.uniform(0.15, 0.6)
            if sh.name == 'plain_B3':
                t = c['start'] + rng.uniform(0.2, 1.0)
                while t < c['end'] - 1.0:
                    dd = rng.uniform(1.0, 2.6)
                    place(fx, squeal(dd), t, -24 + rng.uniform(-4, 0), rng.uniform(-0.5, 0.5))
                    t += rng.uniform(0.4, 1.4)
        elif isinstance(sh, Archive) and arch_key(sh) == 'upton_red_river_carts':
            t = c['start'] + rng.uniform(0.6, 1.4)             # a dry axle, far off, as in the cart-line shot
            while t < c['end'] - 1.0:
                place(fx, squeal(rng.uniform(1.0, 2.2)), t, -26 + rng.uniform(-3, 0), rng.uniform(-0.4, 0.4))
                t += rng.uniform(1.6, 3.0)
        elif isinstance(sh, Sequence):
            # muffled hoofbeats in the rhythm of the looping gallop (one stride per loop of frames)
            stride = len(sh.frames) / sh.fps
            t = c['start'] + 0.2
            while t < c['end'] - 0.4:
                for off in (0.0, 0.11, 0.29, 0.4):
                    if t + off < c['end'] - 0.3:
                        place(fx, thud(), t + off, -27 + rng.uniform(-2, 1), rng.uniform(-0.15, 0.15))
                t += stride
        elif not isinstance(sh, (Archive, Diptych, DocPage)):
            if c['start'] > 1:
                place(fx, whoosh(0.9, True), c['start'] - 0.45, -24)
    # natural cues: loons over the misty river (cold open, ending), bison grunts under herd shots
    for t0 in (3.0, core.anchor('P02.0') + 1.5, core.anchor('P42.4') + 1.0, core.anchor('CREDITS') + 2.0):
        place(fx, loon(rng.uniform(2.6, 3.4)), t0, -22, rng.uniform(-0.6, 0.6))
    for c in clips:
        sh = c['shot']
        if (isinstance(sh, Plate) and sh.name == 'plain_B1') or (isinstance(sh, Archive) and arch_key(sh) in ARCH_BISON):
            t = c['start'] + rng.uniform(0.8, 2.0)
            while t < c['end'] - 1.0:
                place(fx, bison_grunt(rng.uniform(0.6, 1.1)), t, -24 + rng.uniform(-5, 0), rng.uniform(-0.5, 0.5))
                t += rng.uniform(2.5, 5.0)
    # counters / grids
    for t0, t1 in ((core.anchor('P24.2'), core.anchor('P24.2') + 4.2),):
        t = t0
        while t < t1:
            place(fx, tick(), t, -30, rng.uniform(-0.3, 0.3))
            t += 0.09
    amb = lp(amb, 12000)
    sf.write(out_amb, amb, SR, subtype='PCM_24')
    sf.write(out_fx, fx, SR, subtype='PCM_24')
    print('ambience + fx written')


if __name__ == '__main__':
    main()
