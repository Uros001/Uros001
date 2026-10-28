"""Map sequences. Each is fn(tl, dur, t) -> RGB frame. Geography from Natural Earth (public domain).

Places and routes are approximate and drawn for orientation; the film labels reconstructed
boundaries as approximate.
"""
import math, functools
import numpy as np
from . import core, maps as M, text as T
from .core import ease_io, ease_out, seg, clamp, lerp, anchor
from .text import Layer, font, INK, INK_DIM, OCHRE, STEEL, RUST, DARK, fade_window

# ------------------------------------------------------------------ places (lon, lat)
MONTREAL = (-73.57, 45.50)
FORT_WILLIAM = (-89.25, 48.38)
FORKS = (-97.131, 49.887)
FORT_DOUGLAS = (-97.125, 49.905)
FROG_PLAIN = (-97.115, 49.945)
SOURIS_POST = (-99.55, 49.65)
QUAPPELLE = (-101.9, 50.55)
PORTAGE = (-98.29, 49.97)
LAKE_WPG_S = (-96.85, 50.45)
YORK_FACTORY = (-92.3, 57.0)
CHIPEWYAN = (-111.15, 58.71)
BROWNING = (-113.01, 48.557)

# North West Company canoe road, Montreal -> Athabasca (approximate waypoints)
NWC_ROUTE = [MONTREAL, (-75.7, 45.42), (-78.7, 46.32), (-79.6, 46.25), (-80.9, 45.95), (-82.6, 46.1), (-84.35, 46.5),
             (-84.9, 47.6), (-86.3, 48.55), (-88.0, 48.75), FORT_WILLIAM, (-90.6, 48.1), (-92.2, 48.5), (-93.4, 48.65),
             (-94.8, 49.4), (-95.6, 50.2), (-96.35, 50.62), (-96.9, 51.6), (-97.9, 52.7), (-99.27, 53.17),
             (-100.9, 53.6), (-102.27, 53.96), (-103.4, 55.0), (-104.6, 55.6), (-107.9, 55.45), (-109.0, 56.0),
             (-109.9, 56.4), (-111.38, 56.73), (-111.45, 57.6), (-111.3, 58.3), CHIPEWYAN]
SPLIT = NWC_ROUTE.index(FORT_WILLIAM)
HBC_SEA = [(-8.0, 58.5), (-25.0, 59.5), (-42.0, 60.0), (-56.0, 60.8), (-64.5, 61.6), (-70.5, 62.2), (-77.0, 62.4),
           (-83.0, 60.8), (-88.0, 58.8), YORK_FACTORY]
DEPOTS = [(-96.35, 50.62), (-102.27, 53.96), (-107.9, 55.45), FORT_WILLIAM]    # unnamed depot markers
PLAINS_POSTS = [(-99.95, 49.85), (-101.4, 50.6), (-105.0, 52.6), (-110.7, 53.5), (-112.5, 53.9)]

# Assiniboia grant, approximate outline (scaled to ~300,000 km2 at runtime)
_ASSINIBOIA = [(-97.0, 52.5), (-100.5, 52.5), (-101.8, 51.5), (-102.0, 50.0), (-101.5, 48.5), (-99.5, 47.0),
               (-97.0, 46.6), (-95.4, 47.3), (-95.0, 48.4), (-94.7, 49.1), (-95.6, 50.2), (-96.5, 50.6), (-96.9, 51.5)]


def _area_km2(ring):
    ring = np.asarray(ring, float)
    lat0 = ring[:, 1].mean()
    x = ring[:, 0] * 111.32 * math.cos(math.radians(lat0))
    y = ring[:, 1] * 110.57
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


@functools.lru_cache(maxsize=1)
def assiniboia():
    ring = np.array(_ASSINIBOIA, float)
    c = ring.mean(0)
    k = math.sqrt(300000.0 / _area_km2(ring))     # C1: ~116,000 sq mi = ~300,000 km2
    out = c + (ring - c) * k
    return out


@functools.lru_cache(maxsize=1)
def italy_here():
    ring = M.country_outline('Italy')
    src = ring.mean(0)
    return M.transplant(ring, tuple(src), (-85.2, 49.4))


