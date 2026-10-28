"""Compositor core: timing, easing, image I/O, 2.5D parallax layers, atmosphere, grade, grain.

All frame buffers are float32 RGB in [0,1] (display-referred, sRGB-encoded), shape (H, W, 3).
Layers with alpha are (H, W, 4) straight alpha.
"""
import os, json, math, functools
import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H, FPS = 1920, 1080, 30


def set_size(w, h):
    global W, H
    W, H = w, h


# ------------------------------------------------------------------ timing
@functools.lru_cache(maxsize=1)
def timing():
    return json.load(open(os.path.join(ROOT, 'audio/narration/timing.json')))


def anchor(a):
    """Resolve an anchor to film seconds.

    'P07'        -> paragraph start      'P07.e' -> paragraph end
    'P07.2'      -> sentence 2 start     'P07.2e' -> sentence 2 end
    'TITLE', 'CH2', 'CREDITS' (+'.e')    float -> as is
    'P07.2+1.5'  -> with offset
    """
    if isinstance(a, (int, float)):
        return float(a)
    off = 0.0
    for sep in ('+', '-'):
        if sep in a[1:]:
            i = a.rindex(sep)
            off = float(a[i:])
            a = a[:i]
            break
    t = timing()
    end = a.endswith('e') and (a.endswith('.e') or a[-2].isdigit())
    key = a[:-1].rstrip('.') if end else a
    if key.startswith('P') and '.' in key:
        pid, idx = key.split('.')
        s = next(x for x in t['sentences'] if x['pid'] == pid and x['idx'] == int(idx))
        return (s['end'] if end else s['start']) + off
    if key.startswith('P'):
        p = next(x for x in t['paragraphs'] if x['pid'] == key)
        return (p['end'] if end else p['start']) + off
    if key == 'CREDITS':
        c = t['credits']
        return (c['end'] if end else c['start']) + off
    if key == 'END':
        return t['total'] + off
    i = next(x for x in t['inserts'] if x['kind'] == key)
    return (i['end'] if end else i['start']) + off


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_io(x):           # smooth in-out (cubic)
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_io5(x):          # smoother (quintic)
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def ease_out(x, p=3):
    x = clamp(x)
    return 1 - (1 - x) ** p


def ease_in(x, p=2):
    x = clamp(x)
    return x ** p


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, t0, t1):
    """Normalized progress of t within [t0, t1]."""
    if t1 <= t0:
        return 1.0
    return clamp((t - t0) / (t1 - t0))


# ------------------------------------------------------------------ image I/O
@functools.lru_cache(maxsize=64)
def load_image(path, scale_to=None):
    """Load PNG/JPG as float32 RGB(A) in [0,1]. Cached."""
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(path)
    if im.dtype == np.uint16:
        im = im.astype(np.float32) / 65535.0
    else:
        im = im.astype(np.float32) / 255.0
    if im.ndim == 2:
        im = np.dstack([im] * 3)
    if im.shape[2] == 4:
        im = im[:, :, [2, 1, 0, 3]]
    else:
        im = im[:, :, ::-1]
    if scale_to:
        im = cv2.resize(im, scale_to, interpolation=cv2.INTER_AREA)
    return np.ascontiguousarray(im)


def blank(color=(0, 0, 0)):
    f = np.empty((H, W, 3), np.float32)
    f[:] = color
    return f


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ------------------------------------------------------------------ transforms
def affine(scale, cx, cy, tx=0.0, ty=0.0, rot=0.0, src_w=None, src_h=None):
    """Matrix mapping source image -> output frame.

    The source is first fitted to cover the frame, then scaled by `scale` about the
    normalized source point (cx, cy), which lands at frame centre + (tx, ty) (normalized).
    """
    sw, sh = src_w or W, src_h or H
    cover = max(W / sw, H / sh)
    s = cover * scale
    ox, oy = cx * sw, cy * sh
    a = math.radians(rot)
    ca, sa = math.cos(a) * s, math.sin(a) * s
    px, py = W * (0.5 + tx), H * (0.5 + ty)
    return np.array([[ca, -sa, px - (ca * ox - sa * oy)], [sa, ca, py - (sa * ox + ca * oy)]], np.float32)


def warp(img, M, border=cv2.BORDER_REFLECT):
    flags = cv2.INTER_LINEAR if abs(M[0, 0]) >= 0.999 else cv2.INTER_AREA
    if abs(M[0, 0]) > 1.0:
        flags = cv2.INTER_CUBIC
    return cv2.warpAffine(img, M, (W, H), flags=flags, borderMode=border)


def over(dst, src_rgba, opacity=1.0):
    """Alpha-over straight-alpha RGBA onto RGB."""
    a = src_rgba[:, :, 3:4] * opacity
    dst *= (1 - a)
    dst += src_rgba[:, :, :3] * a
    return dst


# ------------------------------------------------------------------ atmosphere
@functools.lru_cache(maxsize=8)
def _fbm_tile(size, seed, octaves=5):
    rng = np.random.default_rng(seed)
    acc = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = 4 * 2 ** o
        g = rng.random((n, n)).astype(np.float32)
        g = cv2.resize(np.tile(g, (2, 2)), (size * 2, size * 2), interpolation=cv2.INTER_CUBIC)[:size, :size]
        acc += g * amp
        tot += amp
        amp *= 0.55
    acc /= tot
    acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)
    return acc


