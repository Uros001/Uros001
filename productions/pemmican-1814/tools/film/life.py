"""Natural motion for still plates: wind in vegetation, water ripple, drifting clouds, smoke, heat haze.

All effects work in plate space (before the camera move), driven by smooth periodic noise, so the
2.5D move and these motions combine like a real lens looking at a moving scene.
"""
import functools, math
import numpy as np
import cv2
from . import core


# ------------------------------------------------------------------ noise
@functools.lru_cache(maxsize=4)
def tile(size=512, seed=0, octaves=4, base=6):
    """Periodic smooth fbm tile in [-1, 1]."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.normal(0, 1, (n, n)).astype(np.float32)
        g = np.tile(g, (3, 3))
        big = cv2.resize(g, (size * 3, size * 3), interpolation=cv2.INTER_CUBIC)[size:2 * size, size:2 * size]
        acc += big * amp
        tot += amp
        amp *= 0.5
    acc /= tot
    return (acc / (np.abs(acc).max() + 1e-6)).astype(np.float32)


def sample(t_img, xs, ys):
    """Bilinear periodic sampling of a tile at float coords (tile pixels)."""
    s = t_img.shape[0]
    return cv2.remap(t_img, (xs % s).astype(np.float32), (ys % s).astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_WRAP)


@functools.lru_cache(maxsize=8)
def _grid(h, w):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return xs, ys


# ------------------------------------------------------------------ masks (cached per plate)
@functools.lru_cache(maxsize=8)
def texture_mask(key, img_id, lo=0.012, hi=0.05):
    """1 where the plate has fine texture (grass, leaves, fur), 0 on smooth surfaces (sky, water, hides)."""
    img = _IMGS[img_id]
    g = img[:, :, :3].mean(2) if img.ndim == 3 else img
    hp = g - cv2.GaussianBlur(g, (0, 0), 2.5)
    e = np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), 6))
    m = np.clip((e - lo) / (hi - lo), 0, 1)
    return cv2.GaussianBlur(m, (0, 0), 4).astype(np.float32)


@functools.lru_cache(maxsize=8)
def sky_mask(key, img_id):
    """Per-column sky region: from the top down to the first textured/dark pixel. Returns (mask, horizon_row)."""
    img = _IMGS[img_id]
    h, w = img.shape[:2]
    g = img[:, :, :3].mean(2)
    gx = cv2.Sobel(cv2.GaussianBlur(g, (0, 0), 1.5), cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(cv2.GaussianBlur(g, (0, 0), 1.5), cv2.CV_32F, 0, 1) ** 2
    edge = np.sqrt(gx)
    top = np.median(g[: max(4, h // 40)], axis=0)
    ok = (edge < 0.025) & (g > np.minimum(top * 0.55, 0.9)[None, :])
    ok = cv2.morphologyEx(ok.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    bad = ~ok
    first_bad = np.where(bad.any(0), bad.argmax(0), h)
    first_bad = cv2.medianBlur(first_bad.astype(np.float32).reshape(1, -1), 5).ravel()
    med = float(np.median(first_bad))
    first_bad = np.minimum(first_bad, med + 0.04 * h)        # never let the sky run down onto smooth ground
    rows = np.arange(h)[:, None]
    m = (rows < first_bad[None, :] - 2).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), 3)
    hor = float(np.median(first_bad))
    return m, hor


_IMGS = {}


def register(img):
    k = id(img)
    _IMGS[k] = img
    return k


# ------------------------------------------------------------------ effects
def _lowgrid(h, w, f=4):
    return _grid(h // f, w // f)


def _up(a, w, h):
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def wind(img, t, key, strength=1.0, y0=None, speed=0.12, gust=0.6, mask=None, seed=1, ref=None):
    """Horizontal sway of textured regions below y0 (normalized; None = detected horizon), stronger toward the bottom."""
    h, w = img.shape[:2]
    kid = register(ref if ref is not None else img)
    tm = texture_mask(key + ':tex', kid) if mask is None else mask
    if y0 is None:
        y0 = max(0.0, sky_mask(key + ':sky', kid)[1] / h - 0.02)
    lx, ly = _lowgrid(h, w)
    f = 4.0
    s = 512 / w * f
    n1 = sample(tile(512, seed, 3, 4), lx * s * 0.6 - t * speed * 512 * 0.35, ly * s * 0.6)
    n2 = sample(tile(512, seed + 1, 3, 8), lx * s * 2.0 - t * speed * 512, ly * s * 2.0 + t * 20)
    gustf = 0.5 + 0.5 * sample(tile(512, seed + 2, 2, 2), lx * s * 0.3 - t * speed * 512 * 0.2, ly * 0)
    v = np.clip((ly * f / h - y0) / (1 - y0), 0, 1) ** 1.5
    amp = strength * (w / 2304) * (1.2 + 4.0 * v) * (1 - gust + gust * gustf)
    dx = _up((0.7 * n1 + 0.5 * n2) * amp, w, h) * tm
    dy = _up(0.25 * n2 * amp, w, h) * tm
    xs, ys = _grid(h, w)
    return cv2.remap(img, xs + dx, ys + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def water(img, t, key, y0=None, strength=1.0, seed=7, ref=None):
    """Ripple distortion of smooth water below the horizon row y0 (normalized; None = detected horizon)."""
    h, w = img.shape[:2]
    kid = register(ref if ref is not None else img)
    tm = texture_mask(key + ':tex', kid)
    if y0 is None:
        y0 = sky_mask(key + ':sky', kid)[1] / h + 0.01
    lx, ly = _lowgrid(h, w, 2)
    f = 2.0
    s = 512 / w * f
    v = np.clip((ly * f / h - y0) / (1 - y0), 0, 1)
    ny = sample(tile(512, seed, 3, 10), lx * s * 1.2 + t * 6, ly * s * 3.5 - t * 18)
    nx = sample(tile(512, seed + 1, 3, 10), lx * s * 1.2 - t * 5, ly * s * 3.5 - t * 14)
    amp = strength * (w / 2304) * (0.4 + 3.2 * v ** 1.4) * (v > 0)
    damp = (1 - 0.8 * tm)
    xs, ys = _grid(h, w)
    return cv2.remap(img, xs + _up(nx * amp * 0.6, w, h) * damp, ys + _up(ny * amp, w, h) * damp, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)


@functools.lru_cache(maxsize=4)
def cloud_tex(seed=3, size=1024, cover=0.5):
    a = tile(size, seed, 6, 3)
    b = tile(size, seed + 5, 4, 6)
    # domain warp for billowy shapes
    xs, ys = _grid(size, size)
    wx = sample(b, xs + 0, ys + 0) * 40
    wy = sample(b, xs + 97, ys + 31) * 40
    d = sample(a, xs + wx, ys + wy)
    d = (d - d.min()) / (d.max() - d.min())
    return d.astype(np.float32)


@functools.lru_cache(maxsize=8)
def _sky_prep(key, kid, sun):
    img = _IMGS[kid]
    h, w = img.shape[:2]
    sm, hor = sky_mask(key, kid)
    small = cv2.resize(img[:, :, :3], (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    sky = cv2.GaussianBlur(small, (0, 0), 15)
    if sun is None:
        g = cv2.GaussianBlur(small.mean(2), (0, 0), 12) * cv2.resize(sm, (w // 2, h // 2))
        sy, sx = np.unravel_index(np.argmax(g), g.shape)
        sx, sy = sx * 2, sy * 2
    else:
        sx, sy = sun[0] * w, sun[1] * h
    return sm, hor, sky, (sx, sy)


def clouds(img, t, key, cover=0.45, opacity=0.75, speed=0.004, sun=None, seed=3, scale=1.0, tint=(1.0, 1.0, 1.0), ref=None):
    """Drifting cloud deck in perspective over the plate's sky; lit from the sun side."""
    h, w = img.shape[:2]
    kid = register(ref if ref is not None else img)
    sm, hor, sky, (sx, sy) = _sky_prep(key + ':sky', kid, sun)
    if hor < h * 0.05:
        return img
    f = 2
    lx, ly = _lowgrid(h, w, f)
    xs, ys = lx * f, ly * f
    tex = cloud_tex(seed)
    S = tex.shape[0]
    dist = np.maximum(hor - ys, 1.0)
    depth = (h * 0.5) / dist                       # distance along a horizontal cloud deck
    A = 220.0 * scale
    u = (xs - w / 2) / w * depth * A * 1.8 + t * speed * S * 6
    v = depth * A + t * speed * S * 2
    d = sample(tex, u, v)
    dens = np.clip((d - (1 - cover)) / 0.22, 0, 1) ** 1.2
    dens *= np.clip((dist - 6) / (h * 0.05), 0, 1)
    r = np.sqrt(((xs - sx) / w) ** 2 + ((ys - sy) / h) ** 2)
    lit = np.clip(sky * 1.18 + 0.05, 0, 1) * np.array(tint, np.float32)
    shade = sky * np.array([0.8, 0.82, 0.88], np.float32)
    k = np.clip(1.2 - r * 2.2, 0, 1)[:, :, None]
    dd = cv2.GaussianBlur(d, (0, 0), 2)
    rim = np.clip((d - dd) * 6 + 0.5, 0, 1)[:, :, None]
    col = shade * (1 - k * 0.6) + lit * (k * 0.6) + (lit - shade) * rim * 0.35
    a = dens * opacity
    a = _up(a, w, h) * sm
    col = _up(col, w, h)
    out = img.copy()
    out[:, :, :3] = img[:, :, :3] * (1 - a[:, :, None]) + col * a[:, :, None]
    return out