def _finish_map(img, L, t):
    out = core.over(img, L.rgba())
    return core.grade(out, contrast=1.04, sat=0.95)


def _cam(keys, tl):
    return M.lerp_cam(keys, tl)


def _caption(L, a, txt):
    T.caption(L, 0, -1, 1, '')  # no-op keeps signature parity
    L.text(txt, 960, 1030, font('sans', 18, 500), INK_DIM, a * 0.85, align='center', tracking=1.5, shadow=0.8)


# ------------------------------------------------------------------ sequences
def plains_peoples(tl, dur, t):
    """P07.2: Plains peoples, among them the Cree and the Assiniboine, where their lands met the fur trade."""
    cam = _cam([(0, -101.0, 52.3, 112), (dur, -101.8, 52.0, 132)], tl)
    img = M.base(cam, relief=1.0, borders=0.0, graticule=0.04)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    k1 = fade_window(tl, 0.6, dur, 0.8, 0.6)
    M.area_label(L, cam, -106.5, 53.4, 'Cree', a * k1, size=40, italic=True, col=INK)
    k2 = fade_window(tl, 1.6, dur, 0.8, 0.6)
    M.area_label(L, cam, -102.8, 50.2, 'Assiniboine (Nakoda)', a * k2, size=36, italic=True, col=INK)
    k3 = fade_window(tl, 3.2, dur, 0.8, 0.6)
    M.route(L, cam, NWC_ROUTE[SPLIT + 5:SPLIT + 15], ease_io(seg(tl, 3.2, dur - 0.5)), OCHRE, 3.0, a * 0.9, dash=(10, 8))
    M.area_label(L, cam, -100.2, 54.6, 'fur-trade canoe routes', a * k3 * 0.9, size=18, col=OCHRE)
    for lon, lat, name in ((-105.3, 53.2, 'Saskatchewan R.'), (-100.6, 49.95, 'Assiniboine R.'), (-97.05, 49.3, 'Red R.')):
        M.area_label(L, cam, lon, lat, name, a * k1 * 0.75, size=15, col=M.LABEL_WATER, tracking=3)
    _caption(L, a, 'Approximate homelands, early 1800s. Other nations also lived and traded across this region.')
    return _finish_map(img, L, t)


def canoe_road(tl, dur, t):
    """P14 (B1/B2): NWC route Montreal -> Athabasca, ~3,000 miles, split at the western end of Lake Superior."""
    keys = [(0, -75.0, 46.5, 220), (4.0, -82.0, 49.0, 120), (9.0, -92.5, 52.4, 52), (dur - 7.0, -92.0, 52.3, 50),
            (dur, -91.0, 51.8, 56)]
    cam = _cam(keys, tl)
    img = M.base(cam, relief=1.0, borders=0.15, graticule=0.05)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    M.marker(L, cam, *MONTREAL, 'Montreal', a * ease_out(seg(tl, 0.3, 1.2)), kind='fort', col=OCHRE, label_size=30)
    M.area_label(L, cam, -75.0, 44.4, 'North West Company', a * fade_window(tl, 0.8, 9.0, 0.6, 0.8), size=18, col=OCHRE)
    p = ease_io(seg(tl, 3.5, 13.0))
    M.route(L, cam, NWC_ROUTE, p, OCHRE, 3.6, a)
    ka = fade_window(tl, 7.5, dur, 0.8, 0.6)
    M.area_label(L, cam, -112.5, 58.0, 'Athabasca', a * ka, size=40, italic=True, col=INK)
    t_mi = anchor('P14.1') - (t - tl)
    km = fade_window(tl, t_mi - 0.2, t_mi + 7.0, 0.6, 0.8)
    L.text('≈ 3,000 miles', 960, 160, font('serif', 64, 600), OCHRE, a * km, align='center', shadow=1.0)
    t_sp = anchor('P14.2') - (t - tl)
    ks = fade_window(tl, t_sp, dur, 0.6, 0.6)
    if ks > 0:
        M.route(L, cam, NWC_ROUTE[:SPLIT + 1], 1.0, '#e8c27a', 5.0, a * ks, glow=False, head=False)
        M.route(L, cam, NWC_ROUTE[SPLIT:], 1.0, '#b9773a', 5.0, a * ks, glow=False, head=False)
        M.marker(L, cam, *FORT_WILLIAM, 'Fort William', a * ks, kind='fort', col=INK, label_size=30, pulse=(tl * 0.6) % 1)
        M.area_label(L, cam, -80.5, 47.6, 'Montreal crews', a * ks * 0.95, size=26, italic=True, col='#e8c27a')
        M.area_label(L, cam, -97.0, 50.8, 'interior crews', a * ks * 0.95, size=26, italic=True, col='#d49a5c')
    _caption(L, a, 'Route simplified; the canoe road followed rivers, lakes and portages.')
    return _finish_map(img, L, t)


