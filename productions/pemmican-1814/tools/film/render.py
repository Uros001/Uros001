"""Render the picture from the EDL.

  python3 -m film.render video  OUT.mp4 [--workers 3] [--scale 1.0] [--from S] [--to S] [--crf 18]
  python3 -m film.render stills OUTDIR t1 t2 ...          (PNG frames at film times)
  python3 -m film.render sheet  OUT.jpg [--every 6]       (contact sheet: one frame per N seconds)

Video is rendered in chunks by parallel workers, each piping RGB frames into its own x264 encoder,
then the chunks are concatenated without re-encoding.
"""
import os, sys, math, bisect, argparse, subprocess, time, json, hashlib
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
        img = core.finish(img, idx, grain=0.015)
        act = [o for o in self.ovs if o[0] - 0.05 <= t <= o[1] + 0.05]
        if act:
            L = T.Layer()
            for t0, t1, fn in act:
                fn(L, t)
            img = core.over(img, L.rgba(), max(g, 0.0))
        return core.to_u8(img)


def _free_caches():
    """Drop plate/mask caches in the parent so pool workers have the memory (they reload what they need)."""
    import gc
    from . import shots, gfx, core, life
    for f in (shots.plate_images, shots._parts, gfx._plate_comp, core.load_image, life.texture_mask, life.sky_mask,
              life._sky_prep):
        f.cache_clear()
    gfx._LIVE.clear()
    life._IMGS.clear()
    gc.collect()


def chunk_plates(scale=0.1, chunk=600, step=0.5):
    """Dry-run the edit at tiny scale and return {(f0, f1): set(plate names)} per chunk."""
    from . import shots
    film = Film(scale)
    fps = film.core.FPS
    n = int(round(film.total * fps))
    out = {}
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        shots.ACCESSED.clear()
        for t in list(np.arange(a / fps, b / fps, step)) + [(b - 1) / fps]:
            film.picture(t)
        out[(a, b)] = set(shots.ACCESSED)
    return out


