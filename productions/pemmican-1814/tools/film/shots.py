"""Shot types for the timeline. Every shot renders an RGB float frame for local time tl in [-pre, dur+post].

  Plate    2.5D move over Blender background/foreground plates (parallax, fog, particles, grade)
  Still    a single image (render or graphic) with a slow move
  Archive, Diptych, Sequence   archival paintings/photographs (rostrum moves)
  DocPage  a real scanned document page with highlighter marks
  Func     any callable fn(tl, dur) -> RGB (maps, graphics, cards)
"""
import os, json, math, functools
import numpy as np
import cv2
from . import core, life as LF
from .core import ease_io, ease_io5, lerp, seg, clamp

PLATES = os.path.join(core.ROOT, 'renders/plates')
ACCESSED = set()          # plate names touched (for chunk readiness checks)


@functools.lru_cache(maxsize=10)
def plate_images(name):
    bgp = os.path.join(PLATES, name + '_bg.png')
    if not os.path.exists(bgp):            # preview placeholder while plates are still rendering
        ph = np.full((1296, 2304, 3), 46, np.uint8)
        cv2.putText(ph, f'PLATE PENDING: {name}', (200, 660), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (200, 200, 200), 6, cv2.LINE_AA)
        return ph.astype(np.float32) / 255.0, None, {}
    bg = core.load_image.__wrapped__(bgp)
    fgp = os.path.join(PLATES, name + '_fg.png')
    fg = core.load_image.__wrapped__(fgp) if os.path.exists(fgp) else None
    mp = os.path.join(PLATES, name + '_meta.json')
    meta = json.load(open(mp)) if os.path.exists(mp) else {}
    return bg, fg, meta


@functools.lru_cache(maxsize=2)
def _parts(name):
    """Connected components of a FG plate's alpha (dilated so each animal is one part), in a random but
    fixed order. Returns (label image, order list)."""
    _, fg, _ = plate_images(name)
    m = (fg[:, :, 3] > 0.02).astype(np.uint8)
    m2 = cv2.dilate(m, np.ones((9, 9), np.uint8))
    n, lab = cv2.connectedComponents(m2)
    order = list(np.random.default_rng(4).permutation(np.arange(1, n)))
    return lab.astype(np.int32), order


def _ease(kind, u):
    return {'io': ease_io, 'io5': ease_io5, 'lin': lambda x: clamp(x), 'out': core.ease_out}[kind](u)


def handheld(t, amp, seed=0):
    """Slow organic drift (normalized frame units)."""
    if not amp:
        return 0.0, 0.0, 0.0
    ph = seed * 1.7
    x = (math.sin(t * 0.31 + ph) * 0.6 + math.sin(t * 0.73 + ph * 2.1) * 0.3 + math.sin(t * 1.9 + ph * 0.7) * 0.1)
    y = (math.sin(t * 0.27 + ph * 1.3) * 0.6 + math.sin(t * 0.61 + ph * 0.4) * 0.3 + math.sin(t * 1.7 + ph) * 0.1)
    r = math.sin(t * 0.21 + ph * 0.9) * 0.6 + math.sin(t * 0.5 + ph) * 0.4
    return x * amp, y * amp * 0.8, r * amp * 25


class Shot:
    desc = ''
    source = ''

    def frame(self, tl, dur, t):
        raise NotImplementedError


