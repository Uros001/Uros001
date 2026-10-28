"""Motion graphics: cards, diagrams, counters. Each scene is fn(tl, dur, t) -> RGB float frame.

All numbers shown on screen come from research/FACT_CHECK.md (row ids noted inline).
"""
import os, math, functools
import numpy as np
import cv2
import skia
from . import core, text as T
from .core import ease_out, ease_io, ease_io5, seg, clamp, lerp, anchor
from .text import Layer, font, INK, INK_DIM, OCHRE, STEEL, RUST, DARK, fade_window, reveal_words

PLATES = os.path.join(core.ROOT, 'renders/plates')


# ------------------------------------------------------------------ backgrounds
@functools.lru_cache(maxsize=2)
def _dark_tex(seed=3):
    rng = np.random.default_rng(seed)
    W, H = core.W, core.H
    img = np.empty((H, W, 3), np.float32)
    img[:] = core.hexc('#14120f')
    for s, a in ((360, 0.035), (120, 0.02), (6, 0.012)):
        n = rng.normal(0, 1, (H // s + 3, W // s + 3)).astype(np.float32)
        n = cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)
        img += n[:, :, None] * a * np.array([1.0, 0.9, 0.75], np.float32)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 * 0.7 + ((y - H / 2) / (H / 2)) ** 2)
    img *= np.clip(1.15 - 0.45 * r, 0, 1)[:, :, None]
    return np.clip(img, 0, 1)


def bg_dark(t, fog=0.10):
    out = _dark_tex().copy()
    if fog:
        out = core.over(out, core.fog_layer(t, density=0.3, speed=(0.004, 0.001), color=(0.55, 0.5, 0.42),
                                            band=(0.0, 1.0), soft=0.4), fog)
    return out


@functools.lru_cache(maxsize=6)
def _plate_comp(name, blur):
    if not os.path.exists(os.path.join(PLATES, name + '_bg.png')):
        return np.full((1296, 2304, 3), 0.15, np.float32)
    bg = core.load_image.__wrapped__(os.path.join(PLATES, name + '_bg.png'))
    fgp = os.path.join(PLATES, name + '_fg.png')
    img = bg.copy()
    if os.path.exists(fgp):
        fg = core.load_image.__wrapped__(fgp)
        img = img * (1 - fg[:, :, 3:4]) + fg[:, :, :3] * fg[:, :, 3:4]
    if blur:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    return np.ascontiguousarray(img.astype(np.float32))


def bg_plate(name, tl, dur, blur=14, dim=0.42, s=(1.04, 1.1), c=(0.5, 0.5), sat=0.7):
    from .shots import ACCESSED
    ACCESSED.add(name)
    img = _plate_comp(name, blur)
    sh, sw = img.shape[:2]
    e = ease_io(seg(tl, 0, dur))
    sc = s[0] * (s[1] / s[0]) ** e
    out = core.warp(img, core.affine(sc, c[0], c[1], src_w=sw, src_h=sh))
    out = core.grade(out, sat=sat, gain=dim)
    return out


_LIVE = {}


def bg_live(name, tl, dur, t, dim=0.5, s=(1.0, 1.07), c=((0.5, 0.5), (0.5, 0.5)), band=0.35):
    """The real moving 3D shot (parallax + natural motion), dimmed with a soft centre band for legible text."""
    from . import edl
    key = (name, s, c)
    if key not in _LIVE:
        _LIVE[key] = edl.P(name, s=s, c=c)
    img = _LIVE[key].frame(tl, dur, t)
    y = np.linspace(-1, 1, core.H, dtype=np.float32)[:, None]
    x = np.linspace(-1, 1, core.W, dtype=np.float32)[None, :]
    centre = np.exp(-(y ** 2) / 0.5 - (x ** 2) / 1.6)
    g = dim * (1 - band * centre)
    return np.clip(img * g[:, :, None], 0, 1).astype(np.float32)


def comp(bg, L):
    return core.over(bg, L.rgba())


def _leader(L, x0, y0, x1, y1, a, col=INK_DIM):
    L.line(x0, y0, x1, y1, col, 0.7 * a, 1.4)
    L.circle(x0, y0, 4, col, a)