def depots(tl, dur, t):
    """P16.3 (B3): pemmican made on the plains, bought, and stockpiled at depots along the route."""
    cam = _cam([(0, -100.0, 53.6, 84), (dur, -100.5, 53.5, 92)], tl)
    img = M.base(cam, relief=1.0, borders=0.1, graticule=0.04)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    M.route(L, cam, NWC_ROUTE[SPLIT:], 1.0, OCHRE, 3.0, a * 0.8, glow=False, head=False)
    plains = [(-112.0, 50.0), (-104.0, 49.0), (-97.5, 48.5), (-97.0, 50.2), (-101.0, 52.5), (-108.0, 53.2), (-113.5, 53.0)]
    M.polygon(L, cam, plains, a * ease_out(seg(tl, 0.3, 1.5)), fill='#a8483a', fill_a=0.16, stroke='#a8483a', stroke_a=0.5, dash=(6, 6))
    M.area_label(L, cam, -104.5, 50.8, 'bison country', a * fade_window(tl, 0.6, dur, 0.6, 0.6), size=34, italic=True, col='#e6a090')
    for i, (lon, lat) in enumerate(PLAINS_POSTS):
        M.marker(L, cam, lon, lat, None, a * ease_out(seg(tl, 1.2 + i * 0.25, 1.8 + i * 0.25)), kind='dot', col='#e6a090', size=0.8)
    for i, (lon, lat) in enumerate(DEPOTS):
        k = ease_out(seg(tl, 3.0 + i * 0.6, 3.8 + i * 0.6))
        M.marker(L, cam, lon, lat, 'depot' if i == 0 else None, a * k, kind='diamond', col=OCHRE, size=1.4, label_size=26, italic=True)
        if k > 0 and i < len(DEPOTS):
            x0, y0 = cam.p(*PLAINS_POSTS[min(i, len(PLAINS_POSTS) - 1)])
    _caption(L, a, 'Schematic: provisioning posts on the plains supplied depots on the canoe road.')
    return _finish_map(img, L, t)


def metis_rivers(tl, dur, t):
    """P17.1: Métis communities along the Red and Assiniboine rivers."""
    cam = _cam([(0, -99.0, 50.0, 380), (dur, -98.6, 49.95, 450)], tl)
    img = M.base(cam, relief=1.0, borders=0.1, graticule=0.0, rivers=1.4)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    red = [(-97.2, 48.6), (-97.15, 49.0), (-97.2, 49.4), (-97.13, 49.887), (-97.0, 50.2), (-96.8, 50.4)]
    assin = [(-101.6, 50.4), (-100.5, 49.9), (-99.6, 49.75), (-98.6, 49.95), (-98.0, 49.85), (-97.5, 49.87), (-97.131, 49.887)]
    k = ease_io(seg(tl, 0.5, 3.5))
    M.route(L, cam, red, k, OCHRE, 5.0, a, head=False)
    M.route(L, cam, assin, k, OCHRE, 5.0, a, head=False)
    M.area_label(L, cam, -97.55, 49.15, 'Red River', a * k, size=30, italic=True, col=INK)
    M.area_label(L, cam, -100.0, 50.2, 'Assiniboine River', a * k, size=30, italic=True, col=INK)
    kk = fade_window(tl, 2.5, dur, 0.8, 0.6)
    M.area_label(L, cam, -98.6, 50.75, 'Métis communities', a * kk, size=24, col=OCHRE)
    M.marker(L, cam, *FORKS, None, a * kk, kind='dot', col=OCHRE)
    return _finish_map(img, L, t)