def _encoder(path, w, h, fps, crf, preset='medium'):
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
           '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-pix_fmt', 'yuv420p',
           '-profile:v', 'high', '-g', str(fps * 2), '-keyint_min', str(fps), '-bf', '2',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def _safe(v):
    """JSON-able, address-free description of a shot attribute (for chunk signatures)."""
    if isinstance(v, (str, int, bool)) or v is None:
        return v
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, (list, tuple)):
        return [_safe(x) for x in v[:64]]
    if isinstance(v, dict):
        return {str(k): _safe(x) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
    if isinstance(v, np.ndarray):
        return ['array', list(v.shape)]
    if callable(v):
        return getattr(v, '__qualname__', type(v).__name__)
    return type(v).__name__


def chunk_signature(film, a, b):
    """Hash of everything in the edit that can reach frames a..b: the clips around them (timing, transition,
    shot type and parameters) and the overlays. A finished chunk whose signature changed is re-rendered."""
    fps = film.core.FPS
    t0, t1 = a / fps - 1.5, b / fps + 1.5
    clips = [[round(c['start'], 3), round(c['end'], 3), c['xfade'], type(c['shot']).__name__,
              {k: _safe(v) for k, v in vars(c['shot']).items() if not k.startswith('_')}]
             for c in film.clips if c['end'] >= t0 and c['start'] <= t1]
    ovs = [[round(o0, 3), round(o1, 3), getattr(fn, 'desc', '')] for o0, o1, fn in film.ovs if o1 >= t0 and o0 <= t1]
    return hashlib.sha1(json.dumps([clips, ovs], sort_keys=True, default=str).encode()).hexdigest()[:16]


def _claim(path):
    """Atomically claim a chunk via path.lock (holding the worker PID) so several render processes can share
    the chunk list; a lock whose owner is gone is taken over."""
    lock = path + '.lock'
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                os.kill(int(open(lock).read().strip()), 0)
                return False
            except (ValueError, OSError):
                try:
                    os.remove(lock)
                except FileNotFoundError:
                    pass
                continue
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    return False


def _work(args):
    f0, f1, path, scale, crf, sig = args
    if os.path.exists(path + '.ok') or not _claim(path):
        return path + '.skip', 0, 1.0          # done or being rendered by another process
    try:
        film = Film(scale)
        core = film.core
        enc = _encoder(path, core.W, core.H, core.FPS, crf)
        t = time.time()
        for i in range(f0, f1):
            enc.stdin.write(film.frame(i).tobytes())
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError(f'encoder failed for {path}')
        dt = time.time() - t
        open(path + '.ok', 'w').write(f'{f1 - f0} {dt:.1f}\n{sig}\n')
    finally:
        os.remove(path + '.lock')
    return path, f1 - f0, dt


def _plan(chunk):
    """chunk_plates() cached on disk until any film module changes (the dry-run takes minutes)."""
    import glob
    here = os.path.dirname(os.path.abspath(__file__))
    key = max(os.path.getmtime(f) for f in glob.glob(os.path.join(here, '*.py')))
    cache = os.path.join(here, '..', '..', 'delivery', f'.chunk_plates_{chunk}.json')
    try:
        d = json.load(open(cache))
        if d['key'] == key:
            return {tuple(map(int, k.split('_'))): set(v) for k, v in d['plates'].items()}
    except (OSError, ValueError, KeyError):
        pass
    cp = chunk_plates(chunk=chunk)
    json.dump({'key': key, 'plates': {f'{a}_{b}': sorted(v) for (a, b), v in cp.items()}}, open(cache, 'w'))
    return cp


def video(out, workers=3, scale=1.0, t_from=0.0, t_to=None, crf=18, chunk=600, pending=None, redo=None, stamp=False):
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed
    film = Film(scale)
    core = film.core
    fps = core.FPS
    n_total = int(round(core.timing()['total'] * fps))
    f0 = int(round(t_from * fps))
    f1 = n_total if t_to is None else min(n_total, int(round(t_to * fps)))
    tmp = os.path.abspath(out + '.parts')         # concat lists resolve relative paths against the list's folder
    os.makedirs(tmp, exist_ok=True)
    skip = set()
    # dry-run in a child process so this parent stays small while the workers run
    with ProcessPoolExecutor(1, mp_context=mp.get_context('spawn')) as ex:
        cp = ex.submit(_plan, chunk).result()
    if pending:
        skip = {k for k, v in cp.items() if v & pending}
        print(f'{len(skip)} chunks wait for pending plates', flush=True)
    # invalidate finished chunks whose edit changed (signature stored in the .ok file); --stamp records the
    # current signature in .ok files written before signatures existed
    sigs = {(a, b): chunk_signature(film, a, b) for (a, b) in cp}
    for (a, b), sg in sigs.items():
        p = os.path.join(out + '.parts', f'{a:06d}_{b:06d}.mp4')
        if not os.path.exists(p + '.ok'):
            continue
        lines = open(p + '.ok').read().split()
        if len(lines) >= 3 and lines[2] != sg:
            os.remove(p + '.ok')
            print(f'  edit changed in chunk {a}-{b}', flush=True)
        elif len(lines) < 3 and stamp:
            open(p + '.ok', 'a').write(sg + '\n')
    if stamp:
        print('signatures stamped', flush=True)
        return
    # invalidate finished chunks whose plates were re-rendered after the chunk was encoded,
    # or that use plates whose compositing settings changed since (--redo)
    pdir = os.path.join(core.ROOT, 'renders/plates')
    for (a, b), names in cp.items():
        p = os.path.join(out + '.parts', f'{a:06d}_{b:06d}.mp4')
        if os.path.exists(p + '.ok') and redo and names & redo:
            os.remove(p + '.ok')
            print(f'  redo chunk {a}-{b} ({sorted(names & redo)})', flush=True)
        if os.path.exists(p + '.ok'):
            t_chunk = os.path.getmtime(p)
            newer = [n for n in names if any(os.path.exists(os.path.join(pdir, n + suf)) and
                                             os.path.getmtime(os.path.join(pdir, n + suf)) > t_chunk for suf in ('_bg.png', '_fg.png'))]
            if newer:
                os.remove(p + '.ok')
                print(f'  stale chunk {a}-{b} (newer plates: {newer})', flush=True)
    jobs = []
    for a in range(f0, f1, chunk):
        if (a, min(f1, a + chunk)) in skip:
            continue
        b = min(f1, a + chunk)
        p = os.path.join(tmp, f'{a:06d}_{b:06d}.mp4')
        if os.path.exists(p) and os.path.getsize(p) > 1000 and os.path.exists(p + '.ok'):
            continue
        jobs.append((a, b, p, scale, crf, sigs.get((a, b), '')))
    print(f'{len(jobs)} chunks to render ({f1 - f0} frames total range)', flush=True)
    t = time.time()
    # an executor (unlike Pool) fails fast if a worker is killed, e.g. by the OOM killer; finished chunks are kept
    with ProcessPoolExecutor(workers, mp_context=mp.get_context('spawn'), max_tasks_per_child=1) as ex:
        for fut in as_completed([ex.submit(_work, j) for j in jobs]):
            path, n, dt = fut.result()
            if not n:
                continue
            print(f'  {os.path.basename(path)}: {n} frames in {dt:.0f}s ({n / dt:.2f} fps)', flush=True)
    if skip:
        print('partial pass done; re-run without --pending to finish', flush=True)
        return
    missing = [j[2] for j in jobs if not os.path.exists(j[2] + '.ok')]
    if missing:
        raise SystemExit(f'{len(missing)} chunks not finished (rendered by another process?): run again')
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
    ap.add_argument('--pending', default='', help='comma-separated plate names not final yet: skip chunks that use them')
    ap.add_argument('--redo', default='', help='comma-separated plate names whose finished chunks must be re-rendered')
    ap.add_argument('--stamp', action='store_true', help='record edit signatures in finished chunks that have none')
    a = ap.parse_args()
    if a.mode == 'video':
        pend = set(x for x in a.pending.split(',') if x)
        redo = set(x for x in a.redo.split(',') if x)
        video(a.out, a.workers, a.scale, a.t_from, a.t_to, a.crf, a.chunk, pend or None, redo or None, a.stamp)
    elif a.mode == 'stills':
        stills(a.out, a.times, a.scale)
    elif a.mode == 'sheet':
        sheet(a.out, a.every, a.scale if a.scale != 1.0 else 0.25, t_from=a.t_from, t_to=a.t_to)