class Plate(Shot):
    """Move over a BG/FG plate pair.

    s   (start, end) zoom; 1.0 = whole plate fitted to cover the frame
    c   ((cx0, cy0), (cx1, cy1)) normalized plate point held at frame centre
    p   parallax gain of the FG layer relative to the BG move
    fog dict for core.fog_layer, drawn between BG and FG
    dust dict for core.Particles.draw (in front)
    grade dict for core.grade
    """

    def __init__(self, name, s=(1.0, 1.06), c=((0.5, 0.5), (0.5, 0.5)), p=0.06, ease='io', hand=0.0012,
                 fog=None, fog2=None, dust=None, grade=None, bloom=(0.8, 0.18), flicker=0.0, fg_fade=None,
                 desc='', source='', post=None, fg_alpha=1.0, seed=0, fade_parts=None, life=None, rack=None):
        self.name, self.s, self.c, self.p, self.ease, self.hand = name, s, c, p, ease, hand
        self.fog, self.fog2, self.dust, self.grd, self.bloom = fog, fog2, dust, grade or {}, bloom
        self.flicker, self.fg_fade, self.post, self.fg_alpha, self.seed = flicker, fg_fade, post, fg_alpha, seed
        self.fade_parts = fade_parts      # (t0, t1) film seconds: FG connected parts fade out one by one
        self.life = life or {}             # wind / fgwind / water / clouds / smoke / heat / chroma (see film.life)
        self.rack = rack                   # dict(layer='fg'|'bg', sigma=(s0, s1), span=(u0, u1)): focus pull
        self._smoke = None
        self.desc = desc or name
        self.source = source or f'Original Blender 3D reconstruction ({name})'
        self._parts = None

    def transform(self, u, parallax=0.0):
        s0, s1 = self.s
        (x0, y0), (x1, y1) = self.c
        e = _ease(self.ease, u)
        s = s0 * (s1 / s0) ** e
        sp = s0 * (s1 / s0) ** (e * (1 + parallax))
        cx, cy = lerp(x0, x1, e), lerp(y0, y1, e)
        cx = x0 + (cx - x0) * (1 + parallax)
        cy = y0 + (cy - y0) * (1 + parallax)
        return sp if parallax else s, cx, cy

    def frame(self, tl, dur, t):
        ACCESSED.add(self.name)
        bg, fg, meta = plate_images(self.name)
        sh, sw = bg.shape[:2]
        u = seg(tl, 0, dur)
        hx, hy, hr = handheld(t, self.hand, self.seed)
        aspect_fix = (sw / sh) / (core.W / core.H)

        def M(scale, cx, cy, extra=1.0):
            # keep the view inside the plate
            half_w = 0.5 / scale / max(aspect_fix, 1.0) * (1.0 if aspect_fix >= 1 else 1.0)
            vis_w = (core.W / (max(core.W / sw, core.H / sh) * scale)) / sw / 2
            vis_h = (core.H / (max(core.W / sw, core.H / sh) * scale)) / sh / 2
            cx = clamp(cx, vis_w, 1 - vis_w)
            cy = clamp(cy, vis_h, 1 - vis_h)
            return core.affine(scale, cx, cy, -hx * extra, -hy * extra, hr * extra, sw, sh)

        L_ = self.life
        bg0 = bg
        if L_.get('wind'):
            bg = LF.wind(bg, t, self.name + ':bg', ref=bg0, **L_['wind'])
        if L_.get('water'):
            bg = LF.water(bg, t, self.name + ':bg', ref=bg0, **L_['water'])
        if L_.get('clouds'):
            bg = LF.clouds(bg, t, self.name + ':bg', ref=bg0, **L_['clouds'])
        if fg is not None and L_.get('fgwind'):
            fg0 = fg
            fg = LF.wind(fg, t, self.name + ':fg', ref=fg0, **L_['fgwind'])
        if self.rack:
            r = self.rack
            k = ease_io(seg(u, *r.get('span', (0.0, 0.4))))
            sig = lerp(r['sigma'][0], r['sigma'][1], k) * sw / 2304
            if sig > 0.3:
                if r.get('layer', 'fg') == 'fg' and fg is not None:
                    pm = fg[:, :, :3] * fg[:, :, 3:4]
                    pm = cv2.GaussianBlur(pm, (0, 0), sig)
                    al = cv2.GaussianBlur(fg[:, :, 3], (0, 0), sig)
                    fg = np.dstack([pm / np.maximum(al[:, :, None], 1e-4), al])
                else:
                    bg = cv2.GaussianBlur(bg, (0, 0), sig)
        s, cx, cy = self.transform(u)
        Mbg = M(s, cx, cy)
        out = core.warp(bg, Mbg)
        if self.flicker:
            f = 1 + self.flicker * (math.sin(t * 11.3) * 0.5 + math.sin(t * 17.9 + 1) * 0.3 + math.sin(t * 5.1) * 0.2)
            out = out * f
        if self.fog:
            out = core.over(out, core.fog_layer(t, **self.fog))
        if fg is not None and self.fade_parts:
            lab, order = _parts(self.name)
            t0, t1 = self.fade_parts
            n = len(order)
            lut = np.ones(n + 1, np.float32)
            for k, comp_id in enumerate(order):
                ts = t0 + (t1 - t0) * k / max(n, 1)
                lut[comp_id] = 1.0 - ease_io(seg(t, ts, ts + (t1 - t0) / max(n, 1) * 1.6))
            fg = fg.copy()
            fg[:, :, 3] *= lut[lab]
        if fg is not None:
            s2, cx2, cy2 = self.transform(u, self.p)
            fgw = core.warp(fg, M(s2, cx2, cy2, 1.0 + self.p * 2), border=cv2.BORDER_CONSTANT)
            a = self.fg_alpha
            if self.fg_fade:
                a *= self.fg_fade(tl, dur)
            if a > 0:
                out = core.over(out, fgw, a)
        if self.fog2:
            out = core.over(out, core.fog_layer(t, **self.fog2))
        if L_.get('smoke') or L_.get('heat'):
            def tf(px, py):
                q = Mbg @ np.array([px * sw, py * sh, 1.0], np.float32)
                return float(q[0] / core.W), float(q[1] / core.H)
            zoom = float(np.hypot(Mbg[0, 0], Mbg[1, 0])) * sw / core.W
            if L_.get('smoke'):
                cfg = dict(L_['smoke'])
                pts = cfg.pop('points')
                em = [(*tf(px, py), k * zoom) for px, py, k in pts]
                sm = LF.Smoke(em, **cfg)
                out = sm.draw(out, t)
            if L_.get('heat'):
                hb = L_['heat']['box']
                a0, b0 = tf(hb[0], hb[1])
                a1, b1 = tf(hb[2], hb[3])
                out = LF.heat(out, t, (max(0, a0), max(0, b0), min(1, a1), min(1, b1)), L_['heat'].get('strength', 2.0))
        if self.post:
            out = self.post(out, tl, dur, t)
        if self.dust:
            if self._parts is None:
                d = dict(self.dust)
                self._parts = core.Particles(d.pop('n', 260), d.pop('seed', 5), d.pop('kind', 'dust'))
                self._dust_kw = d
            out = self._parts.draw(out, t, **self._dust_kw)
        if self.bloom:
            out = core.bloom(out, *self.bloom)
        if self.grd:
            out = core.grade(out, **self.grd)
        if L_.get('chroma', 0.0009):
            out = LF.chroma(out, L_.get('chroma', 0.0009))
        return out


