"""Mix narration, score, ambience and effects; duck music/ambience under speech; master to -14 LUFS, TP <= -1 dBTP.

  python3 mix.py <out_master.wav>
"""
import os, sys
import numpy as np
import soundfile as sf
from scipy import signal
import pyloudnorm as pyln

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loudness

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000


def read(p):
    y, sr = sf.read(os.path.join(ROOT, p), dtype='float32', always_2d=True)
    assert sr == SR, (p, sr)
    if y.shape[1] == 1:
        y = np.repeat(y, 2, 1)
    return y


def fit(y, n):
    if len(y) >= n:
        return y[:n]
    return np.vstack([y, np.zeros((n - len(y), 2), np.float32)])


def to_lufs(y, target):
    m = pyln.Meter(SR)
    cur = m.integrated_loudness(y)
    return y * 10 ** ((target - cur) / 20), cur


def speech_env(nar, att=0.06, rel=0.7):
    """0..1 envelope that is 1 while the narrator speaks, with smooth attack/release."""
    x = np.abs(nar).max(1)
    win = int(0.03 * SR)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, mode='same'))
    gate = (rms > 10 ** (-42 / 20)).astype(np.float32)
    # hold gaps shorter than 0.35 s
    hold = int(0.35 * SR)
    g = np.convolve(gate, np.ones(hold), mode='same') > 0
    g = g.astype(np.float32)
    a = np.exp(-1 / (att * SR))
    r = np.exp(-1 / (rel * SR))
    out = np.empty_like(g)
    v = 0.0
    # one-pole attack/release follower (vectorised in blocks for speed)
    blk = 480
    for i in range(0, len(g), blk):
        target = g[i:i + blk].max()
        coef = a if target > v else r
        v = target + (v - target) * coef ** blk
        out[i:i + blk] = v
    return np.convolve(out, np.ones(blk) / blk, mode='same')


def main():
    out = sys.argv[1]
    nar = read('audio/narration/narration_master.wav')
    n = len(nar)
    mus = fit(read('audio/music/score_raw.wav'), n)
    amb = fit(read('audio/sfx/ambience.wav'), n)
    fx = fit(read('audio/sfx/fx.wav'), n)
    mus, m0 = to_lufs(mus, -25.0)
    amb, a0 = to_lufs(amb, -33.0)
    fx = fx * 10 ** (-4 / 20)
    env = speech_env(nar)[:, None]
    duck_m = 10 ** (-7.5 * env / 20)
    duck_a = 10 ** (-4.0 * env / 20)
    mix = nar * 1.0 + mus * duck_m + amb * duck_a + fx * duck_a
    # gentle bus glue: high-pass rumble, slight low shelf trim
    sos = signal.butter(2, 28 / (SR / 2), 'high', output='sos')
    mix = signal.sosfilt(sos, mix, axis=0).astype(np.float32)
    tmp = out + '.premaster.wav'
    sf.write(tmp, mix, SR, subtype='FLOAT')
    pre, post, tp = loudness.normalize(tmp, out, -14.0, tp_limit_db=-2.2)
    os.remove(tmp)
    stems = dict(music_in=round(m0, 1), ambience_in=round(a0, 1), premaster_lufs=round(pre, 2), master_lufs=round(post, 2), true_peak=tp)
    print('MIX', stems)
    # stems for delivery (unducked music bed, ducked versions are in the mix)
    for name, y in (('music_stem.wav', mus * duck_m), ('ambience_stem.wav', amb * duck_a), ('fx_stem.wav', fx * duck_a)):
        sf.write(os.path.join(os.path.dirname(out), name), y, SR, subtype='PCM_24')


if __name__ == '__main__':
    main()
