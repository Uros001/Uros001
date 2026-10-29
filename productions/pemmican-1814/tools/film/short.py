"""Vertical Short (1080x1920, ~56 s) cut from the cold open: same shots reframed for portrait, burned-in
captions from the narration timing, end card. Audio is the final mix (0 s to the end of P05.0) with a fade.

  python3 -m film.short OUT.mp4 [--workers 3]
"""
import os, sys, subprocess, argparse, time
import numpy as np


def setup():
    from . import core
    core.set_size(1080, 1920)
    from . import edl, text as T
    return core, edl, T


END = None


def clips(core, edl):
    A = core.anchor
    P = edl.P
    return [
        (0.0, P('dock_D1', s=(1.0, 1.12), c=((0.47, 0.55), (0.47, 0.6)), p=0.07)),
        (A('P01.2-0.35'), P('dock_D2', s=(1.0, 1.08), c=((0.45, 0.5), (0.55, 0.5)))),
        (A('P02.0-0.45'), P('dock_C1', s=(1.0, 1.06), c=((0.62, 0.5), (0.66, 0.5)))),
        (A('P02.1-0.15'), P('fort_F1', s=(1.0, 1.08), c=((0.42, 0.5), (0.46, 0.5)), dust=edl.SNOW)),
        (A('P02.1+6.5'), edl.DOC('proclamation', (0.5, 0.36, 1.02), (0.5, 0.35, 0.9), [('take_out', 1.8, 1.6)])),
        (A('P02.1e+0.8'), 'NOTMOVE'),
        (A('P04.0-0.5'), P('plain_G3', s=(1.0, 1.06), c=((0.5, 0.5), (0.52, 0.5)), fog=edl.DUSK_FOG, grade=edl.G_DUSK, dust=None)),
        (A('P04.1-0.25'), P('plain_G2', s=(1.0, 1.08), c=((0.45, 0.55), (0.55, 0.55)), grade=edl.G_DUSK, rack=edl.DENOISE_FG)),
        (A('P05.0-0.35'), P('dock_D3', s=(1.0, 1.08), c=((0.4, 0.5), (0.42, 0.52)), p=0.08)),
        (A('P05.0e+0.6'), 'END'),
    ]


class Short:
    def __init__(self):
        self.core, self.edl, self.T = setup()
        self.list = clips(self.core, self.edl)
        self.total = self.core.anchor('P05.0e') + 4.6
        self.sents = [s for s in self.core.timing()['sentences'] if s['end'] <= self.core.anchor('P05.0e') + 0.01]

    def picture(self, t):
        core = self.core
        starts = [c[0] for c in self.list]
        i = max(0, int(np.searchsorted(starts, t, side='right')) - 1)
        st, sh = self.list[i]
        end = starts[i + 1] if i + 1 < len(starts) else self.total
        tl, dur = t - st, end - st
        if sh == 'NOTMOVE':
            return self.notmove(t)
        if sh == 'END':
            return self.endcard(tl)
        img = sh.frame(tl, dur, t)
        # 0.5 s dissolve into the next clip
        if i + 1 < len(self.list) and t > end - 0.25 and self.list[i + 1][1] not in ('END',):
            pass
        return img

    def notmove(self, t):
        core, T = self.core, self.T
        out = core.blank(core.hexc('#121110'))
        L = T.Layer()
        a1 = T.fade_window(t, core.anchor('P03.0') - 0.25, core.anchor('P04.0') - 0.5, 0.5, 0.5)
        a2 = T.fade_window(t, core.anchor('P03.1') - 0.2, core.anchor('P04.0') - 0.5, 0.35, 0.5)
        self._text(L, 'Not illegal to eat.', 860, T.font('serif_i', 120 * 1920 / 1080, 500), T.INK_DIM, a1)
        self._text(L, 'ILLEGAL', 1100, T.font('serif', 190 * 1920 / 1080, 600), T.RUST, a2)
        self._text(L, 'TO MOVE.', 1290, T.font('serif', 190 * 1920 / 1080, 600), T.RUST, a2)
        return core.over(out, L.rgba())

    def endcard(self, tl):
        core, T = self.core, self.T
        out = core.blank(core.hexc('#121110'))
        L = T.Layer()
        a = T.fade_window(tl, 0, 10, 0.5, 0.5)
        self._text(L, 'THE PEMMICAN', 840, T.font('serif', 100 * 1920 / 1080, 600), T.INK, a)
        self._text(L, 'WAR', 980, T.font('serif', 100 * 1920 / 1080, 600), T.OCHRE, a)
        self._text(L, 'Full documentary on the channel', 1180, T.font('serif_i', 56 * 1920 / 1080, 500), T.INK_DIM, a)
        return core.over(out, L.rgba())

    def _text(self, L, txt, y, f, col, a):
        # positions in 1080-wide design pixels (Layer.s() scales by W/1920, so convert)
        k = 1920 / 1080
        L.text(txt, 540 * k, y * k, f, col, a, align='center', shadow=0.8)

    def captions(self, L, t):
        core, T = self.core, self.T
        k = 1920 / 1080
        if core.anchor('P02.1e+0.8') <= t < core.anchor('P04.0-0.5'):
            return                                 # the typographic card carries these words
        import re
        for s in self.sents:
            if not (s['start'] - 0.05 <= t <= s['end'] + 0.25):
                continue
            parts = [p for p in re.split(r'(?<=[,;:])\s+', s['text']) if p]
            chunks, cur = [], ''
            for p in parts:
                if cur and len(cur) + len(p) > 46:
                    chunks.append(cur)
                    cur = p
                else:
                    cur = (cur + ' ' + p).strip()
            chunks.append(cur)
            tot = sum(len(c) for c in chunks)
            t0 = s['start']
            for c in chunks:
                t1 = t0 + (s['end'] - s['start']) * len(c) / tot
                if t0 - 0.05 <= t < t1 + (0.25 if c is chunks[-1] else 0):
                    words, lines, cur = c.split(), [], ''
                    for w in words:
                        if len(cur) + len(w) + 1 > 22:
                            lines.append(cur)
                            cur = w
                        else:
                            cur = (cur + ' ' + w).strip()
                    lines.append(cur)
                    y0 = 1460 - (len(lines) - 1) * 46
                    f = T.font('sans', 66 * 1920 / 1080, 700)
                    # soft dark plate behind the words so they stay legible over snow and bright sky
                    bw = max(L.measure(ln, f) for ln in lines) / L.s(1) + 56 * k
                    L.rect(540 * k - bw / 2, (y0 - 78) * k, bw, ((len(lines) - 1) * 92 + 112) * k, T.DARK, 0.42,
                           radius=22 * k)
                    for j, ln in enumerate(lines):
                        L.text(ln, 540 * k, (y0 + j * 92) * k, f, T.INK, 1.0, align='center', shadow=1.6)
                    break
                t0 = t1

    def frame(self, idx):
        core, T = self.core, self.T
        t = idx / core.FPS
        img = self.picture(t)
        g = min(core.ease_io(t / 0.6), 1.0 - core.ease_io((t - (self.total - 0.8)) / 0.8))
        img = core.finish(img * max(g, 0), idx, grain=0.015)
        L = T.Layer()
        if t < core.anchor('P05.0e') + 0.3:
            self.captions(L, t)
        starts = [c[0] for c in self.list]
        for i, (st, sh) in enumerate(self.list):
            cr = getattr(sh, 'credit', None)
            if cr and cr[0]:                         # on-screen credit for archival material, top right
                en = starts[i + 1] if i + 1 < len(starts) else self.total
                T.credit(L, t, st + 0.6, en - 0.35, cr[0], cr[1], y=150)
        img = core.over(img, L.rgba())
        return core.to_u8(img)