class Still(Shot):
    """Single image (RGB) with a slow Ken-Burns-style move; used for graphics and full renders."""

    def __init__(self, path, s=(1.0, 1.05), c=((0.5, 0.5), (0.5, 0.5)), ease='io', grade=None, desc='', source=''):
        self.path, self.s, self.c, self.ease, self.grd = path, s, c, ease, grade or {}
        self.desc, self.source = desc or os.path.basename(path), source

    def frame(self, tl, dur, t):
        img = core.load_image(self.path)[:, :, :3]
        sh, sw = img.shape[:2]
        e = _ease(self.ease, seg(tl, 0, dur))
        s = self.s[0] * (self.s[1] / self.s[0]) ** e
        cx = lerp(self.c[0][0], self.c[1][0], e)
        cy = lerp(self.c[0][1], self.c[1][1], e)
        out = core.warp(np.ascontiguousarray(img), core.affine(s, cx, cy, src_w=sw, src_h=sh))
        return core.grade(out, **self.grd) if self.grd else out


@functools.lru_cache(maxsize=6)
def _arch_pyr(path):
    """uint8 RGB image pyramid (full size down to ~1600 px) for archival stills."""
    im = cv2.imread(path, cv2.IMREAD_COLOR)
    if im is None:
        raise FileNotFoundError(path)
    pyr = [np.ascontiguousarray(im[:, :, ::-1])]
    while max(pyr[-1].shape[:2]) > 1600:
        pyr.append(cv2.pyrDown(pyr[-1]))
    return pyr


def _arch_view(path, cx, cy, w, out_w, out_h):
    """The window of width w (fraction of image width, 16:9 or out aspect) centred at (cx, cy) in normalized
    image coords, resampled to out_w x out_h. The window is kept inside the image (no mirrored edges)."""
    pyr = _arch_pyr(path)
    H0, W0 = pyr[0].shape[:2]
    w = min(w, H0 * out_w / out_h / W0)
    ww, wh = w * W0, w * W0 * out_h / out_w
    cxp = min(max(cx * W0, ww / 2), W0 - ww / 2)
    cyp = min(max(cy * H0, wh / 2), H0 - wh / 2)
    s = out_w / ww
    k = 0
    while k + 1 < len(pyr) and s * 2 ** (k + 1) <= 1.0:
        k += 1
    f = 2 ** k
    sk = s * f
    M = np.array([[sk, 0, out_w / 2 - sk * cxp / f], [0, sk, out_h / 2 - sk * cyp / f]], np.float32)
    out = cv2.warpAffine(pyr[k], M, (out_w, out_h), flags=cv2.INTER_CUBIC if sk > 1.0 else cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)
    return out.astype(np.float32) / 255.0