def furs_fuel(tl, dur, t):
    """P18.1–P18.2: furs from the north, fuel from bison country."""
    cam = _cam([(0, -106.0, 54.8, 72), (dur, -106.0, 54.6, 78)], tl)
    img = M.base(cam, relief=1.0, borders=0.1, graticule=0.04)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    M.route(L, cam, NWC_ROUTE[SPLIT:], 1.0, OCHRE, 2.6, a * 0.6, glow=False, head=False)
    k1 = fade_window(t, anchor('P18.1') - 0.2, t - tl + dur, 0.7, 0.6)
    north = [(-117.0, 56.0), (-110.0, 55.5), (-104.0, 57.0), (-104.0, 60.5), (-112.0, 61.0), (-119.0, 59.5)]
    M.polygon(L, cam, north, a * k1, fill=STEEL, fill_a=0.22, stroke=STEEL, stroke_a=0.7)
    M.area_label(L, cam, -111.0, 58.4, 'furs', a * k1, size=56, italic=True, col='#cfe0ea')
    k2 = fade_window(t, anchor('P18.2') - 0.2, t - tl + dur, 0.7, 0.6)
    south = [(-114.0, 49.2), (-104.0, 48.8), (-97.6, 48.6), (-97.0, 50.3), (-101.0, 52.6), (-108.0, 53.3), (-114.0, 53.0)]
    M.polygon(L, cam, south, a * k2, fill=OCHRE, fill_a=0.2, stroke=OCHRE, stroke_a=0.7)
    M.area_label(L, cam, -105.5, 51.0, 'fuel', a * k2, size=56, italic=True, col='#f0cc8a')
    return _finish_map(img, L, t)


def two_routes(tl, dur, t):
    """P19.1–P19.4: HBC by sea through Hudson Bay vs NWC canoe road; then zoom to the Forks."""
    t4 = anchor('P19.4') - (t - tl)
    keys = [(0, -62.0, 55.0, 15.5), (max(t4 - 1.0, 1.0), -70.0, 54.0, 17.0), (max(t4 + 5.5, 2.0), -97.13, 49.9, 520), (dur, -97.13, 49.9, 600)]
    cam = _cam(keys, tl)
    img = M.base(cam, relief=1.0, borders=0.1, graticule=0.05)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    p1 = ease_io(seg(t, anchor('P19.1') - 0.2, anchor('P19.1') + 4.0))
    M.route(L, cam, HBC_SEA, p1, STEEL, 3.4, a, dash=(14, 8))
    k1 = fade_window(t, anchor('P19.1'), t - tl + t4 + 1.0, 0.6, 0.8)
    M.marker(L, cam, *YORK_FACTORY, 'York Factory', a * k1, kind='fort', col=STEEL, label_size=26)
    M.area_label(L, cam, -86.0, 60.0, 'Hudson Bay', a * k1 * 0.85, size=20, col=M.LABEL_WATER)
    M.area_label(L, cam, -38.0, 62.5, "Hudson's Bay Company: by sea", a * k1, size=20, col='#cfe0ea')
    p2 = ease_io(seg(t, anchor('P19.2') - 0.2, anchor('P19.3') + 3.0))
    M.route(L, cam, NWC_ROUTE, p2, OCHRE, 3.4, a * (1 - 0.5 * seg(tl, t4 + 1, t4 + 3)))
    k2 = fade_window(t, anchor('P19.2'), t - tl + t4 + 1.0, 0.6, 0.8)
    M.area_label(L, cam, -79.0, 44.0, 'North West Company: by canoe', a * k2, size=20, col='#f0cc8a')
    k4 = fade_window(tl, t4 + 2.5, dur, 0.8, 0.6)
    if k4 > 0:
        red = [(-97.2, 49.4), (-97.13, 49.887), (-97.0, 50.2)]
        assin = [(-98.0, 49.85), (-97.5, 49.87), (-97.131, 49.887)]
        M.route(L, cam, red, 1.0, OCHRE, 6, a * k4, head=False)
        M.route(L, cam, assin, 1.0, OCHRE, 6, a * k4, head=False)
        M.marker(L, cam, *FORKS, 'the Forks', a * k4, kind='dot', col=INK, size=1.6, label_size=40, pulse=(tl * 0.5) % 1)
    return _finish_map(img, L, t)


