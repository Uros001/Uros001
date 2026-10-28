"""Thumbnails (1920x1080 master + 1280x720 upload size) from the rendered plates and graphics.

Primary  "ILLEGAL CARGO": the hair-on rawhide bag on the misty landing (plate dock_D3).
Alt      "LASTED YEARS":  the bag (dock_D1) with a cutaway inset of what is inside (diagram).
"""
import os, sys
import numpy as np
import cv2
import skia
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from film import core, gfx, text as T

OUT = os.path.join(core.ROOT, 'delivery')


def oswald(size, weight=700):
    return skia.Font(T.typeface(T.OSWALD, weight), size)


def draw_text(c, txt, x, y, f, col, shadow=True, stroke=0):
    if shadow:
        sp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.75))
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
        c.drawString(txt, x + 6, y + 8, f, sp)
    if stroke:
        p = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.05, 0.04, 0.03, 0.9), Style=skia.Paint.kStroke_Style, StrokeWidth=stroke)
        p.setStrokeJoin(skia.Paint.kRound_Join)
        c.drawString(txt, x, y, f, p)
    c.drawString(txt, x, y, f, skia.Paint(AntiAlias=True, Color4f=T.color(col)))


def base(name, crop_cx=0.5, crop_cy=0.5, zoom=1.0):
    img = gfx._plate_comp(name, 0)
    sh, sw = img.shape[:2]
    M = core.affine(zoom, crop_cx, crop_cy, src_w=sw, src_h=sh)
    out = core.warp(img, M)
    out = core.grade(out, contrast=1.16, sat=1.08, temp=0.25, gamma=1.02)
    out = core.bloom(out, 0.8, 0.2)
    y, x = np.mgrid[0:core.H, 0:core.W].astype(np.float32)
    r = np.sqrt(((x - core.W * 0.45) / core.W) ** 2 * 1.4 + ((y - core.H * 0.55) / core.H) ** 2)
    out *= np.clip(1.12 - 0.75 * r, 0.35, 1)[:, :, None]
    return out


def to_canvas(img):
    u8 = core.to_u8(img)
    rgba = np.dstack([u8, np.full(u8.shape[:2], 255, np.uint8)])
    surf = skia.Surface(core.W, core.H)
    c = surf.getCanvas()
    c.drawImage(skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType), 0, 0)
    return surf, c


def save(surf, stem):
    arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3]
    bgr = arr[:, :, ::-1]
    cv2.imwrite(os.path.join(OUT, stem + '_1920.png'), bgr)
    small = cv2.resize(bgr, (1280, 720), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(OUT, stem + '.png'), small)
    cv2.imwrite(os.path.join(OUT, stem + '_preview160.png'), cv2.resize(bgr, (160, 90), interpolation=cv2.INTER_AREA))


def primary():
    img = base('dock_D3', 0.47, 0.52, 1.06)
    # darken the right third behind the text
    g = np.linspace(0, 1, core.W, dtype=np.float32)[None, :, None]
    img *= 1 - 0.55 * np.clip((g - 0.55) / 0.3, 0, 1)
    surf, c = to_canvas(img)
    f = oswald(250, 700)
    w1 = f.measureText('ILLEGAL')
    w2 = f.measureText('CARGO')
    x = core.W - 70 - max(w1, w2)
    draw_text(c, 'ILLEGAL', core.W - 70 - w1, 330, f, '#f4ead8', stroke=10)
    draw_text(c, 'CARGO', core.W - 70 - w2, 590, f, '#e7a64c', stroke=10)
    tag = oswald(64, 600)
    c.drawRect(skia.Rect.MakeXYWH(core.W - 70 - 196, 640, 196, 84), skia.Paint(AntiAlias=True, Color4f=T.color('#a8483a', 0.95)))
    c.drawString('1814', core.W - 70 - 196 + 30, 705, tag, skia.Paint(AntiAlias=True, Color4f=T.color('#f4ead8')))
    save(surf, 'thumbnail_primary')


def alternative():
    img = base('dock_D1', 0.44, 0.55, 1.12)
    surf, c = to_canvas(img)
    # inset: cutaway diagram, rendered from the film's own graphic, clipped to a rounded panel
    sec = gfx.section(6.0, 8.0, 200.0)
    sec_u8 = core.to_u8(sec)
    crop = sec_u8[300:780, 520:1400]
    crop = cv2.resize(crop, (700, 382), interpolation=cv2.INTER_AREA)
    rgba = np.dstack([crop, np.full(crop.shape[:2], 255, np.uint8)])
    x0, y0 = 1150, 560
    c.save()
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y0, 700, 382), 28, 28)
    sp = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.7))
    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
    c.drawRRect(rr, sp)
    c.clipRRect(rr, doAntiAlias=True)
    c.drawImage(skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType), x0, y0)
    c.restore()
    c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=T.color('#e7a64c'), Style=skia.Paint.kStroke_Style, StrokeWidth=6))
    lp = skia.Paint(AntiAlias=True, Color4f=T.color('#e7a64c'), Style=skia.Paint.kStroke_Style, StrokeWidth=6)
    c.drawLine(1150, 700, 900, 720, lp)
    c.drawCircle(900, 720, 12, skia.Paint(AntiAlias=True, Color4f=T.color('#e7a64c')))
    f = oswald(230, 700)
    draw_text(c, 'LASTED', 70, 270, f, '#f4ead8', stroke=10)
    draw_text(c, 'YEARS', 70, 510, f, '#e7a64c', stroke=10)
    save(surf, 'thumbnail_alt')


if __name__ == '__main__':
    primary()
    alternative()
    print('thumbnails written')