def _mono(img, amount, tone=(1.0, 0.97, 0.9)):
    if not amount:
        return img
    y = (img @ core._LUM.T)
    return img * (1 - amount) + y * np.array(tone, np.float32) * amount


class Archive(Shot):
    """Archival painting or photograph filmed like a rostrum camera: an eased move between two framings.

    a, b  framings (cx, cy, w): centre in normalized image coords and the width of the frame window as a
          fraction of the image width. The window never leaves the image.
    mono  0..1 desaturation (photographs); grade: core.grade kwargs.
    """

    def __init__(self, path, a=(0.5, 0.5, 1.0), b=None, ease='io', mono=0.0, grade=None, desc='', source=''):
        self.path, self.a, self.b, self.ease, self.mono, self.grd = path, a, b or a, ease, mono, grade or {}
        self.desc, self.source = desc, source
        self.name = 'archive:' + os.path.basename(path)

    def frame(self, tl, dur, t):
        e = _ease(self.ease, seg(tl, 0, dur))
        cx, cy, w = (lerp(p, q, e) for p, q in zip(self.a, self.b))
        out = _mono(_arch_view(self.path, cx, cy, w, core.W, core.H), self.mono)
        return core.grade(out, **self.grd) if self.grd else out


@functools.lru_cache(maxsize=4)
def _ground(seed=3):
    """Dark, faintly textured ground for prints and portraits (like a museum wall or a mount board)."""
    rng = np.random.default_rng(seed)
    n = cv2.resize(rng.normal(0, 1, (core.H // 8, core.W // 8)).astype(np.float32), (core.W, core.H),
                   interpolation=cv2.INTER_CUBIC)
    n = cv2.GaussianBlur(n, (0, 0), 6) * 0.012
    yy, xx = np.mgrid[0:core.H, 0:core.W].astype(np.float32)
    v = 1.0 - 0.35 * (((xx / core.W - 0.5) * 1.3) ** 2 + ((yy / core.H - 0.5) * 1.6) ** 2)
    base = np.array(core.hexc('#17140f'), np.float32)
    return np.clip(base[None, None] * v[:, :, None] + n[:, :, None], 0, 1).astype(np.float32)


def _fit(path, box_h):
    """Whole image resized so its height is box_h px (float RGB)."""
    pyr = _arch_pyr(path)
    k = 0
    while k + 1 < len(pyr) and pyr[k + 1].shape[0] >= box_h:
        k += 1
    im = pyr[k]
    w = int(round(im.shape[1] * box_h / im.shape[0]))
    return cv2.resize(im, (w, int(box_h)), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def _place(dst, img, cx, cy, shadow=0.55):
    """Paste img centred at (cx, cy) px with a soft drop shadow."""
    h, w = img.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    sh = np.zeros(dst.shape[:2], np.float32)
    sh[max(0, y0 + 10):y0 + h + 10, max(0, x0 + 6):x0 + w + 6] = 1.0
    sh = cv2.GaussianBlur(sh, (0, 0), 14) * shadow
    dst = dst * (1 - sh[:, :, None])
    ya, yb, xa, xb = max(0, y0), min(dst.shape[0], y0 + h), max(0, x0), min(dst.shape[1], x0 + w)
    dst[ya:yb, xa:xb] = img[ya - y0:yb - y0, xa - x0:xb - x0]
    return dst


class Diptych(Shot):
    """Two portraits side by side on a dark ground with a slow push; captions drawn under each."""

    def __init__(self, paths, captions, zoom=(1.0, 1.05), desc='', source=''):
        self.paths, self.captions, self.zoom, self.desc, self.source = paths, captions, zoom, desc, source
        self.name = 'archive:diptych'

    def frame(self, tl, dur, t):
        from . import text as T
        e = ease_io(seg(tl, 0, dur))
        z = lerp(self.zoom[0], self.zoom[1], e)
        out = _ground().copy()
        box = core.H * 0.70 * z
        for i, p in enumerate(self.paths):
            img = _fit(p, box)
            out = _place(out, img, core.W * (0.32 + 0.36 * i), core.H * 0.45)
        L = T.Layer()
        for i, (l1, l2) in enumerate(self.captions):
            x = 1920 * (0.32 + 0.36 * i)
            a = T.fade_window(tl, 0.6 + 0.5 * i, dur + 1, 0.8, 0.1)
            L.text(l1, x, 1080 * 0.45 + 1080 * 0.35 * z + 58, T.font('serif_i', 30, 500), T.INK, a, align='center', shadow=0.6)
            L.text(l2.upper(), x, 1080 * 0.45 + 1080 * 0.35 * z + 92, T.font('sans', 15, 600), T.INK_DIM, a,
                   align='center', tracking=2.5, shadow=0.6)
        return core.over(out, L.rgba())


class Sequence(Shot):
    """Animated photographic sequence (Muybridge) shown as a mounted print on a dark ground.

    frames  list of image paths played in a loop at fps; zoom: print scale over the shot;
    fade    (u0, u1): the print fades out over this part of the shot (normalized time).
    """

    def __init__(self, frames, fps=10.0, height=0.5, zoom=(1.0, 1.06), fade=None, mono=0.0, desc='', source=''):
        self.frames, self.fps, self.height, self.zoom, self.fade, self.mono = frames, fps, height, zoom, fade, mono
        self.desc, self.source = desc, source
        self.name = 'archive:sequence'

    def frame(self, tl, dur, t):
        e = ease_io(seg(tl, 0, dur))
        z = lerp(self.zoom[0], self.zoom[1], e)
        i = int(math.floor(max(tl, 0.0) * self.fps)) % len(self.frames)
        h = int(core.H * self.height * z)
        img = _mono(_fit(self.frames[i], h), self.mono)
        m = int(round(h * 0.045))                                   # cream paper margin of the print
        card = np.empty((img.shape[0] + 2 * m, img.shape[1] + 2 * m, 3), np.float32)
        card[:] = np.array(core.hexc('#e9e1cf'), np.float32)
        card[m:-m, m:-m] = img
        out = _place(_ground().copy(), card, core.W / 2, core.H * 0.47)
        if self.fade:
            k = ease_io(seg(tl / max(dur, 1e-6), *self.fade))
            if k > 0:
                out = out * (1 - k) + _ground() * k
        return out


@functools.lru_cache(maxsize=1)
def _doc_marks():
    return json.load(open(os.path.join(core.ROOT, 'assets/archival/work/doc_marks.json')))


def _doc_view(path, cx, cy, w, tone, lamp):
    """A scanned page seen through a 16:9 window: centre (cx, cy) in page coords (0..1), window width w as a
    fraction of the page width. w > 1 shows the page lying on a dark ground (with a soft shadow). Returns the frame
    and the page-to-frame mapping (scale, ox, oy) in px so highlights can be drawn in frame coordinates."""
    pyr = _arch_pyr(path)
    H0, W0 = pyr[0].shape[:2]
    ow, oh = core.W, core.H
    ww = w * W0
    wh = ww * oh / ow
    cxp, cyp = cx * W0, cy * H0
    if ww <= W0:
        cxp = min(max(cxp, ww / 2), W0 - ww / 2)
    if wh <= H0:
        cyp = min(max(cyp, wh / 2), H0 - wh / 2)
    s = ow / ww
    k = 0
    while k + 1 < len(pyr) and s * 2 ** (k + 1) <= 1.0:
        k += 1
    f = 2 ** k
    sk = s * f
    M = np.array([[sk, 0, ow / 2 - sk * cxp / f], [0, sk, oh / 2 - sk * cyp / f]], np.float32)
    flag = cv2.INTER_CUBIC if sk > 1.0 else cv2.INTER_LINEAR
    page = cv2.warpAffine(pyr[k], M, (ow, oh), flags=flag, borderMode=cv2.BORDER_REPLICATE).astype(np.float32) / 255.0
    page = page * np.array(tone, np.float32)
    yy, xx = np.mgrid[0:oh, 0:ow].astype(np.float32)
    lx, ly, lo = lamp
    page = page * (1.0 - lo * np.clip(((xx / ow - lx) / 0.75) ** 2 + ((yy / oh - ly) / 0.8) ** 2, 0, 1))[:, :, None]
    ox, oy = ow / 2 - s * cxp, oh / 2 - s * cyp
    if ww > W0 * 0.985 or wh > H0 * 0.985:                           # the page edge is in view: put it on the ground
        a = cv2.warpAffine(np.ones((pyr[k].shape[0], pyr[k].shape[1]), np.float32), M, (ow, oh), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        sh = cv2.GaussianBlur(np.roll(a, (int(oh * 0.012), int(ow * 0.006)), (0, 1)), (0, 0), 14) * 0.6
        out = _ground() * (1 - sh[:, :, None])
        out = out * (1 - a[:, :, None]) + page * a[:, :, None]
    else:
        out = page
    return out, (s, ox, oy)


_HILITE = np.array([1.0, 0.84, 0.36], np.float32)                  # highlighter ink (multiplied onto the page)


class DocPage(Shot):
    """A real document page (scan) filmed like a rostrum camera, with highlighter marks that draw on.

    key     page name in work/doc_marks.json (file work/doc_<key>.jpg)
    a, b    framings (cx, cy, w) as for Archive, but w may exceed 1 (the whole page on a dark ground)
    marks   [(phrase, t0, dur)] or [(phrase, t0, dur, t_off)] phrases of doc_marks.json: the marker runs along the
            phrase line by line from t0 for dur seconds and fades at t_off (default: stays)
    """

    def __init__(self, key, a, b=None, marks=(), ease='io', tone=(0.96, 0.90, 0.78), lamp=(0.5, 0.4, 0.38),
                 grade=None, desc='', source=''):
        self.key, self.a, self.b, self.marks, self.ease, self.tone, self.lamp, self.grd = key, a, b or a, marks, ease, tone, lamp, grade or {}
        self.path = os.path.join(core.ROOT, f'assets/archival/work/doc_{key}.jpg')
        self.desc, self.source = desc, source
        self.name = f'archive:doc_{key}'

    def frame(self, tl, dur, t):
        e = _ease(self.ease, seg(tl, 0, dur))
        cx, cy, w = (lerp(p, q, e) for p, q in zip(self.a, self.b))
        out, (s, ox, oy) = _doc_view(self.path, cx, cy, w, self.tone, self.lamp)
        pyr = _arch_pyr(self.path)
        H0, W0 = pyr[0].shape[:2]
        pm = _doc_marks()[self.key]
        ink = np.zeros(out.shape[:2], np.float32)
        for m in self.marks:
            name, t0, d = m[:3]
            t_off = m[3] if len(m) > 3 else None
            u = ease_io(seg(tl, t0, t0 + d))
            if t_off is not None:
                u *= 1.0 - ease_io(seg(tl, t_off, t_off + 0.6)) * 0.85
            if u <= 0:
                continue
            boxes = pm[name]
            full = ease_io(seg(tl, t0, t0 + d))
            n = len(boxes)
            for i, (x0, y0, x1, y1) in enumerate(boxes):
                f = clamp(full * n - i)                              # this line's share of the stroke
                if f <= 0:
                    continue
                X0, X1 = ox + s * x0 * W0, ox + s * x1 * W0
                Y0, Y1 = oy + s * y0 * H0, oy + s * y1 * H0
                h = (Y1 - Y0)
                Y0, Y1 = Y0 + h * 0.10, Y1 - h * 0.06                # a marker sits on the x-height, not the whole box
                xe = X0 + (X1 - X0) * f
                cv2.rectangle(ink, (int(round(X0)), int(round(Y0))), (int(round(xe)), int(round(Y1))),
                              float(u * 0.8), -1, cv2.LINE_AA)
        if ink.any():
            ink = cv2.GaussianBlur(ink, (0, 0), max(1.0, s * 3.0))
            out = out * (1.0 - ink[:, :, None] * (1.0 - _HILITE)[None, None])     # multiply: print stays black under the ink
        return core.grade(out, **self.grd) if self.grd else out


class Func(Shot):
    def __init__(self, fn, desc='', source=''):
        self.fn, self.desc, self.source = fn, desc, source

    def frame(self, tl, dur, t):
        return self.fn(tl, dur, t)


class Black(Shot):
    desc = 'black'

    def frame(self, tl, dur, t):
        return core.blank()