# ------------------------------------------------------------------ cards
def title_card(tl, dur, t):
    out = bg_live('dock_D4', tl, dur, t, dim=0.5, s=(1.12, 1.04))
    L = Layer()
    a = fade_window(tl, 0.0, dur, 1.2, 1.0)
    k = ease_out(seg(tl, 0.3, 2.6), 4)
    trk = lerp(34, 16, k)
    f = font('serif', 124, 500)
    L.text('THE PEMMICAN WAR', 960, 560, f, INK, a * ease_out(seg(tl, 0.2, 1.6)), align='center', tracking=trk)
    w = 520 * ease_io(seg(tl, 0.9, 2.6))
    L.line(960 - w, 448, 960 + w, 448, OCHRE, 0.75 * a, 1.6)
    L.line(960 - w, 622, 960 + w, 622, OCHRE, 0.75 * a, 1.6)
    L.text('RED RIVER  ·  1812 – 1821', 960, 680, font('sans', 22, 600), INK_DIM, a * ease_out(seg(tl, 1.8, 3.0)),
           align='center', tracking=8)
    return comp(out, L)


def chapter(num, title, plate=None):
    def fn(tl, dur, t):
        out = bg_live(plate, tl, dur, t, dim=0.42, s=(1.04, 1.1)) if plate else bg_dark(t, 0.14)
        L = Layer()
        T.chapter_card(L, tl, 0.0, dur, num, title)
        return comp(out, L)
    return fn


def not_move(tl, dur, t):
    """P03: 'Not illegal to eat. / Illegal to move.'"""
    out = bg_dark(t, 0.1)
    L = Layer()
    t1 = anchor('P03.0') - 0.25
    t2 = anchor('P03.1') - 0.2
    end = t - tl + dur
    a1 = fade_window(t, t1, end, 0.5, 0.7)
    L.text('Not illegal to eat.', 960, 470, font('serif_i', 70, 500), INK_DIM, a1, align='center')
    a2 = fade_window(t, t2, end, 0.35, 0.7)
    k = ease_out(seg(t, t2, t2 + 0.9))
    L.text('ILLEGAL TO MOVE.', 960, 620, font('serif', 104, 600), RUST, a2, align='center', tracking=lerp(22, 10, k))
    return comp(out, L)


def word_card(tl, dur, t):
    """P07.3 (A3): the English word comes from Cree pimîhkân, built on pimiy, 'fat, grease'."""
    out = bg_live('camp_R1', tl, dur, t, dim=0.38, s=(1.15, 1.22))
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.8)
    k = ease_out(seg(tl, 0.2, 1.6))
    L.text('CREE', 960, 360, font('sans', 24, 700), OCHRE, a * k, align='center', tracking=10)
    L.text('pimîhkân', 960, 560, font('serif_i', 150, 500), INK, a * k, align='center')
    k2 = ease_out(seg(tl, 1.6, 2.8))
    L.line(760, 620, 1160, 620, OCHRE, a * 0.6 * k2, 1.4)
    L.text('built on  pimiy  —  fat, grease', 960, 700, font('serif_i', 46, 500), INK_DIM, a * k2, align='center')
    return comp(out, L)


def credits(tl, dur, t):
    out = bg_dark(t, 0.08)
    L = Layer()
    pages = [
        (0.0, 7.6, [('LOST TRIBE KNOWLEDGE', 'serif', 64, INK, 10),
                    ('The Pemmican War', 'serif_i', 40, OCHRE, 0),
                    ('', 'sans', 10, INK, 0),
                    ('Narration: synthetic voice (Kokoro-82M, Apache-2.0); not a human recording', 'sans', 22, INK_DIM, 1),
                    ('3D scenes: original Blender reconstructions — illustrative, not historical records', 'sans', 22, INK_DIM, 1),
                    ('Documents on screen are generated props, not facsimiles', 'sans', 22, INK_DIM, 1)]),
        (7.6, dur, [('Maps: Natural Earth (public domain); relief: NASA/NOAA via basemap (public domain)', 'sans', 22, INK_DIM, 1),
                    ('Music: original score built from VSCO 2 Community Edition samples (CC0), Versilian Studios', 'sans', 22, INK_DIM, 1),
                    ('Upright piano samples: Simon Dalzell, Ivy Audio', 'sans', 22, INK_DIM, 1),
                    ('Sound effects: synthesized for this film', 'sans', 22, INK_DIM, 1),
                    ('', 'sans', 10, INK, 0),
                    ('Sources and corrections: see the video description', 'sans', 24, INK, 2),
                    ('Pemmican is living knowledge of the Plains nations and the Métis.', 'serif_i', 34, OCHRE, 0)]),
    ]
    for t0, t1, lines in pages:
        a = fade_window(tl, t0, t1, 0.9, 0.9)
        if a <= 0:
            continue
        y = 360 if t0 == 0 else 380
        for txt, face, size, col, trk in lines:
            if txt:
                L.text(txt, 960, y, font(face, size, 600 if face == 'serif' else 500), col, a, align='center', tracking=trk)
            y += size * 1.9
    return comp(out, L)