def _work(args):
    f0, f1, path = args
    if os.path.exists(path + '.ok'):
        return path
    sh = Short()
    core = sh.core
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920',
           '-r', '30', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-g', '60', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1):
        p.stdin.write(sh.frame(i).tobytes())
    p.stdin.close()
    if p.wait() == 0:
        open(path + '.ok', 'w').write('ok\n')
    return path


def main():
    import multiprocessing as mp
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    sh = Short()
    n = int(round(sh.total * 30))
    tmp = os.path.abspath(a.out + '.parts')       # concat lists resolve relative paths against the list's folder
    os.makedirs(tmp, exist_ok=True)
    jobs = [(i, min(n, i + 300), os.path.join(tmp, f'{i:05d}.mp4')) for i in range(0, n, 300)]
    with mp.get_context('spawn').Pool(a.workers) as pool:
        parts = list(pool.imap(_work, jobs))
    lst = os.path.join(tmp, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
    vid = os.path.join(tmp, 'video.mp4')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', vid], check=True)
    import soundfile as sf
    root = sh.core.ROOT
    mix, sr = sf.read(os.path.join(root, 'audio/mix/pemmican_mix_master.wav'), dtype='float32', always_2d=True)
    mus, _ = sf.read(os.path.join(root, 'audio/mix/music_stem.wav'), dtype='float32', always_2d=True)
    dur = sh.total
    n = int(dur * sr)
    cut = int((sh.core.anchor('P05.1') - 0.12) * sr)        # before the next sentence starts
    xf = int(0.25 * sr)
    out = np.zeros((n, 2), np.float32)
    out[:cut] = mix[:cut]
    w = np.linspace(1, 0, xf, dtype=np.float32)[:, None]
    out[cut - xf:cut] *= w
    tail = mus[cut - xf:n] * 1.6
    out[cut - xf:n] += tail[: n - cut + xf] * (1 - np.concatenate([w, np.zeros((n - cut, 1), np.float32)]))
    fo = int(2.5 * sr)
    out[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
    wav = os.path.join(tmp, 'audio.wav')
    sf.write(wav, np.clip(out, -0.95, 0.95), sr, subtype='PCM_24')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', vid, '-i', wav, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', a.out],
                   check=True)
    print('short written', a.out, round(dur, 1), 's')


if __name__ == '__main__':
    main()