class Smoke:
    """Rising, drifting smoke from emitters given in normalized plate coords."""

    def __init__(self, emitters, seed=4, rate=6.0, rise=0.022, drift=(0.012, 0.0), size=0.012, grow=0.05,
                 life=9.0, color=(0.82, 0.83, 0.85), opacity=0.32):
        self.em, self.rate, self.rise, self.drift, self.size, self.grow, self.life = emitters, rate, rise, drift, size, grow, life
        self.color, self.opacity = np.array(color, np.float32), opacity
        rng = np.random.default_rng(seed)
        n = int(rate * life) + 1
        self.ph = rng.random((len(emitters), n)).astype(np.float32)
        self.jit = rng.normal(0, 1, (len(emitters), n, 3)).astype(np.float32)

    def draw(self, img, t):
        h, w = img.shape[:2]
        sc = 4
        lw, lh = w // sc, h // sc
        acc = np.zeros((lh, lw), np.float32)
        n = self.ph.shape[1]
        for e, (ex, ey, k) in enumerate(self.em):
            for i in range(n):
                age = ((t / self.life) + self.ph[e, i]) % 1.0 * self.life
                fa = age / self.life
                x = ex + (self.drift[0] * age + self.jit[e, i, 0] * 0.004 * age ** 0.8) * k
                y = ey - (self.rise * age ** 0.85 + self.jit[e, i, 1] * 0.002 * age) * k
                r = (self.size + self.grow * fa) * k * (1 + 0.25 * self.jit[e, i, 2])
                a = (min(1.0, age / 0.8) * (1 - fa) ** 1.6) * 0.55
                if a <= 0.005:
                    continue
                cv2.circle(acc, (int(x * lw), int(y * lh)), max(1, int(r * lw)), float(a), -1, cv2.LINE_AA)
        if acc.max() <= 0:
            return img
        acc = cv2.GaussianBlur(acc, (0, 0), 2.5)
        tex = sample(tile(512, 11, 4, 6), *[(g * (512 / lw) * 1.5) for g in _grid(lh, lw)]) * 0.5 + 0.5
        tex2 = sample(tile(512, 12, 3, 12), *[(g * (512 / lw) * 2.5 - t * 9) for g in _grid(lh, lw)]) * 0.5 + 0.5
        acc = np.clip(acc * (0.35 + 0.9 * tex * tex2), 0, 1)
        a = cv2.resize(acc, (w, h), interpolation=cv2.INTER_CUBIC)[:, :, None] * self.opacity
        out = img.copy()
        out[:, :, :3] = img[:, :, :3] * (1 - a) + self.color * a
        return out


def heat(img, t, box, strength=2.0, seed=9):
    """Shimmer above a fire: box=(x0, y0, x1, y1) normalized; stronger toward the bottom of the box."""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = (int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))
    sub = img[y0:y1, x0:x1]
    sh, sw = sub.shape[:2]
    xs, ys = _grid(sh, sw)
    s = 512 / max(sw, 1)
    n = sample(tile(512, seed, 3, 8), xs * s * 2, ys * s * 2 + t * 160)
    vx = np.sin(np.pi * xs / max(sw - 1, 1)) * (ys / max(sh - 1, 1)) ** 0.7
    dx = n * strength * vx
    out = img.copy()
    out[y0:y1, x0:x1] = cv2.remap(sub, xs + dx, ys + dx * 0.5, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


def chroma(img, amount=0.0009):
    """Lateral chromatic aberration: R scaled out, B scaled in, about the frame centre."""
    h, w = img.shape[:2]
    out = img.copy()
    for c, k in ((0, 1 + amount), (2, 1 - amount)):
        M = np.array([[k, 0, (1 - k) * w / 2], [0, k, (1 - k) * h / 2]], np.float32)
        out[:, :, c] = cv2.warpAffine(img[:, :, c], M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out
