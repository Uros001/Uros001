"""Typography and vector drawing on Skia, returned as straight-alpha float RGBA layers."""
import os, functools, math
import numpy as np
import skia
from . import core
from .core import ease_out, ease_io, seg, clamp, hexc

FONTS = os.path.join(core.ROOT, 'assets/fonts')
CORMORANT = os.path.join(FONTS, 'cormorantgaramond_CormorantGaramond[wght].ttf')
CORMORANT_I = os.path.join(FONTS, 'cormorantgaramond_CormorantGaramond-Italic[wght].ttf')
OSWALD = os.path.join(FONTS, 'oswald_Oswald[wght].ttf')

# brand palette (sRGB hex)
INK = '#ece4d4'        # warm off-white text
INK_DIM = '#b9b0a0'
OCHRE = '#d39b45'      # North West Company route / highlights
STEEL = '#8fb0c2'      # Hudson's Bay Company / water
RUST = '#a8483a'       # conflict / seizure
DARK = '#101214'


@functools.lru_cache(maxsize=64)
def typeface(path_or_family, weight=400):
    if os.path.sep in path_or_family:
        tf = skia.Typeface.MakeFromFile(path_or_family)
        if '[wght]' in path_or_family:
            tag = int.from_bytes(b'wght', 'big')
            C = skia.FontArguments.VariationPosition.Coordinate
            vp = skia.FontArguments.VariationPosition(skia.FontArguments.VariationPosition.Coordinates([C(tag, weight)]))
            fa = skia.FontArguments()
            fa.setVariationDesignPosition(vp)
            tf = tf.makeClone(fa)
        return tf
    return skia.Typeface.MakeFromName(path_or_family, skia.FontStyle(weight, 5, skia.FontStyle.kUpright_Slant))


def font(face='serif', size=48, weight=500):
    path = {'serif': CORMORANT, 'serif_i': CORMORANT_I, 'cond': OSWALD}.get(face)
    tf = typeface(path, weight) if path else typeface({'sans': 'Inter', 'garamond': 'EB Garamond 12'}.get(face, face), weight)
    f = skia.Font(tf, size * core.W / 1920)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kSubpixelAntiAlias if False else skia.Font.Edging.kAntiAlias)
    return f


def color(h, a=1.0):
    r, g, b = hexc(h)
    return skia.Color4f(r, g, b, a)


class Layer:
    """A transparent Skia canvas the size of the frame."""

    def __init__(self):
        self.surface = skia.Surface(core.W, core.H)
        self.c = self.surface.getCanvas()
        self.c.clear(skia.Color4f(0, 0, 0, 0))

    def rgba(self):
        img = self.surface.makeImageSnapshot()
        arr = img.toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
        return arr.astype(np.float32) / 255.0

    # ---- primitives (sizes are in 1920-px design units, scaled to the frame)
    @staticmethod
    def s(v):
        return v * core.W / 1920

    def text(self, txt, x, y, f, col=INK, alpha=1.0, align='left', tracking=0.0, shadow=0.0, blur=0.0):
        paint = skia.Paint(AntiAlias=True, Color4f=color(col, alpha))
        if blur:
            paint.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, self.s(blur)))
        w = self.measure(txt, f, tracking)
        X = self.s(x) - (w if align == 'right' else w / 2 if align == 'center' else 0)
        Y = self.s(y)
        if shadow:
            sp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.55 * alpha * shadow))
            sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, self.s(6)))
            self._draw(txt, X + self.s(2), Y + self.s(3), f, sp, tracking)
        self._draw(txt, X, Y, f, paint, tracking)
        return w

    def _draw(self, txt, X, Y, f, paint, tracking):
        if not tracking:
            self.c.drawString(txt, X, Y, f, paint)
            return
        tr = self.s(tracking)
        for ch in txt:
            self.c.drawString(ch, X, Y, f, paint)
            X += f.measureText(ch) + tr

    def measure(self, txt, f, tracking=0.0):
        if not tracking:
            return f.measureText(txt)
        return sum(f.measureText(ch) for ch in txt) + self.s(tracking) * (len(txt) - 1)

    def line(self, x0, y0, x1, y1, col=INK, alpha=1.0, width=2.0, cap='round', dash=None):
        p = skia.Paint(AntiAlias=True, Color4f=color(col, alpha), StrokeWidth=self.s(width), Style=skia.Paint.kStroke_Style)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == 'round' else skia.Paint.kButt_Cap)
        if dash:
            p.setPathEffect(skia.DashPathEffect.Make([self.s(d) for d in dash], 0))
        self.c.drawLine(self.s(x0), self.s(y0), self.s(x1), self.s(y1), p)

    def rect(self, x, y, w, h, col=DARK, alpha=1.0, radius=0.0, stroke=0.0):
        p = skia.Paint(AntiAlias=True, Color4f=color(col, alpha))
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style)
            p.setStrokeWidth(self.s(stroke))
        r = skia.Rect.MakeXYWH(self.s(x), self.s(y), self.s(w), self.s(h))
        if radius:
            self.c.drawRoundRect(r, self.s(radius), self.s(radius), p)
        else:
            self.c.drawRect(r, p)

    def circle(self, x, y, r, col=INK, alpha=1.0, stroke=0.0, blur=0.0):
        p = skia.Paint(AntiAlias=True, Color4f=color(col, alpha))
        if stroke:
            p.setStyle(skia.Paint.kStroke_Style)
            p.setStrokeWidth(self.s(stroke))
        if blur:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, self.s(blur)))
        self.c.drawCircle(self.s(x), self.s(y), self.s(r), p)

    def gradient_rect(self, x, y, w, h, stops, vertical=True):
        pts = [skia.Point(self.s(x), self.s(y)), skia.Point(self.s(x), self.s(y + h))] if vertical else \
              [skia.Point(self.s(x), self.s(y)), skia.Point(self.s(x + w), self.s(y))]
        cols = [color(c, a) for _, c, a in stops]
        pos = [p for p, _, _ in stops]
        sh = skia.GradientShader.MakeLinear(pts, [c.toColor() for c in cols], pos)
        p = skia.Paint(AntiAlias=True)
        p.setShader(sh)
        self.c.drawRect(skia.Rect.MakeXYWH(self.s(x), self.s(y), self.s(w), self.s(h)), p)