def assiniboia_map(tl, dur, t):
    """P20.0–P20.4 (C1): the grant, ~116,000 sq mi, roughly the size of Italy; the Forks in the middle."""
    keys = [(0, -97.13, 49.9, 520), (3.0, -97.8, 49.6, 110), (dur, -90.0, 49.3, 80)]
    cam = _cam(keys, tl)
    img = M.base(cam, relief=1.0, borders=0.25, graticule=0.04)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    ring = assiniboia()
    pg = ease_io(seg(tl, 2.0, 5.0))
    M.polygon(L, cam, ring, a, fill=OCHRE, fill_a=0.22 * pg, stroke=OCHRE, stroke_a=0.95, width=2.6, progress=max(pg, 0.001))
    kl = fade_window(tl, 4.5, dur, 0.8, 0.6)
    M.area_label(L, cam, -98.6, 47.6, '≈ 116,000 sq mi', a * kl, size=26, col='#f0cc8a')
    t_it = anchor('P20.1') - (t - tl)
    ki = fade_window(tl, t_it - 0.2, dur, 0.8, 0.6)
    if ki > 0:
        M.polygon(L, cam, italy_here(), a * ki, fill=STEEL, fill_a=0.2, stroke=STEEL, stroke_a=0.9, dash=None,
                  progress=max(ease_io(seg(tl, t_it - 0.2, t_it + 1.8)), 0.001))
        M.area_label(L, cam, -85.0, 53.4, 'Italy, same scale', a * ki, size=26, italic=True, col='#cfe0ea')
    t_n = anchor('P20.3') - (t - tl)
    kn = fade_window(tl, t_n - 0.2, dur, 0.8, 0.6)
    M.area_label(L, cam, -99.6, 50.9, 'ASSINIBOIA', a * kn, size=40, col=INK, tracking=12)
    t_f = anchor('P20.4') - (t - tl)
    kf = fade_window(tl, t_f - 0.2, dur, 0.8, 0.6)
    M.marker(L, cam, *FORKS, 'the Forks', a * kf, kind='dot', col=INK, size=1.4, label_size=30, pulse=(tl * 0.6) % 1)
    if kf > 0:
        M.route(L, cam, NWC_ROUTE[SPLIT + 4:SPLIT + 12], 1.0, OCHRE, 3.0, a * kf * 0.9, dash=(10, 8), glow=False, head=False)
    _caption(L, a, 'Grant boundary approximate. Italy outline: Natural Earth.')
    return _finish_map(img, L, t)


def souris(tl, dur, t):
    """P24.1 (C6): Sheriff John Spencer sent to the NWC post on the Souris River."""
    cam = _cam([(0, -98.3, 49.8, 520), (dur, -98.4, 49.78, 600)], tl)
    img = M.base(cam, relief=1.0, borders=0.1, graticule=0.0, rivers=1.3)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    M.marker(L, cam, *FORT_DOUGLAS, 'colony (Fort Douglas)', a, kind='fort', col=INK, label_size=24, label_dy=28)
    k = ease_io(seg(tl, 0.8, dur - 1.5))
    M.route(L, cam, [FORT_DOUGLAS, (-97.6, 49.85), (-98.6, 49.85), (-99.2, 49.7), SOURIS_POST], k, RUST, 3.4, a, dash=(12, 8))
    ks = fade_window(tl, 1.5, dur, 0.8, 0.6)
    M.marker(L, cam, *SOURIS_POST, 'North West Company post', a * ks, kind='fort', col=OCHRE, label_size=26, align='right', label_dx=-16)
    M.area_label(L, cam, -100.0, 49.42, 'Souris R.', a * ks * 0.8, size=16, col=M.LABEL_WATER, tracking=3)
    _caption(L, a, 'Locations approximate.')
    return _finish_map(img, L, t)


