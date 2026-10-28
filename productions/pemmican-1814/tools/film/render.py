"""Render the picture from the EDL.

  python3 -m film.render video  OUT.mp4 [--workers 3] [--scale 1.0] [--from S] [--to S] [--crf 18]
  python3 -m film.render stills OUTDIR t1 t2 ...          (PNG frames at film times)
  python3 -m film.render sheet  OUT.jpg [--every 6]       (contact sheet: one frame per N seconds)

Video is rendered in chunks by parallel workers, each piping RGB frames into its own x264 encoder,
then the chunks are concatenated without re-encoding.
"""
import os, sys, math, bisect, argparse, subprocess, time, json
import numpy as np
import cv2


def _setup(scale):
    from . import core
    if scale != 1.0:
        core.set_size(int(1920 * scale) // 2 * 2, int(1080 * scale) // 2 * 2)
    from . import edl
    return core, edl


class Film:
    def __init__(self, scale=1.0):
        self.core, self.edl = _setup(scale)
        self.clips = self.edl.resolved()
        self.starts = [c['start'] for c in self.clips]
        self.total = self.core.timing()['total']
        self.ovs = self.edl.overlays()

    def _shot(self, c, t):
        return c['shot'].frame(t - c['start'], c['end'] - c['start'], t)

    def picture(self, t):
        core = self.core
        i = max(0, bisect.bisect_right(self.starts, t) - 1)
        cur = self.clips[i]
        x = cur['xfade']
        h = abs(x) / 2
        if x and i > 0 and t < cur['start'] + h:
            return self._blend(self.clips[i - 1], cur, t, (t - (cur['start'] - h)) / abs(x), x < 0)
        if i + 1 < len(self.clips):
            nx = self.clips[i + 1]
            x2 = nx['xfade']
            h2 = abs(x2) / 2
            if x2 and t >= nx['start'] - h2:
                return self._blend(cur, nx, t, (t - (nx['start'] - h2)) / abs(x2), x2 < 0)
        return self._shot(cur, t)

    def _blend(self, a, b, t, w, dip):
        core = self.core
        w = core.clamp(w)
        if dip:
            if w < 0.5:
                return self._shot(a, t) * (1 - core.ease_io(w * 2))
            return self._shot(b, t) * core.ease_io((w - 0.5) * 2)
        e = core.ease_io(w)
        if e <= 0.001:
            return self._shot(a, t)
        if e >= 0.999:
            return self._shot(b, t)
        return self._shot(a, t) * (1 - e) + self._shot(b, t) * e

    def frame(self, idx):
        core = self.core
        from . import text as T
        t = idx / core.FPS
        img = self.picture(t).astype(np.float32)
        # global fade from / to black
        g = min(core.ease_io(t / 1.4), 1.0 - core.ease_io((t - (self.total - 1.6)) / 1.6))
        if g < 1:
            img = img * max(g, 0.0)
        img = core.finish(img, idx, grain=0.02)
        act = [o for o in self.ovs if o[0] - 0.05 <= t <= o[1] + 0.05]
        if act:
            L = T.Layer()
            for t0, t1, fn in act:
                fn(L, t)
            img = core.over(img, L.rgba(), max(g, 0.0))
        return core.to_u8(img)


def _encoder(path, w, h, fps, crf, preset='slow'):
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
           '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-pix_fmt', 'yuv420p',
           '-profile:v', 'high', '-g', str(fps * 2), '-keyint_min', str(fps), '-bf', '2',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def _work(args):
    f0, f1, path, scale, crf = args
    film = Film(scale)
    core = film.core
    enc = _encoder(path, core.W, core.H, core.FPS, crf)
    t = time.time()
    for i in range(f0, f1):
        enc.stdin.write(film.frame(i).tobytes())
    enc.stdin.close()
    enc.wait()
    return path, f1 - f0, time.time() - t


def video(out, workers=3, scale=1.0, t_from=0.0, t_to=None, crf=18, chunk=600):
    import multiprocessing as mp
    film = Film(scale)
    fps = film.core.FPS
    n_total = int(round(film.total * fps))
    f0 = int(round(t_from * fps))
    f1 = n_total if t_to is None else min(n_total, int(round(t_to * fps)))
    tmp = out + '.parts'
    os.makedirs(tmp, exist_ok=True)
    jobs = []
    for a in range(f0, f1, chunk):
        b = min(f1, a + chunk)
        p = os.path.join(tmp, f'{a:06d}_{b:06d}.mp4')
        if os.path.exists(p) and os.path.getsize(p) > 1000 and os.path.exists(p + '.ok'):
            continue
        jobs.append((a, b, p, scale, crf))
    print(f'{len(jobs)} chunks to render ({f1 - f0} frames total range)', flush=True)
    t = time.time()
    ctx = mp.get_context('spawn')
    with ctx.Pool(workers, maxtasksperchild=1) as pool:
        for path, n, dt in pool.imap_unordered(_work, jobs):
            open(path + '.ok', 'w').write(f'{n} {dt:.1f}\n')
            print(f'  {os.path.basename(path)}: {n} frames in {dt:.0f}s ({n / dt:.2f} fps)', flush=True)
    parts = sorted(p for p in os.listdir(tmp) if p.endswith('.mp4'))
    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts:
            a, b = (int(x) for x in p[:-4].split('_'))
            if a >= f0 and b <= f1:
                f.write(f"file '{os.path.join(tmp, p)}'\n")
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-c', 'copy', '-movflags', '+faststart', out], check=True)
    print(f'video done: {out} in {time.time() - t:.0f}s', flush=True)


def stills(outdir, times, scale=1.0):
    film = Film(scale)
    os.makedirs(outdir, exist_ok=True)
    for t in times:
        idx = int(round(float(t) * film.core.FPS))
        im = film.frame(idx)
        cv2.imwrite(os.path.join(outdir, f'f_{float(t):07.2f}.png'), im[:, :, ::-1])


def sheet(out, every=6.0, scale=0.25, cols=6, t_from=0.0, t_to=None):
    film = Film(scale)
    t_to = film.total if t_to is None else t_to
    times = np.arange(t_from + every / 2, t_to, every)
    tiles = []
    for t in times:
        im = film.frame(int(round(t * film.core.FPS)))[:, :, ::-1].copy()
        cv2.putText(im, f'{int(t // 60)}:{t % 60:04.1f}', (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(im)
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode')
    ap.add_argument('out')
    ap.add_argument('times', nargs='*')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--from', dest='t_from', type=float, default=0.0)
    ap.add_argument('--to', dest='t_to', type=float, default=None)
    ap.add_argument('--crf', type=int, default=18)
    ap.add_argument('--every', type=float, default=6.0)
    ap.add_argument('--chunk', type=int, default=600)
    a = ap.parse_args()
    if a.mode == 'video':
        video(a.out, a.workers, a.scale, a.t_from, a.t_to, a.crf, a.chunk)
    elif a.mode == 'stills':
        stills(a.out, a.times, a.scale)
    elif a.mode == 'sheet':
        sheet(a.out, a.every, a.scale if a.scale != 1.0 else 0.25, t_from=a.t_from, t_to=a.t_to)