# ------------------------------------------------------------------ chapter I diagrams
def water(tl, dur, t):
    """P06: fresh meat is mostly water (about three-quarters; standard food composition)."""
    out = bg_live('camp_R2', tl, dur, t, dim=0.45)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.7)
    L.text('FRESH LEAN MEAT', 960, 250, font('sans', 24, 600), INK, a, align='center', tracking=8)
    n = 10
    size, gap = 44, 8
    x0 = 960 - (n * size + (n - 1) * gap) / 2
    y0 = 300
    fill = ease_io(seg(tl, 0.8, 3.8)) * 74
    for j in range(n):
        for i in range(n):
            idx = (n - 1 - j) * n + i         # fill from the bottom up
            col = '#7a2c22'
            if idx < fill:
                col = '#4e7d98'
            L.rect(x0 + i * (size + gap), y0 + j * (size + gap), size, size, col, a * 0.92, radius=4)
    ka = a * ease_out(seg(tl, 3.0, 4.0))
    L.text('about three-quarters water', 960, y0 + n * (size + gap) + 60, font('serif_i', 44, 500), STEEL, ka, align='center')
    L.text('Typical composition of raw lean meat', 960, 1010, font('sans', 18, 400), INK_DIM, ka * 0.8, align='center', tracking=1)
    return comp(out, L)


def steps(tl, dur, t):
    """P10.0–P10.1: every step had a job."""
    out = bg_live('camp_K1', tl, dur, t, dim=0.38)
    L = Layer()
    items = [('DRY', 'removes the water', 'microbes need'), ('POUND', 'breaks it down', 'to pack densely'),
             ('FAT', 'adds energy and', 'shuts out air'), ('SEW', 'a greased hide bag', 'seals the load')]
    for i, (h, l1, l2) in enumerate(items):
        x = 960 + (i - 1.5) * 380
        a = fade_window(tl, 0.25 + i * 0.35, dur, 0.6, 0.7)
        hl = 1.0 if i == 0 and tl > anchor('P10.1') - (t - tl) else 0.0
        col = OCHRE if (i == 0 and hl) else INK
        L.circle(x, 470, 76, OCHRE if i == 0 and hl else INK_DIM, a * 0.85, stroke=2)
        L.text(f'{i + 1}', x, 495, font('serif', 64, 500), col, a, align='center')
        L.text(h, x, 620, font('sans', 30, 700), col, a, align='center', tracking=6)
        L.text(l1, x, 670, font('serif_i', 30, 500), INK_DIM, a, align='center')
        L.text(l2, x, 708, font('serif_i', 30, 500), INK_DIM, a, align='center')
        if i < 3:
            L.line(x + 100, 470, x + 280, 470, INK_DIM, a * 0.5, 1.5, dash=(6, 6))
    return comp(out, L)


def ratio(tl, dur, t):
    """P10.2 (A7): 5–6 lb fresh lean meat -> 1 lb dried, pounded meat."""
    out = bg_live('camp_R2', tl, dur, t, dim=0.38, s=(1.12, 1.2))
    L = Layer()
    a = fade_window(tl, 0, dur, 0.5, 0.7)
    for i in range(6):
        r, c = divmod(i, 3)
        k = ease_out(seg(tl, 0.2 + i * 0.18, 0.8 + i * 0.18))
        alpha = a * k * (0.45 if i == 5 else 1.0)
        L.rect(420 + c * 130, 400 + r * 130, 112, 112, '#8a3326', alpha, radius=10)
        L.text('1 lb', 476 + c * 130, 468 + r * 130, font('sans', 22, 600), INK, alpha, align='center')
    L.text('5–6 lb', 616, 720, font('serif', 64, 600), INK, a, align='center')
    L.text('fresh lean meat', 616, 770, font('serif_i', 34, 500), INK_DIM, a, align='center')
    ka = ease_io(seg(tl, 2.2, 3.6))
    L.line(880, 520, 880 + 230 * ka, 520, OCHRE, a * 0.9, 3)
    if ka > 0.95:
        L.line(1110, 520, 1090, 505, OCHRE, a * 0.9, 3)
        L.line(1110, 520, 1090, 535, OCHRE, a * 0.9, 3)
    kb = ease_out(seg(tl, 3.4, 4.4))
    L.rect(1250, 470, 100, 100, '#4b3021', a * kb, radius=10)
    L.text('1 lb', 1300, 530, font('sans', 22, 600), INK, a * kb, align='center')
    L.text('1 lb', 1300, 720, font('serif', 64, 600), OCHRE, a * kb, align='center')
    L.text('dried, pounded meat', 1300, 770, font('serif_i', 34, 500), INK_DIM, a * kb, align='center')
    L.text('Ratios reported in fur-trade era accounts', 960, 1010, font('sans', 18, 400), INK_DIM, a * 0.8 * kb, align='center')
    return comp(out, L)