def frog_plain_map(tl, dur, t, phase='march'):
    """P28.0–P29.0 (D1–D3): Grant's party carrying pemmican toward Lake Winnipeg; Semple marches out."""
    if phase == 'route':
        cam = _cam([(0, -99.4, 50.2, 420), (dur, -98.4, 50.15, 500)], tl)
    else:
        cam = _cam([(0, -97.2, 49.95, 900), (dur, -97.15, 49.93, 1100)], tl)
    img = M.base(cam, relief=1.0, borders=0.0, graticule=0.0, rivers=1.5)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    grant = [QUAPPELLE, (-100.6, 50.15), (-99.4, 50.0), PORTAGE, (-97.7, 50.05), FROG_PLAIN, (-97.0, 50.2), LAKE_WPG_S]
    if phase == 'route':
        k = ease_io(seg(tl, 0.5, dur - 1.0))
        M.route(L, cam, grant, k, OCHRE, 3.6, a)
        M.marker(L, cam, *FORT_DOUGLAS, 'colony', a, kind='fort', col=INK, label_size=24, label_dy=30)
        M.area_label(L, cam, -97.2, 50.55, 'Lake Winnipeg', a * 0.85, size=16, col=M.LABEL_WATER, tracking=3)
        kk = fade_window(t, anchor('P28.2') - 0.2, t - tl + dur, 0.7, 0.6)
        M.marker(L, cam, *FROG_PLAIN, 'Frog Plain', a * kk, kind='dot', col=OCHRE, label_size=30, align='left', label_dx=18, label_dy=-14)
        M.area_label(L, cam, -100.0, 49.55, "Grant's party with pemmican", a * fade_window(tl, 1.0, dur, 0.6, 0.6), size=20, col='#f0cc8a')
        _caption(L, a, 'Route approximate.')
    else:
        M.marker(L, cam, *FORT_DOUGLAS, 'Fort Douglas', a, kind='fort', col=INK, label_size=30, align='right', label_dx=-18)
        k = ease_io(seg(tl, 0.8, dur - 0.5))
        M.route(L, cam, [FORT_DOUGLAS, (-97.121, 49.92), FROG_PLAIN], k, RUST, 4.0, a, dash=(12, 8))
        M.route(L, cam, [(-97.35, 49.97), (-97.22, 49.955), FROG_PLAIN, (-97.08, 49.97)], 1.0, OCHRE, 3.6, a * 0.9, head=False)
        M.marker(L, cam, *FROG_PLAIN, 'Frog Plain', a, kind='dot', col=OCHRE, label_size=32, label_dx=18)
        M.area_label(L, cam, -97.06, 49.9, 'Red R.', a * 0.8, size=16, col=M.LABEL_WATER, tracking=3)
        _caption(L, a, 'Schematic positions; the exact ground is still discussed.')
    return _finish_map(img, L, t)


def fort_william_map(tl, dur, t):
    """P33.1 (E1): Selkirk seizes Fort William, the NWC's inland headquarters, August 1816."""
    cam = _cam([(0, -91.5, 49.0, 200), (dur, -89.8, 48.6, 330)], tl)
    img = M.base(cam, relief=1.0, borders=0.2, graticule=0.04)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    k = ease_io(seg(tl, 0.5, 3.5))
    M.route(L, cam, NWC_ROUTE[SPLIT:SPLIT + 17][::-1], k, OCHRE, 2.6, a * 0.6, glow=False, head=False)
    kf = fade_window(tl, 1.5, dur, 0.8, 0.6)
    M.marker(L, cam, *FORT_WILLIAM, 'Fort William', a * kf, kind='fort', col=RUST, label_size=34, pulse=(tl * 0.6) % 1)
    M.area_label(L, cam, -89.0, 47.75, 'seized by Selkirk, August 1816', a * kf, size=20, col='#e6a090')
    M.area_label(L, cam, -87.5, 47.6 - 0.6, 'Lake Superior', a * 0.8, size=16, col=M.LABEL_WATER, tracking=3)
    return _finish_map(img, L, t)