# ------------------------------------------------------------------ components
def fade_window(t, t0, t1, fin=0.5, fout=0.6):
    """Opacity envelope for an element visible on [t0, t1]."""
    if t < t0 or t > t1:
        return 0.0
    return min(ease_out(seg(t, t0, t0 + fin)), 1.0 - ease_io(seg(t, t1 - fout, t1)))


def lower_third(L, t, t0, t1, name, role, x=150, y=900):
    a = fade_window(t, t0, t1, 0.7, 0.7)
    if a <= 0:
        return
    k = ease_out(seg(t, t0, t0 + 1.0))
    L.gradient_rect(0, y - 110, 1100, 230, [(0, DARK, 0.0), (0.5, DARK, 0.45 * a), (1, DARK, 0.0)])
    L.line(x, y - 58, x + 420 * k, y - 58, OCHRE, 0.9 * a, 2)
    L.text(name, x, y - 10, font('serif', 52, 600), INK, a, shadow=0.6)
    L.text(role.upper(), x + 2, y + 34, font('sans', 19, 500), INK_DIM, a * k, tracking=3.2)


def super_label(L, t, t0, t1, line1, line2=None, x=150, y=150, align='left'):
    """Place/date super (top-left by default)."""
    a = fade_window(t, t0, t1, 0.8, 0.8)
    if a <= 0:
        return
    L.text(line1.upper(), x, y, font('sans', 22, 600), INK, a, align=align, tracking=5, shadow=0.7)
    if line2:
        L.text(line2, x, y + 40, font('serif_i', 30, 500), INK_DIM, a, align=align, shadow=0.7)


def caption(L, t, t0, t1, txt, x=960, y=1010, size=20):
    """Small source/disclosure caption, bottom centre."""
    a = fade_window(t, t0, t1, 0.6, 0.6) * 0.85
    if a <= 0:
        return
    L.text(txt, x, y, font('sans', size, 400), INK_DIM, a, align='center', tracking=0.6, shadow=0.8)


def credit(L, t, t0, t1, title, line2, x=1840, y=1000):
    """Credit for an archival image, bottom right: title and date, then maker and collection."""
    a = fade_window(t, t0, t1, 0.8, 0.6)
    if a <= 0:
        return
    L.gradient_rect(1100, y - 70, 820, 150, [(0, DARK, 0.0), (0.6, DARK, 0.32 * a), (1, DARK, 0.4 * a)], vertical=False)
    L.text(title, x, y, font('serif_i', 25, 500), INK, a * 0.95, align='right', shadow=0.8)
    L.text(line2.upper(), x, y + 32, font('sans', 14, 600), INK_DIM, a * 0.9, align='right', tracking=2.4, shadow=0.8)


def chapter_label(L, t, t0, num, title, dur=4.2):
    a = fade_window(t, t0, t0 + dur, 0.9, 0.9)
    if a <= 0:
        return
    L.text(num, 150, 140, font('serif', 34, 500), OCHRE, a, shadow=0.6)
    L.text(title.upper(), 150 + 22 + L.measure(num, font('serif', 34, 500)) / (core.W / 1920), 138,
           font('sans', 20, 600), INK, a, tracking=5, shadow=0.6)


def chapter_card(L, t, t0, t1, num, title):
    a = fade_window(t, t0, t1, 0.7, 0.8)
    k = ease_out(seg(t, t0 + 0.2, t0 + 1.6))
    L.text(num, 960, 470, font('serif', 64, 400), OCHRE, a, align='center')
    L.line(960 - 160 * k, 520, 960 + 160 * k, 520, OCHRE, 0.7 * a, 1.6)
    L.text(title.upper(), 960, 600, font('serif', 64, 500), INK, a, align='center', tracking=10)


def reveal_words(L, t, t0, txt, x, y, f, col=INK, per=0.09, dur=0.6, align='left', tracking=0.0, alpha=1.0,
                 rise=14):
    """Word-by-word fade/rise reveal starting at t0."""
    words = txt.split(' ')
    space = f.measureText(' ')
    total = sum(L.measure(w, f, tracking) for w in words) + space * (len(words) - 1)
    X = L.s(x) - (total if align == 'right' else total / 2 if align == 'center' else 0)
    for i, w in enumerate(words):
        k = ease_out(seg(t, t0 + i * per, t0 + i * per + dur))
        if k > 0:
            paint = skia.Paint(AntiAlias=True, Color4f=color(col, alpha * k))
            L._draw(w, X, L.s(y + rise * (1 - k)), f, paint, tracking)
        X += L.measure(w, f, tracking) + space
    return total