def energy(tl, dur, t):
    """P11.1 (A10): fat ~9 kcal/g vs protein ~4 kcal/g."""
    out = bg_live('camp_K2', tl, dur, t, dim=0.42)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.5, 0.7)
    L.text('ENERGY PER GRAM', 960, 330, font('sans', 24, 600), INK, a, align='center', tracking=8)
    rows = [('FAT', 9, OCHRE, 0.4), ('PROTEIN', 4, '#a0533f', 0.9)]
    for i, (lab, v, col, d) in enumerate(rows):
        y = 430 + i * 150
        k = ease_out(seg(tl, d, d + 1.6))
        L.text(lab, 560, y + 52, font('sans', 26, 700), INK, a, align='right', tracking=4)
        L.rect(600, y, 90 * v * k, 76, col, a * 0.92, radius=6)
        L.text(f'≈ {v} kcal', 600 + 90 * v * k + 24, y + 54, font('serif', 46, 600), INK, a * k)
    L.text('Standard nutrition values (Atwater factors)', 960, 1010, font('sans', 18, 400), INK_DIM, a * 0.8, align='center')
    return comp(out, L)


def _flecks(n, seed, box):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = box
    return np.c_[rng.uniform(x0, x1, n), rng.uniform(y0, y1, n), rng.uniform(5, 15, n), rng.uniform(2, 5, n),
                 rng.uniform(0, 180, n), rng.uniform(0, 1, n)]


def section(tl, dur, t):
    """P11.2–P11.3: cutaway of a filled bag (diagram, not to scale)."""
    out = bg_dark(t, 0.08)
    L = Layer()
    s = core.W / 1920
    a = fade_window(tl, 0, dur, 0.5, 0.8)
    bx, by, bw, bh = 560, 330, 800, 420
    c = L.c
    # bag wall (rawhide) with hair fringe
    wall = skia.Paint(AntiAlias=True, Color4f=T.color('#6e4f31', a))
    c.drawRoundRect(skia.Rect.MakeXYWH(bx * s, by * s, bw * s, bh * s), 70 * s, 70 * s, wall)
    rng = np.random.default_rng(4)
    hp = skia.Paint(AntiAlias=True, Color4f=T.color('#2d2016', a * 0.9), StrokeWidth=1.6 * s, Style=skia.Paint.kStroke_Style)
    for k in range(700):
        u = k / 700
        per = 2 * (bw + bh)
        d = u * per
        if d < bw:
            px, py, nx, ny = bx + d, by, 0, -1
        elif d < bw + bh:
            px, py, nx, ny = bx + bw, by + d - bw, 1, 0
        elif d < 2 * bw + bh:
            px, py, nx, ny = bx + bw - (d - bw - bh), by + bh, 0, 1
        else:
            px, py, nx, ny = bx, by + bh - (d - 2 * bw - bh), -1, 0
        if (px - bx < 60 or bx + bw - px < 60) and (py - by < 60 or by + bh - py < 60):
            continue
        L_ = rng.uniform(8, 18)
        c.drawLine(px * s, py * s, (px + nx * L_ + rng.uniform(-6, 6)) * s, (py + ny * L_ + rng.uniform(-6, 6)) * s, hp)
    # interior: fat matrix fills from the bottom, fibres visible first
    ib = (bx + 26, by + 26, bx + bw - 26, by + bh - 26)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(*(v * s for v in ib)), 50 * s, 50 * s), doAntiAlias=True)
    c.drawRect(skia.Rect.MakeLTRB(*(v * s for v in ib)), skia.Paint(Color4f=T.color('#2a1d14', a)))
    kf = ease_io(seg(tl, 0.6, 2.6))
    fy = ib[3] - (ib[3] - ib[1]) * kf
    c.drawRect(skia.Rect.MakeLTRB(ib[0] * s, fy * s, ib[2] * s, ib[3] * s), skia.Paint(Color4f=T.color('#cdb98a', a * 0.95)))
    fl = _flecks(1600, 9, ib)
    fp = skia.Paint(AntiAlias=True)
    for x, y, w, h, r, v in fl:
        col = '#5a3622' if v < 0.6 else '#74472c'
        fp.setColor4f(T.color(col, a * ease_out(seg(tl, 0.0 + v * 0.5, 0.6 + v * 0.5))))
        c.save(); c.translate(x * s, y * s); c.rotate(r)
        c.drawOval(skia.Rect.MakeXYWH(-w * s / 2, -h * s / 2, w * s, h * s), fp)
        c.restore()
    c.restore()
    # greased seam along the top: lacing
    kg = ease_out(seg(t, anchor('P11.3') - 0.3, anchor('P11.3') + 1.0))
    for i in range(14):
        x = bx + 120 + i * 40
        L.line(x, by - 14, x + 22, by + 20, '#3b2717', a, 5)
    L.rect(bx + 100, by - 20, 600, 46, '#f2d38a', a * 0.28 * kg, radius=20)
    # labels
    k1 = fade_window(tl, 1.0, dur, 0.6, 0.7)
    _leader(L, 760, 470, 470, 260, k1 * a)
    L.text('dried, pounded meat', 460, 248, font('serif_i', 34, 500), INK, k1 * a, align='right')
    k2 = fade_window(tl, 2.2, dur, 0.6, 0.7)
    _leader(L, 1180, 640, 1460, 820, k2 * a)
    L.text('rendered fat fills the gaps', 1470, 834, font('serif_i', 34, 500), INK, k2 * a)
    k3 = fade_window(t, anchor('P11.3') - 0.2, t - tl + dur, 0.6, 0.7)
    _leader(L, 1200, 320, 1470, 230, k3 * a)
    L.text('rawhide, seams sealed with grease', 1480, 220, font('serif_i', 34, 500), INK, k3 * a)
    L.text('Diagram, not to scale', 960, 1010, font('sans', 18, 400), INK_DIM, a * 0.7, align='center')
    return comp(out, L)