def globe_pole(tl, dur, t):
    """P34.3–P34.4 (E6): factory-made pemmican went worldwide; Amundsen's party carried it to the South Pole, 1911."""
    keys = [(0, -97.0, 42.0, 8.6, 0), (dur * 0.55, -125.0, -28.0, 8.2, 0), (dur, -155.0, -68.0, 8.8, 0)]
    cam = _cam(keys, tl)
    img = M.base(cam, relief=1.0, borders=0.0, graticule=0.08, rivers=0.0)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.6)
    arc = [(-97.0, 50.0), (-105.0, 30.0), (-118.0, 5.0), (-135.0, -25.0), (-158.0, -55.0), (-164.0, -78.5), (0.0, -90.0)]
    k = ease_io(seg(t, anchor('P34.4') - 1.0, anchor('P34.4') + 5.0))
    M.route(L, cam, arc[:-1], k, OCHRE, 3.0, a, dash=(10, 8))
    if k > 0.98:
        M.route(L, cam, [arc[-2], (-170.0, -84.0), (-90.0, -89.99)], ease_io(seg(t, anchor('P34.4') + 5.0, anchor('P34.4') + 7.0)), OCHRE, 3.0, a, dash=(10, 8), smooth=False)
    kp = fade_window(t, anchor('P34.4') + 3.0, t - tl + dur, 0.8, 0.6)
    x, y = cam.p(-90.0, -89.99)
    L.circle(x / (core.W / 1920), y / (core.W / 1920), 6, OCHRE, a * kp)
    L.text('South Pole, 1911', x / (core.W / 1920) + 18, y / (core.W / 1920) - 14, font('serif', 34, 600), INK, a * kp, shadow=1.0)
    kt = fade_window(t, anchor('P34.3') - 0.2, anchor('P34.4') + 1.0, 0.6, 0.8)
    L.text('factory-made pemmican', 960, 160, font('serif_i', 44, 500), INK, a * kt, align='center', shadow=1.0)
    ka = fade_window(t, anchor('P34.4') - 0.2, t - tl + dur, 0.6, 0.6)
    L.text("Amundsen's party: pemmican with oatmeal and dried peas", 960, 160, font('serif_i', 40, 500), INK, a * ka, align='center', shadow=1.0)
    return _finish_map(img, L, t)


def treaty_map(tl, dur, t):
    """P41.2–P41.3 (F8): the Buffalo Treaty, 2014, signed in Browning, Montana."""
    cam = _cam([(0, -112.6, 49.55, 290), (dur, -112.9, 49.5, 330)], tl)
    img = M.base(cam, relief=1.0, borders=0.9, graticule=0.0)
    L = Layer()
    a = fade_window(tl, 0, dur, 0.6, 0.8)
    M.area_label(L, cam, -111.0, 49.12, 'CANADA', a * 0.8, size=20, col=INK_DIM)
    M.area_label(L, cam, -111.0, 48.86, 'UNITED STATES', a * 0.8, size=20, col=INK_DIM)
    nations = [(-113.05, 48.25, 'Blackfeet'), (-113.25, 49.35, 'Blood Tribe (Kainai)'), (-113.95, 49.62, 'Piikani'),
               (-112.9, 50.82, 'Siksika')]
    for i, (lon, lat, name) in enumerate(nations):
        k = ease_out(seg(tl, 0.8 + i * 0.6, 1.6 + i * 0.6))
        M.marker(L, cam, lon, lat, name, a * k, kind='dot', col=OCHRE, label_size=30, italic=True)
    kb = fade_window(tl, 3.6, dur, 0.8, 0.8)
    M.marker(L, cam, *BROWNING, 'Browning, Montana', a * kb, kind='diamond', col=INK, label_size=22, label_dy=30, size=1.2)
    L.gradient_rect(0, 60, 1920, 240, [(0, DARK, 0.6 * a), (1, DARK, 0.0)])
    L.text('THE BUFFALO TREATY  ·  2014', 960, 150, font('sans', 34, 700), INK, a, align='center', tracking=8, shadow=1.0)
    L.text('signed by nations on both sides of the border', 960, 205, font('serif_i', 36, 500), INK_DIM, a, align='center', shadow=1.0)
    k3 = fade_window(t, anchor('P41.3') - 0.2, t - tl + dur, 0.7, 0.8)
    L.text('the first treaty among them in more than 150 years', 960, 980, font('serif_i', 38, 500), OCHRE, a * k3, align='center', shadow=1.0)
    _caption(L, a * (1 - k3), 'Four of the signatory nations shown; others also signed. Positions approximate.')
    return _finish_map(img, L, t)