def fog_layer(t, density=0.35, speed=(0.012, 0.002), scale=1.0, seed=3, color=(0.75, 0.78, 0.8),
              band=(0.35, 0.8), soft=0.25):
    """Drifting fog wisps as RGBA (straight alpha). `band` = vertical extent (0 top..1 bottom)."""
    tile = _fbm_tile(1024, seed)
    tw = int(W * 1.5 * scale)
    th = int(H * 1.5 * scale)
    big = cv2.resize(tile, (tw, th), interpolation=cv2.INTER_LINEAR)
    ox = int((t * speed[0] * W) % (tw - W)) if tw > W else 0
    oy = int((t * speed[1] * H) % (th - H)) if th > H else 0
    n = big[oy:oy + H, ox:ox + W]
    n = np.clip((n - (1 - density)) / max(soft, 1e-3), 0, 1)
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    m = np.clip((y - band[0]) / 0.15, 0, 1) * np.clip((band[1] - y) / 0.15, 0, 1)
    a = (n * m * 0.85).astype(np.float32)
    out = np.empty((H, W, 4), np.float32)
    out[:, :, :3] = color
    out[:, :, 3] = a
    return out


class Particles:
    """Deterministic 2D particle field (dust motes, snow, embers) with depth-based parallax."""

    def __init__(self, n=300, seed=1, kind='dust'):
        rng = np.random.default_rng(seed)
        self.p = rng.random((n, 2)).astype(np.float32)
        self.z = rng.uniform(0.2, 1.0, n).astype(np.float32)
        self.ph = rng.uniform(0, 6.283, n).astype(np.float32)
        self.kind = kind

    def draw(self, frame, t, color=(1, 0.95, 0.85), opacity=0.6, drift=(0.004, -0.002), size=2.0,
             mask=None, fall=0.0, sway=0.004):
        x = (self.p[:, 0] + t * drift[0] * self.z + np.sin(t * 0.7 + self.ph) * sway) % 1.0
        y = (self.p[:, 1] + t * (drift[1] + fall) * self.z + np.cos(t * 0.5 + self.ph) * sway * 0.5) % 1.0
        layer = np.zeros((H, W), np.float32)
        xs = (x * W).astype(np.int32)
        ys = (y * H).astype(np.int32)
        r = np.maximum(1, (size * self.z * (W / 1920)).astype(np.int32))
        tw = 0.6 + 0.4 * np.sin(t * 2.0 + self.ph * 3)
        for xi, yi, ri, zi, ti in zip(xs, ys, r, self.z, tw):
            cv2.circle(layer, (int(xi), int(yi)), int(ri), float(zi * ti), -1, lineType=cv2.LINE_AA)
        layer = cv2.GaussianBlur(layer, (0, 0), 1.2)
        if mask is not None:
            layer *= mask
        a = np.clip(layer * opacity, 0, 1)[:, :, None]
        frame *= (1 - a)
        frame += np.array(color, np.float32) * a
        return frame


# ------------------------------------------------------------------ grade / finish
def grade(img, lift=0.0, gamma=1.0, gain=1.0, sat=1.0, temp=0.0, tint=0.0, contrast=1.0, pivot=0.45):
    out = img
    if temp or tint:
        out = out * np.array([1 + temp * 0.06 + tint * 0.02, 1 - tint * 0.04, 1 - temp * 0.06 + tint * 0.02], np.float32)
    if contrast != 1.0:
        out = (out - pivot) * contrast + pivot
    if lift or gain != 1.0:
        out = out * (gain - lift) + lift
    if gamma != 1.0:
        out = np.power(np.clip(out, 0, None), 1.0 / gamma)
    if sat != 1.0:
        l = (out * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
        out = l + (out - l) * sat
    return np.clip(out, 0, 1).astype(np.float32)


def bloom(img, threshold=0.78, strength=0.25, radius=24):
    hi = np.clip(img - threshold, 0, None)
    small = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), radius / 4)
    hb = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
    return np.clip(img + hb * strength, 0, 1)


@functools.lru_cache(maxsize=1)
def _vignette():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (x - W / 2) / (W / 2), (y - H / 2) / (H / 2)
    r = np.sqrt(nx ** 2 * 0.8 + ny ** 2)
    return np.clip(1 - 0.28 * np.clip(r - 0.45, 0, None) ** 1.6, 0, 1)[:, :, None].astype(np.float32)


@functools.lru_cache(maxsize=1)
def _grain_bank():
    rng = np.random.default_rng(7)
    bank = []
    for i in range(24):
        g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        g = cv2.GaussianBlur(g, (0, 0), 0.6)
        bank.append(g)
    return bank


def finish(img, frame_idx, grain=0.022, vignette=True):
    out = img
    if vignette:
        out = out * _vignette()
    if grain:
        g = _grain_bank()[frame_idx % 24]
        lum = (out * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1)
        w = (grain * (0.35 + 0.65 * (1 - np.abs(lum - 0.45) * 1.6))).clip(0.004, None)
        out = out + (g * w)[:, :, None]
    return np.clip(out, 0, 1)


def to_u8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