# ------------------------------------------------------------------ chapter II
def cargo(tl, dur, t):
    """P15.2: every pound of food displaced a pound of cargo."""
    out = bg_live('dock_C1', tl, dur, t, dim=0.45)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.5, 0.7)
    L.text('ONE CANOE, ONE LOAD', 960, 360, font('sans', 24, 600), INK, a, align='center', tracking=8)
    x0, w, y = 360, 1200, 450
    L.rect(x0 - 6, y - 6, w + 12, 112, INK_DIM, a * 0.6, radius=10, stroke=2)
    k = ease_io(seg(tl, 0.8, 3.2)) * 0.42
    L.rect(x0, y, w * k, 100, OCHRE, a * 0.9, radius=6)
    L.rect(x0 + w * k, y, w * (1 - k), 100, STEEL, a * 0.7, radius=6)
    if k > 0.08:
        L.text('FOOD', x0 + w * k / 2, y + 62, font('sans', 26, 700), DARK, a, align='center', tracking=4)
    L.text('TRADE GOODS  ·  FURS', x0 + w * k + w * (1 - k) / 2, y + 62, font('sans', 26, 700), DARK, a, align='center', tracking=4)
    L.text('Every pound of food was a pound of cargo left behind.', 960, 680, font('serif_i', 40, 500), INK, a * ease_out(seg(tl, 2.0, 3.0)), align='center')
    return comp(out, L)


def ration(tl, dur, t):
    """P16.1 (A11): about two pounds a day."""
    out = bg_live('dock_C3b', tl, dur, t, dim=0.42)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.5, 0.7)
    k = ease_out(seg(tl, 0.3, 1.4))
    L.text('≈ 2 lb', 960, 560, font('serif', 190, 600), OCHRE, a * k, align='center')
    L.text('of pemmican a day for a working man', 960, 650, font('serif_i', 42, 500), INK, a * ease_out(seg(tl, 0.9, 1.9)), align='center')
    L.text('Fur-trade reckoning; actual rations varied', 960, 1010, font('sans', 18, 400), INK_DIM, a * 0.8, align='center')
    return comp(out, L)


