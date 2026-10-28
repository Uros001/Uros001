"""Original score for THE PEMMICAN WAR, rendered from VSCO 2 Community Edition samples (CC0, Versilian Studios).

A small offline sampler: per-sample pitch is measured (the library's note names use mixed octave
conventions), notes are pitch-shifted by resampling, long notes are extended by crossfaded loops of the
sustain region, and the mix goes through a synthetic stereo hall reverb. Cues follow the narration
timing (audio/narration/timing.json).

  python3 score.py <vsco_dir> <out_wav>
"""
import os, sys, json, math, random, functools, glob, re
from fractions import Fraction
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIM = json.load(open(os.path.join(ROOT, 'audio/narration/timing.json')))
VSCO = sys.argv[1] if len(sys.argv) > 1 else ''
NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def A(a):
    """Narration anchor -> seconds (subset of film.core.anchor)."""
    if isinstance(a, (int, float)):
        return float(a)
    off = 0.0
    m = re.match(r'^(.*?)([+-][0-9.]+)?$', a)
    key, o = m.group(1), m.group(2)
    if o:
        off = float(o)
    end = key.endswith('e') and (key.endswith('.e') or key[-2].isdigit())
    k = key[:-1].rstrip('.') if end else key
    if k.startswith('P') and '.' in k:
        pid, idx = k.split('.')
        s = next(x for x in TIM['sentences'] if x['pid'] == pid and x['idx'] == int(idx))
        return (s['end'] if end else s['start']) + off
    if k.startswith('P'):
        p = next(x for x in TIM['paragraphs'] if x['pid'] == k)
        return (p['end'] if end else p['start']) + off
    if k == 'CREDITS':
        return (TIM['credits']['end'] if end else TIM['credits']['start']) + off
    i = next(x for x in TIM['inserts'] if x['kind'] == k)
    return (i['end'] if end else i['start']) + off


def midi(name):
    m = re.match(r'([A-G]#?)(-?\d)', name)
    return 12 * (int(m.group(2)) + 1) + NOTE[m.group(1)]


