"""Shot types for the timeline. Every shot renders an RGB float frame for local time tl in [-pre, dur+post].

  Plate    2.5D move over Blender background/foreground plates (parallax, fog, particles, grade)
  Still    a single image (render or graphic) with a slow move
  Func     any callable fn(tl, dur) -> RGB (maps, graphics, cards)
"""
import os, json, math, functools
import numpy as np
import cv2
from . import core
from .core import ease_io, ease_io5, lerp, seg, clamp

PLATES = os.path.join(core.ROOT, 'renders/plates')


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
                 desc='', source='', post=None, fg_alpha=1.0, seed=0, fade_parts=None):
        self.name, self.s, self.c, self.p, self.ease, self.hand = name, s, c, p, ease, hand
        self.fog, self.fog2, self.dust, self.grd, self.bloom = fog, fog2, dust, grade or {}, bloom
        self.flicker, self.fg_fade, self.post, self.fg_alpha, self.seed = flicker, fg_fade, post, fg_alpha, seed
        self.fade_parts = fade_parts      # (t0, t1) film seconds: FG connected parts fade out one by one
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

        s, cx, cy = self.transform(u)
        out = core.warp(bg, M(s, cx, cy))
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


class Func(Shot):
    def __init__(self, fn, desc='', source=''):
        self.fn, self.desc, self.source = fn, desc, source

    def frame(self, tl, dur, t):
        return self.fn(tl, dur, t)


class Black(Shot):
    desc = 'black'

    def frame(self, tl, dur, t):
        return core.blank()