def depot_math(tl, dur, t):
    """P16.4–P16.5 (B3): about four 90-lb bags per canoe at a depot; next depot hundreds of miles on."""
    out = bg_live('dock_C2', tl, dur, t, dim=0.4)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.5, 0.7)
    L.text('ONE NORTHERN CANOE', 960, 250, font('sans', 24, 600), INK, a, align='center', tracking=8)
    L.text('crew of six  ·  perhaps 35 miles a day', 960, 305, font('serif_i', 36, 500), INK_DIM,
           a * ease_out(seg(t, anchor('P16.4') - 0.2, anchor('P16.4') + 1.0)), align='center')
    for i in range(4):
        k = ease_out(seg(tl, 1.4 + i * 0.35, 2.0 + i * 0.35))
        x = 610 + i * 190
        L.rect(x, 420 - 30 * (1 - k), 150, 92, '#6e4f31', a * k, radius=22)
        for j in range(5):
            L.line(x + 30 + j * 22, 420 - 30 * (1 - k) + 6, x + 42 + j * 22, 420 - 30 * (1 - k) + 22, '#2d2016', a * k, 3)
        L.text('90 lb', x + 75, 560, font('sans', 24, 600), INK, a * k, align='center')
    k2 = ease_out(seg(tl, 3.2, 4.2))
    L.text('4 × 90 lb = 360 lb', 960, 680, font('serif', 64, 600), OCHRE, a * k2, align='center')
    k3 = fade_window(t, anchor('P16.5') - 0.1, t - tl + dur, 0.6, 0.7)
    L.text('→  enough to reach the next depot, hundreds of miles on', 960, 770, font('serif_i', 38, 500), INK, a * k3, align='center')
    return comp(out, L)


# ------------------------------------------------------------------ chapter III
def order_terms(tl, dur, t):
    """P22 (C4): paraphrased main terms of Macdonell's 8 January 1814 order. Not the original text."""
    out = bg_live('desk_W1', tl, dur, t, dim=0.32)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.8)
    L.text('THE ORDER OF 8 JANUARY 1814', 960, 230, font('sans', 26, 700), INK, a, align='center', tracking=8)
    L.text('its main terms, paraphrased — not the original wording', 960, 280, font('serif_i', 30, 500), INK_DIM, a, align='center')
    L.line(660, 320, 1260, 320, OCHRE, a * 0.7, 1.5)
    lines = [('P22.1', 'For one year, no provisions gathered in Assiniboia', 'may be taken out of it'),
             ('P22.2', 'Meat  ·  fish  ·  grain  ·  vegetables', None),
             ('P22.3', 'Traders may keep what they need to reach their posts,', 'under licence from the governor'),
             ('P22.4', 'Anything else may be seized — and will be paid for', None)]
    y = 410
    for anc, l1, l2 in lines:
        k = fade_window(t, anchor(anc) - 0.15, t - tl + dur, 0.6, 0.8)
        hl = 1.0 if anchor(anc) - 0.15 <= t < anchor(anc) + 4.0 else 0.6
        L.text(l1, 960, y, font('serif', 44, 500), INK, a * k * hl + a * k * (1 - hl) * 0.75, align='center')
        if l2:
            L.text(l2, 960, y + 50, font('serif', 44, 500), INK, a * k * hl + a * k * (1 - hl) * 0.75, align='center')
            y += 50
        y += 105
    return comp(out, L)


def paper_practice(tl, dur, t):
    """P23: on paper vs in practice."""
    out = bg_live('fort_F2', tl, dur, t, dim=0.36)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.5, 0.8)
    end = t - tl + dur
    k1 = fade_window(t, anchor('P23.0') - 0.2, end, 0.6, 0.8)
    L.text('ON PAPER', 560, 330, font('sans', 26, 700), INK_DIM, a * k1, align='center', tracking=8)
    L.text('food for a', 560, 430, font('serif_i', 46, 500), INK, a * k1, align='center')
    L.text('hungry colony', 560, 485, font('serif_i', 46, 500), INK, a * k1, align='center')
    k2 = fade_window(t, anchor('P23.1') - 0.2, end, 0.6, 0.8)
    L.text('IN PRACTICE', 1360, 330, font('sans', 26, 700), OCHRE, a * k2, align='center', tracking=8)
    L.text("the North West Company's fuel", 1360, 430, font('serif_i', 46, 500), INK, a * k2, align='center')
    k3 = fade_window(t, anchor('P23.1') + 4.5, end, 0.6, 0.8)
    L.text('the Métis families’ living', 1360, 485, font('serif_i', 46, 500), INK, a * k3, align='center')
    L.line(960, 290, 960, 560, INK_DIM, a * 0.5, 1.5)
    k4 = fade_window(t, anchor('P23.3') - 0.1, end, 0.6, 0.8)
    L.text('Both can be true at once.', 960, 720, font('serif', 56, 600), OCHRE, a * k4, align='center')
    return comp(out, L)