@functools.lru_cache(maxsize=None)
def load(path):
    y, sr = sf.read(path, dtype='float32', always_2d=True)
    if y.shape[1] == 1:
        y = np.repeat(y, 2, 1)
    y = y[:, :2]
    if sr != SR:
        g = math.gcd(SR, sr)
        y = signal.resample_poly(y, SR // g, sr // g, axis=0).astype(np.float32)
    # trim leading silence
    env = np.abs(y).max(1)
    th = env.max() * 0.02
    i0 = max(0, int(np.argmax(env > th)) - int(0.005 * SR))
    return y[i0:]


def measure_pitch(path):
    y = load(path).mean(1)
    a = y[int(SR * 0.25):int(SR * 1.25)] if len(y) > SR * 1.4 else y[: len(y) // 2]
    a = a * np.hanning(len(a))
    c = np.fft.irfft(np.abs(np.fft.rfft(a, 2 * len(a))) ** 2)[: len(a)]
    lo, hi = int(SR / 2200), int(SR / 26)
    lag = lo + int(np.argmax(c[lo:hi]))
    f = SR / lag
    return 69 + 12 * math.log2(f / 440)


class Inst:
    def __init__(self, name, pattern, gain=1.0, attack=0.25, release=1.2, loop=True, name_re=None, keymap=None, fixed=False):
        self.name, self.gain, self.attack, self.release, self.loop, self.fixed = name, gain, attack, release, loop, fixed
        files = sorted(glob.glob(os.path.join(VSCO, pattern)))
        self.map = {}
        cache = os.path.join(ROOT, 'audio/music/pitchmap.json')
        pm = json.load(open(cache)) if os.path.exists(cache) else {}
        for f in files:
            key = os.path.relpath(f, VSCO)
            if keymap is not None:
                mm = re.search(r'_(\d{3})\.wav$', f)
                if not mm:
                    continue
                m = keymap[int(mm.group(1))]
            else:
                if key not in pm:
                    est = measure_pitch(f)
                    nm = re.search(name_re or r'_([A-G]#?\d)_', os.path.basename(f))
                    if nm:
                        base = midi(nm.group(1))
                        m = min((base, base + 12, base - 12), key=lambda c: abs(c - est))
                    else:
                        m = int(round(est))
                    pm[key] = m
                m = pm[key]
            dyn = 3 if re.search(r'_v3|_f\.|_ff|dyn3|_mf', f) else 1
            self.map.setdefault(m, []).append((dyn, f))
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump(pm, open(cache, 'w'), indent=0)
        self.keys = sorted(self.map)
        assert self.keys, f'no samples for {name}: {pattern}'

    def pick(self, m, vel, rnd):
        if self.fixed:
            allf = [(d, f) for v in self.map.values() for d, f in v]
            want = 3 if vel > 0.6 else 1
            cand = [f for d, f in allf if d == want] or [f for d, f in allf]
            return m, rnd.choice(cand)
        k = min(self.keys, key=lambda x: (abs(x - m), x < m))
        opts = self.map[k]
        want = 3 if vel > 0.6 else 1
        best = [f for d, f in opts if d == want] or [f for d, f in opts]
        return k, rnd.choice(best)


@functools.lru_cache(maxsize=512)
def shifted(path, semis):
    y = load(path)
    if abs(semis) < 1e-3:
        return y
    r = Fraction(2 ** (-semis / 12)).limit_denominator(200)
    return signal.resample_poly(y, r.numerator, r.denominator, axis=0).astype(np.float32)


def render_note(inst, m, dur, vel, rnd, attack=None, release=None):
    k, f = inst.pick(m, vel, rnd)
    y = shifted(f, m - k)
    att = inst.attack if attack is None else attack
    rel = inst.release if release is None else release
    n = int((dur + rel) * SR)
    if len(y) >= n or not inst.loop:
        out = y[: min(len(y), n)].copy()
    else:
        s0, s1 = int(0.6 * SR), max(int(0.6 * SR) + SR, len(y) - int(0.6 * SR))
        xf = int(0.35 * SR)
        out = np.zeros((n, 2), np.float32)
        out[: min(len(y), n)] = y[:n]
        pos = min(len(y), n) - xf
        while pos < n:
            st = rnd.randint(s0, max(s0 + 1, s1 - SR))
            seglen = min(s1 - st, n - pos + xf)
            seg_ = y[st: st + seglen].copy()
            L = len(seg_)
            if L <= xf:
                break
            w = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
            out[pos: pos + xf] = out[pos: pos + xf] * (1 - w) + seg_[:xf] * w if pos + xf <= n else out[pos: pos + xf]
            end = min(n, pos + L)
            out[pos + xf: end] = seg_[xf: end - pos]
            if end >= n:
                break
            pos = end - xf
    L = len(out)
    env = np.ones(L, np.float32)
    a = min(L, int(att * SR))
    if a > 0:
        env[:a] = np.linspace(0, 1, a) ** 1.5
    r0 = min(L, int(dur * SR))
    rl = L - r0
    if rl > 0:
        env[r0:] *= np.linspace(1, 0, rl) ** 2
    return out * env[:, None] * vel * inst.gain


class Score:
    def __init__(self, total):
        self.buf = np.zeros((int((total + 8) * SR), 2), np.float32)
        self.rnd = random.Random(7)

    def note(self, inst, t, m, dur, vel=0.5, pan=0.0, **kw):
        if isinstance(m, str):
            m = midi(m)
        y = render_note(inst, m, dur, vel, self.rnd, **kw)
        lg = math.cos((pan + 1) * math.pi / 4) * 1.414
        rg = math.sin((pan + 1) * math.pi / 4) * 1.414
        i = int(t * SR)
        j = min(len(self.buf), i + len(y))
        if j > i:
            self.buf[i:j, 0] += y[: j - i, 0] * lg
            self.buf[i:j, 1] += y[: j - i, 1] * rg

    def chord(self, inst, t, notes, dur, vel=0.4, spread=0.5, **kw):
        for k, m in enumerate(notes):
            pan = (k / max(1, len(notes) - 1) - 0.5) * spread
            self.note(inst, t + self.rnd.uniform(0, 0.05), m, dur, vel * self.rnd.uniform(0.9, 1.05), pan, **kw)

    def gain_ramp(self, t0, t1, g0, g1):
        i0, i1 = int(t0 * SR), int(t1 * SR)
        self.buf[i0:i1] *= np.linspace(g0, g1, i1 - i0, dtype=np.float32)[:, None]

    def mute(self, t0, t1, fade=0.25):
        i0, i1, f = int(t0 * SR), int(t1 * SR), int(fade * SR)
        self.buf[i0:i1] *= 0.0
        self.buf[max(0, i0 - f):i0] *= np.linspace(1, 0, min(f, i0), dtype=np.float32)[:, None]


def hall_ir(seconds=3.6, predelay=0.025, seed=1):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 6.9 / seconds)
    ir = rng.normal(0, 1, (n, 2)).astype(np.float32) * env[:, None]
    # darker tail: progressive lowpass by mixing with a smoothed copy
    b, a = signal.butter(2, 3500 / (SR / 2), 'low')
    lp = signal.lfilter(b, a, ir, axis=0)
    mix = np.clip(t / seconds * 2, 0, 1)[:, None]
    ir = ir * (1 - mix) + lp * mix
    ir = np.vstack([np.zeros((int(predelay * SR), 2), np.float32), ir])
    return (ir / np.sqrt((ir ** 2).sum(0))).astype(np.float32)


def reverb(x, wet=0.32):
    ir = hall_ir()
    out = np.zeros_like(x)
    for c in range(2):
        out[:, c] = signal.fftconvolve(x[:, c], ir[:, c])[: len(x)]
    return x * (1 - wet) + out * wet * 1.2


# ------------------------------------------------------------------ the cues
def compose(S, I):
    cel, vla, vln, cb = I['cello'], I['viola'], I['violins'], I['bass']
    harp, pno, solo, trem, ctrem, pizz = I['harp'], I['piano'], I['solo'], I['vtrem'], I['ctrem'], I['pizz']
    timp, troll, bd = I['timp'], I['troll'], I['bdrum']

    Dm = ['D3', 'F3', 'A3']
    # ---- cold open
    S.note(cb, 0.0, 'D2', 33.0, 0.35, attack=4.0, release=3.0)
    S.note(cel, 1.0, 'D3', 32.0, 0.28, -0.2, attack=5.0, release=3.0)
    S.note(cel, 9.0, 'A3', 24.0, 0.18, 0.2, attack=6.0, release=3.0)
    for t, n in ((3.5, 'D5'), (8.4, 'A4'), (13.0, 'F4'), (17.8, 'E4'), (22.5, 'D4'), (27.0, 'A4')):
        S.note(harp, t, n, 4.0, 0.35, 0.3)
    S.note(vln, 20.8, 'A4', 11.5, 0.16, 0.3, attack=4.0, release=2.0)
    S.note(timp, A('P03.1') - 0.05, 'D2', 4.0, 0.55)
    S.note(ctrem, A('P04.0') - 1.0, 'D2', 13.0, 0.3, attack=3.0, release=2.0)
    S.note(trem, A('P04.0') - 0.5, 'E5', 12.0, 0.13, 0.4, attack=4.0, release=2.0)
    S.note(trem, A('P04.0') + 2.0, 'F5', 9.5, 0.1, -0.4, attack=4.0, release=2.0)
    S.chord(vla, A('P05.0') - 1.0, ['D3', 'A3', 'F4'], 11.0, 0.22, attack=3.0)
    S.chord(cel, A('P05.0') - 1.0, ['D2', 'A2'], 11.0, 0.2, attack=3.0)
    for k, n in enumerate(['D4', 'F4', 'A4', 'D5', 'A4', 'F4', 'E4', 'C4']):
        S.note(harp, A('P05.0') + 0.5 + k * 1.3, n, 3.0, 0.28, 0.25)
    t0 = A('TITLE') - 1.8
    S.note(troll, t0, 'D2', 3.0, 0.35, attack=1.6, release=1.5)
    S.chord(cel, A('TITLE'), ['A#1', 'F2', 'A#2', 'D3'], 7.0, 0.36, attack=1.2, release=3.0)
    S.chord(vln, A('TITLE'), ['F4', 'A#4', 'D5'], 7.0, 0.22, attack=1.4, release=3.0)
    S.chord(vla, A('TITLE'), ['D4', 'F4'], 7.0, 0.22, attack=1.4, release=3.0)
    S.note(timp, A('TITLE') + 0.05, 'A#1', 4.0, 0.5)

    # ---- I. Meat That Keeps: pastoral, D dorian / F major
    prog = [(['D3', 'A3', 'F4'], 'D2'), (['A#2', 'F3', 'D4'], 'A#1'), (['F3', 'C4', 'A4'], 'F2'), (['C3', 'G3', 'E4'], 'C2'),
            (['D3', 'A3', 'F4'], 'D2'), (['G2', 'D3', 'A#3'], 'G1'), (['A#2', 'F3', 'D4'], 'A#1'), (['A2', 'E3', 'C#4'], 'A1')]
    t, end, i = A('TITLE.e') + 1.0, A('CH2') - 0.5, 0
    while t < end:
        ch, root = prog[i % len(prog)]
        d = min(8.0, end - t)
        S.chord(vla, t, ch, d + 0.4, 0.15, attack=2.0, release=2.0)
        S.note(cel, t, root.replace('1', '2') if root.endswith('1') else root, d + 0.4, 0.15, -0.3, attack=2.0, release=2.0)
        arp = ch + [ch[1].replace('3', '4').replace('4', '5', 1) if '3' in ch[1] else ch[1]]
        for k in range(4):
            S.note(harp, t + 0.3 + k * 2.0, arp[k % len(arp)].replace('2', '4').replace('3', '4') if k % 2 else arp[(k + 1) % len(arp)].replace('2', '3'),
                   2.5, 0.2, 0.3 * (1 if k % 2 else -1))
        t += 8.0
        i += 1
    motif = [('D5', 0.0), ('F5', 1.1), ('E5', 2.2), ('C5', 3.3), ('D5', 5.0)]
    for start in (A('P06.3') - 0.5, A('P09.0') - 1.0, A('P12.2') - 1.0):
        for n, dt in motif:
            S.note(pno, start + dt, n, 2.0, 0.22, 0.15)
    S.note(troll, A('CH2') - 1.6, 'D2', 2.6, 0.25, attack=1.4)
    S.chord(cel, A('CH2'), ['D2', 'A2'], 4.0, 0.3, attack=0.8, release=2.5)
    S.chord(vln, A('CH2'), ['A4', 'D5'], 4.0, 0.15, attack=1.0, release=2.5)
    S.note(timp, A('CH2') + 0.05, 'D2', 3.0, 0.4)

    # ---- II. The Canoe Road: pizzicato paddling ostinato (76 bpm)
    beat = 60 / 76
    t, end = A('CH2.e') + 0.2, A('CH3') - 1.0
    bars = [('D2', 'A2', ['D3', 'A3', 'F4']), ('C2', 'G2', ['C3', 'G3', 'E4']), ('A#1', 'F2', ['A#2', 'F3', 'D4']), ('C2', 'G2', ['C3', 'G3', 'E4'])]
    b = 0
    while t < end - 4 * beat:
        r, f, ch = bars[(b // 2) % 4]
        for k, n in enumerate([r, f, r.replace('1', '2').replace('2', '3', 1) if r.endswith(('1', '2')) else r, f]):
            S.note(pizz, t + k * beat, n, 0.9, 0.34 if k == 0 else 0.24, -0.2)
        if b % 2 == 0:
            S.chord(vln, t, [c.replace('3', '4').replace('4', '5', 0) for c in ch], 8 * beat + 0.3, 0.11, attack=1.8, release=1.8)
            S.note(cb, t, r, 8 * beat, 0.18, attack=0.8)
        t += 4 * beat
        b += 1
    for start in (A('P15.0') - 0.5, A('P17.2') - 0.5):
        for n, dt, d in [('A4', 0, 1.6), ('D5', 1.6, 1.6), ('E5', 3.2, 0.8), ('F5', 4.0, 0.8), ('E5', 4.8, 1.6), ('D5', 6.4, 3.0)]:
            S.note(solo, start + dt, n, d, 0.24, 0.25, attack=0.12, release=0.8)
    S.note(troll, A('CH3') - 1.8, 'D2', 3.0, 0.3, attack=1.5)
    S.chord(cel, A('CH3'), ['D2', 'A2'], 4.0, 0.34, attack=0.6, release=2.5)
    S.note(timp, A('CH3') + 0.05, 'D2', 3.0, 0.45)

    # ---- III. The Order: low, tense
    t, end = A('CH3.e') + 0.5, A('CH4') - 1.0
    tprog = [(['D2', 'A2'], ['D4', 'F4']), (['D2', 'A2'], ['D#4', 'G4']), (['C2', 'G2'], ['C4', 'D#4']), (['D2', 'A2'], ['D4', 'F4']),
             (['A#1', 'F2'], ['D4', 'F4']), (['A1', 'E2'], ['C#4', 'E4'])]
    i = 0
    while t < end:
        lo, hi = tprog[i % len(tprog)]
        d = min(10.0, end - t)
        S.chord(cel, t, lo, d + 0.5, 0.2, attack=3.0, release=2.5)
        S.chord(vla, t, hi, d + 0.5, 0.11, attack=3.5, release=2.5)
        t += 10.0
        i += 1
    S.note(trem, A('P22.1') - 1.0, 'A4', 20.0, 0.08, 0.4, attack=5.0, release=3.0)
    S.note(trem, A('P22.1') + 3.0, 'D5', 16.0, 0.06, -0.4, attack=5.0, release=3.0)
    S.note(troll, A('P24.1'), 'D2', 14.0, 0.18, attack=6.0, release=3.0)
    S.note(timp, A('P24.2') - 0.1, 'D2', 3.0, 0.35)
    S.note(troll, A('CH4') - 1.8, 'A1', 3.0, 0.32, attack=1.5)
    S.chord(cel, A('CH4'), ['A1', 'E2', 'A2'], 4.0, 0.34, attack=0.6, release=2.5)
    S.note(timp, A('CH4') + 0.05, 'A1', 3.0, 0.45)

    # ---- IV. Frog Plain: heartbeat, build, silence, lament
    t, end = A('CH4.e') + 1.0, A('P28.0') - 0.5
    while t < end:
        S.note(bd, t, 'C2', 0.8, 0.18)
        S.note(bd, t + 0.33, 'C2', 0.8, 0.10)
        t += 1.6
    S.note(cb, A('CH4.e'), 'D2', A('P28.0') - A('CH4.e'), 0.2, attack=5.0, release=3.0)
    S.note(cel, A('P25.3') - 1.0, 'A2', 18.0, 0.14, attack=4.0, release=3.0)
    t, end = A('P28.0') - 0.5, A('P30.2') + 0.2
    k = 0
    while t < end:
        g = 0.14 + 0.22 * (t - A('P28.0')) / (end - A('P28.0'))
        S.note(bd, t, 'C2', 0.8, g)
        S.note(bd, t + 0.3, 'C2', 0.8, g * 0.6)
        t += 1.25
        k += 1
    S.note(ctrem, A('P28.0'), 'D2', A('P30.2') - A('P28.0') + 0.4, 0.22, attack=8.0, release=0.3)
    S.note(trem, A('P29.0') - 2.0, 'D5', A('P30.2') - A('P29.0') + 2.4, 0.1, 0.4, attack=6.0, release=0.3)
    S.note(trem, A('P29.0'), 'D#5', A('P30.2') - A('P29.0') + 0.4, 0.08, -0.4, attack=6.0, release=0.3)
    S.note(troll, A('P30.0') - 1.0, 'D2', A('P30.2') - A('P30.0') + 1.2, 0.3, attack=4.0, release=0.2)
    S.mute(A('P30.2') + 0.15, A('P30.4') - 0.2, fade=0.12)
    S.note(timp, A('P30.2') + 0.18, 'D2', 4.0, 0.5)
    S.note(cb, A('P30.4') - 0.2, 'D2', 14.0, 0.26, attack=2.5, release=3.0)
    S.note(cel, A('P30.5'), 'A2', 10.0, 0.14, attack=3.0, release=3.0)
    lament = [('A3', 0, 2.4), ('D4', 2.4, 1.6), ('C4', 4.0, 1.2), ('A#3', 5.2, 1.2), ('A3', 6.4, 3.2), ('G3', 9.6, 1.6),
              ('F3', 11.2, 1.6), ('E3', 12.8, 1.6), ('D3', 14.4, 4.0)]
    st = A('P32.0') - 0.8
    for n, dt, d in lament:
        S.note(solo, st + dt, n, d, 0.26, -0.15, attack=0.25, release=1.2)
    S.chord(vla, st, ['D3', 'F3'], 19.0, 0.1, attack=4.0, release=3.0)
    S.note(cel, st, 'D2', 19.0, 0.14, attack=4.0, release=3.0)
    t, end = A('P32.3') - 1.0, A('CH5') - 1.0
    cyc = (['A#2', 'F3', 'D4'], ['F2', 'C3', 'A3'], ['G2', 'D3', 'A#3'], ['A2', 'E3', 'C#4'])
    i = 0
    while t < end - 1.0:
        d = min(7.0, end - t)
        S.chord(vla, t, cyc[i % 4], d + 0.4, 0.13, attack=2.5, release=2.0)
        S.note(cel, t, cyc[i % 4][0].replace('3', '2'), d + 0.4, 0.1, attack=2.5, release=2.0)
        t += 7.0
        i += 1
    S.note(troll, A('CH5') - 1.8, 'D2', 3.0, 0.3, attack=1.5)
    S.chord(cel, A('CH5'), ['D2', 'A2', 'F3'], 4.0, 0.32, attack=0.6, release=2.5)
    S.note(timp, A('CH5') + 0.05, 'D2', 3.0, 0.42)

    # ---- V. The Last Hunts: elegy, then a warmer ending
    t, end = A('CH5.e') + 0.5, A('P37.3') - 0.5
    eprog = [['D3', 'A3', 'F4'], ['A#2', 'F3', 'D4'], ['G2', 'D3', 'A#3'], ['A2', 'E3', 'C#4']]
    i = 0
    while t < end:
        d = min(8.0, end - t)
        S.chord(vla, t, eprog[i % 4], d + 0.4, 0.14, attack=2.5, release=2.0)
        S.note(cel, t, eprog[i % 4][0].replace('3', '2').replace('2', '2'), d + 0.4, 0.14, attack=2.5, release=2.0)
        t += 8.0
        i += 1
    for start in (A('P35.0') - 0.3, A('P36.2') - 0.5):
        for n, dt in motif:
            S.note(pno, start + dt, n, 2.2, 0.22, 0.15)
    S.note(vln, A('P37.3') - 0.5, 'A5', A('P38.2') - A('P37.3') + 1.0, 0.07, 0.2, attack=6.0, release=4.0)
    S.note(cb, A('P37.3') - 0.5, 'D2', A('P40.0') - A('P37.3'), 0.2, attack=5.0, release=4.0)
    S.note(pno, A('P39.1') + 0.2, 'D4', 4.0, 0.2, 0.0)
    S.note(pno, A('P39.1') + 0.2, 'A3', 4.0, 0.14, 0.0)
    t, end = A('P41.0') - 1.0, A('CREDITS') + 0.5
    hope = [['F3', 'C4', 'A4'], ['C3', 'G3', 'E4'], ['D3', 'A3', 'F4'], ['A#2', 'F3', 'D4'], ['F3', 'C4', 'A4'], ['C3', 'G3', 'E4'],
            ['A#2', 'F3', 'D4'], ['D3', 'A3', 'F#4']]
    i = 0
    while t < end:
        d = min(7.0, end - t)
        g = 0.13 if t < A('P42.0') else 0.19
        S.chord(vla, t, hope[i % len(hope)], d + 0.4, g, attack=2.0, release=2.0)
        S.chord(vln, t, [n.replace('4', '5') for n in hope[i % len(hope)][1:]], d + 0.4, g * 0.6, attack=2.5, release=2.0)
        S.note(cel, t, hope[i % len(hope)][0].replace('3', '2'), d + 0.4, g, attack=2.0, release=2.0)
        for k in range(3):
            S.note(harp, t + 0.4 + k * 2.2, hope[i % len(hope)][k].replace('2', '4').replace('3', '4'), 2.5, 0.16, 0.3)
        t += 7.0
        i += 1
    for n, dt in [('D5', 0.0), ('F5', 1.2), ('E5', 2.4), ('C5', 3.6), ('D5', 5.4), ('A4', 7.6), ('D5', 9.4)]:
        S.note(pno, A('CREDITS') + 0.6 + dt, n, 2.6, 0.24, 0.1)
    S.chord(cel, A('CREDITS') + 0.4, ['D2', 'A2'], 12.0, 0.18, attack=2.0, release=3.0)
    S.chord(vla, A('CREDITS') + 0.4, ['D3', 'F#3', 'A3'], 12.0, 0.14, attack=2.5, release=3.0)


def main():
    out = sys.argv[2]
    I = dict(
        cello=Inst('cello', 'Strings/Cello Section/susvib/*.wav', 1.0, 0.5, 1.5),
        viola=Inst('viola', 'Strings/Viola Section/susvib/*.wav', 1.0, 0.5, 1.5),
        violins=Inst('violins', 'Strings/Violin Section/susVib/*.wav', 0.9, 0.5, 1.5),
        bass=Inst('bass', 'Strings/Solo Contrabass/SusNV/*.wav', 1.0, 0.5, 1.5, name_re=r'_SusNV_([A-G]#?\d)_'),
        vtrem=Inst('vtrem', 'Strings/Violin Section/Trem/*.wav', 0.9, 0.5, 1.2),
        ctrem=Inst('ctrem', 'Strings/Cello Section/trem/*.wav', 1.0, 0.5, 1.2),
        pizz=Inst('pizz', 'Strings/Cello Section/pizzT/*.wav', 1.0, 0.005, 0.4, loop=False),
        harp=Inst('harp', 'Strings/Harp/*.wav', 0.9, 0.003, 1.5, loop=False),
        solo=Inst('solo', 'Strings/Solo Violin/Arco Vib/*.wav', 0.9, 0.15, 0.9, name_re=r'_([A-G]#?\d)_'),
        piano=Inst('piano', 'Keys/Upright Piano/Player_dyn1_rr1_*.wav', 0.9, 0.003, 1.2, loop=False,
                   keymap={i: 21 + 2 * i if i < 44 else 108 for i in range(45)}),
        timp=Inst('timp', 'Percussion/Timpani/Timpani1_Hit_*.wav', 1.0, 0.002, 1.5, loop=False, name_re=r'XX', fixed=True),
        troll=Inst('troll', 'Percussion/Timpani/Rolls/*.wav', 1.0, 0.3, 1.0, name_re=r'XX', fixed=True),
        bdrum=Inst('bdrum', 'VSCO 1 Percussion/drums/bass/bdrum2_p*.wav', 1.0, 0.002, 0.5, loop=False, name_re=r'XX', fixed=True),
    )
    for k, v in I.items():
        print(k, 'keys', v.keys[:3], '...', v.keys[-3:], 'n', sum(len(x) for x in v.map.values()), flush=True)
    S = Score(TIM['total'])
    compose(S, I)
    x = reverb(S.buf)
    x = x[: int(TIM['total'] * SR)]
    pk = np.abs(x).max()
    x = x / max(pk, 1e-6) * 0.7
    sf.write(out, x, SR, subtype='PCM_24')
    print('score written', out, 'peak', pk)


if __name__ == '__main__':
    main()