def bags479(tl, dur, t):
    """P24.2–P24.3 (C6): 479 bags of pemmican; 479 × 90 lb ≈ 43,000 lb."""
    out = bg_live('store_S1', tl, dur, t, dim=0.36)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.5, 0.8)
    L.text('SEIZED AT THE SOURIS RIVER POST, 1814', 960, 170, font('sans', 24, 700), INK, a, align='center', tracking=6)
    cols, n = 30, 479
    w, h, gx, gy = 34, 21, 40, 27
    x0 = 960 - (cols * gx) / 2 + 3
    y0 = 230
    t0 = anchor('P24.2')
    k = ease_io(seg(t, t0, t0 + 4.2))
    shown = int(n * k)
    for i in range(shown):
        r, cidx = divmod(i, cols)
        L.rect(x0 + cidx * gx, y0 + r * gy, w, h, '#7a5636', a * 0.95, radius=6)
    L.text(f'{shown:,}', 960, 760, font('serif', 96, 600), OCHRE, a * (1 if shown else 0), align='center')
    L.text('bags of pemmican', 960, 815, font('serif_i', 38, 500), INK, a * (1 if shown else 0), align='center')
    k2 = fade_window(t, anchor('P24.3') - 0.2, t - tl + dur, 0.6, 0.8)
    L.text('479 × 90 lb  ≈  43,000 lb of food', 960, 905, font('serif', 48, 600), INK, a * k2, align='center')
    L.text('plus kegs of fat and bundles of dried meat', 960, 958, font('serif_i', 30, 500), INK_DIM, a * k2, align='center')
    return comp(out, L)


# ------------------------------------------------------------------ chapter IV
TIMELINE = [  # (year position, label line 1, line 2, anchor at which it appears)
    (1812.6, '1812', 'first settlers arrive', None),
    (1814.02, 'JAN 1814', 'the order', None),
    (1814.4, '1814', 'Souris seizure', None),
    (1815.45, 'JUNE 1815', 'most settlers leave', 'P25.1'),
    (1815.8, 'FALL 1815', 'Semple arrives', 'P26.1'),
    (1816.2, 'MARCH 1816', 'Fort Gibraltar seized', 'P26.2'),
    (1816.4, 'SPRING 1816', "Qu'Appelle seizure", 'P27.1'),
    (1816.47, '19 JUNE 1816', 'Frog Plain', 'P29.0'),
]


def timeline(tl, dur, t, focus=None):
    out = bg_dark(t, 0.08)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.5, 0.7)
    x0, x1, y = 220, 1700, 560

    def X(yr):
        return x0 + (yr - 1812) / (1816.7 - 1812) * (x1 - x0)

    L.line(x0, y, x1, y, INK_DIM, a * 0.7, 2)
    for yr in range(1812, 1817):
        L.line(X(yr), y - 10, X(yr), y + 10, INK_DIM, a * 0.7, 2)
        L.text(str(yr), X(yr), y + 50, font('sans', 22, 600), INK_DIM, a * 0.8, align='center', tracking=3)
    for i, (yr, l1, l2, anc) in enumerate(TIMELINE):
        if anc is not None and t < anchor(anc) - 0.3:
            continue
        k = 1.0 if anc is None else ease_out(seg(t, anchor(anc) - 0.3, anchor(anc) + 0.6))
        new = anc is not None and t < anchor(anc) + 6
        col = OCHRE if new else INK
        up = i % 2 == 0
        yy = y - 70 if up else y + 110
        L.circle(X(yr), y, 7, col if anc else INK_DIM, a * k)
        L.line(X(yr), y + (-12 if up else 12), X(yr), yy + (12 if up else -36), INK_DIM, a * k * 0.5, 1.2)
        L.text(l1, X(yr), yy - 34 if up else yy, font('sans', 19, 700), col, a * k * (1 if (new or anc is None) else 0.75), align='center', tracking=3)
        L.text(l2, X(yr), yy if up else yy + 36, font('serif_i', 28, 500), INK if new else INK_DIM, a * k, align='center')
    return comp(out, L)


def two_names(tl, dur, t):
    """P32.0–P32.1 (D7)."""
    out = bg_live('plain_G3', tl, dur, t, dim=0.4)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.8)
    end = t - tl + dur
    k1 = fade_window(t, anchor('P32.0') - 0.2, end, 0.6, 0.8)
    L.text('IN THE SETTLER TRADITION', 960, 300, font('sans', 22, 700), INK_DIM, a * k1, align='center', tracking=7)
    L.text('The Seven Oaks Massacre', 960, 380, font('serif', 68, 600), INK, a * k1, align='center')
    L.line(760, 470, 1160, 470, INK_DIM, a * 0.5 * k1, 1.2)
    k2 = fade_window(t, anchor('P32.1') - 0.2, end, 0.6, 0.8)
    L.text('FOR THE MÉTIS', 960, 560, font('sans', 22, 700), OCHRE, a * k2, align='center', tracking=7)
    L.text('The Victory of Frog Plain', 960, 640, font('serif', 68, 600), INK, a * k2, align='center')
    L.text('la Victoire de la Grenouillère', 960, 705, font('serif_i', 44, 500), OCHRE, a * k2, align='center')
    return comp(out, L)


def merger(tl, dur, t):
    """P33.3 (E3): 1821 merger."""
    out = bg_live('dock_C1', tl, dur, t, dim=0.4, s=(1.1, 1.18))
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.8)
    k = ease_io(seg(tl, 0.6, 2.6))
    L.text('NORTH WEST COMPANY', 960 - 360 * (1 - k), 470, font('sans', 30, 700), OCHRE, a * (1 - 0.6 * k), align='center', tracking=6)
    L.text("HUDSON'S BAY COMPANY", 960 + 360 * (1 - k), 560, font('sans', 30, 700), STEEL, a, align='center', tracking=6)
    k2 = ease_out(seg(tl, 2.4, 3.4))
    L.text('1821', 960, 360, font('serif', 92, 600), INK, a * k2, align='center')
    L.text("merged under the Hudson's Bay Company name", 960, 680, font('serif_i', 40, 500), INK_DIM, a * k2, align='center')
    return comp(out, L)


# ------------------------------------------------------------------ chapter V overlays (draw on a Layer)
def ov_big(L, t, t0, t1, big, small=None, y=520, col=INK, size=110):
    a = fade_window(t, t0, t1, 0.8, 0.9)
    if a <= 0:
        return
    k = ease_out(seg(t, t0, t0 + 1.4))
    L.gradient_rect(0, y - 220, 1920, 360, [(0, DARK, 0.0), (0.5, DARK, 0.45 * a), (1, DARK, 0.0)])
    L.text(big, 960, y, font('serif', size, 600), col, a, align='center', tracking=lerp(20, 8, k), shadow=0.8)
    if small:
        L.text(small, 960, y + 66, font('serif_i', 36, 500), INK_DIM, a, align='center', shadow=0.8)


def ov_counter(L, t, t0, t1, value, label, sub=None, y=540):
    a = fade_window(t, t0, t1, 0.6, 0.9)
    if a <= 0:
        return
    k = ease_out(seg(t, t0, t0 + 2.0), 3)
    v = int(round(value * k))
    L.gradient_rect(0, y - 230, 1920, 380, [(0, DARK, 0.0), (0.5, DARK, 0.5 * a), (1, DARK, 0.0)])
    L.text(f'{v:,}', 960, y, font('serif', 150, 600), OCHRE, a, align='center', shadow=0.8)
    L.text(label, 960, y + 70, font('serif_i', 40, 500), INK, a, align='center', shadow=0.8)
    if sub:
        L.text(sub, 960, y + 120, font('sans', 20, 500), INK_DIM, a, align='center', tracking=2, shadow=0.8)


def ov_card(L, t, t0, t1, lines, y=380):
    """Stacked text card (title, then lines) on a soft dark band."""
    a = fade_window(t, t0, t1, 0.7, 0.9)
    if a <= 0:
        return
    L.gradient_rect(0, y - 160, 1920, 120 + 70 * len(lines) + 120, [(0, DARK, 0.0), (0.3, DARK, 0.55 * a), (0.7, DARK, 0.55 * a), (1, DARK, 0.0)])
    yy = y
    for i, (txt, face, size, col) in enumerate(lines):
        k = ease_out(seg(t, t0 + 0.25 * i, t0 + 0.25 * i + 0.9))
        L.text(txt, 960, yy, font(face, size, 600 if face in ('serif', 'sans') else 500), col, a * k, align='center',
               tracking=6 if face == 'sans' else 0, shadow=0.8)
        yy += size * 1.55
