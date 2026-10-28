"""Animated cartography: orthographic projection, styled relief, Natural Earth vectors (public domain).

A map frame = MapCam(lon0, lat0, scale) + layers drawn with Skia + animated overlays
(routes that draw on, labels, markers, areas). Units: `scale` = pixels (at 1920 width) per
degree of arc at the projection centre (R = scale * 180/pi).
"""
import os, json, math, pickle, functools
import numpy as np
import cv2
import skia
from . import core, text as T
from .core import seg, ease_io, ease_out, clamp

MAPS = os.path.join(core.ROOT, 'assets/maps')
CACHE = os.path.join(MAPS, 'cache')
RELIEF = '/usr/local/lib/python3.13/dist-packages/mpl_toolkits/basemap_data/shadedrelief.jpg'

# palette
WATER = core.hexc('#121a20')
LAND = core.hexc('#2c281f')
LAKE_EDGE = '#3b5160'
RIVER = '#5b7787'
COAST = '#56656c'
BORDER = '#8d826f'
LABEL_WATER = '#94adb9'


# ------------------------------------------------------------------ data
def _load_geojson(name, bbox=None, kind='line'):
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f'{name}_{bbox}.pkl')
    if os.path.exists(cp):
        return pickle.load(open(cp, 'rb'))
    gj = json.load(open(os.path.join(MAPS, name + '.geojson')))
    out = []
    for f in gj['features']:
        g = f['geometry']
        if g is None:
            continue
        props = f.get('properties', {})
        if g['type'] in ('LineString', 'Polygon'):
            parts = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
        elif g['type'] in ('MultiLineString', 'MultiPolygon'):
            parts = g['coordinates'] if g['type'] == 'MultiLineString' else [r for poly in g['coordinates'] for r in poly]
        else:
            continue
        for p in parts:
            a = np.array(p, np.float64)[:, :2]
            if bbox:
                lo0, la0, lo1, la1 = bbox
                if a[:, 0].max() < lo0 or a[:, 0].min() > lo1 or a[:, 1].max() < la0 or a[:, 1].min() > la1:
                    continue
            out.append((a, {k: props.get(k) for k in ('name', 'scalerank', 'featurecla', 'NAME', 'ADMIN', 'min_zoom', 'strokeweig')}))
    pickle.dump(out, open(cp, 'wb'))
    return out


NA_BBOX = (-175, 20, -40, 85)


@functools.lru_cache(maxsize=None)
def layer(name, bbox=NA_BBOX):
    return _load_geojson(name, bbox)


@functools.lru_cache(maxsize=1)
def relief_tex():
    im = cv2.imread(RELIEF, cv2.IMREAD_COLOR)[:, :, ::-1].astype(np.float32) / 255.0
    lum = im @ np.array([0.3, 0.59, 0.11], np.float32)
    # hillshade-ish: normalise local contrast, tint to umber
    lum = cv2.GaussianBlur(lum, (0, 0), 1.0)
    shade = np.clip((lum - 0.25) * 1.6, 0, 1)
    base = np.array(LAND, np.float32)
    hi = np.array(core.hexc('#4d4434'), np.float32)
    tex = base[None, None] * (1 - shade[..., None]) + hi[None, None] * shade[..., None]
    return tex.astype(np.float32)


# ------------------------------------------------------------------ projection
class MapCam:
    def __init__(self, lon0, lat0, scale, rot=0.0):
        self.lon0, self.lat0, self.scale, self.rot = lon0, lat0, scale, rot
        self.R = scale * 180 / math.pi * core.W / 1920

    def project(self, lon, lat):
        """lon/lat arrays (deg) -> pixel x, y, visible mask."""
        l0, p0 = math.radians(self.lon0), math.radians(self.lat0)
        lam, phi = np.radians(lon), np.radians(lat)
        cosc = math.sin(p0) * np.sin(phi) + math.cos(p0) * np.cos(phi) * np.cos(lam - l0)
        x = self.R * np.cos(phi) * np.sin(lam - l0)
        y = self.R * (math.cos(p0) * np.sin(phi) - math.sin(p0) * np.cos(phi) * np.cos(lam - l0))
        if self.rot:
            a = math.radians(self.rot)
            x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        return core.W / 2 + x, core.H / 2 - y, cosc > 0

    def p(self, lon, lat):
        x, y, v = self.project(np.array([lon]), np.array([lat]))
        return float(x[0]), float(y[0])

    def inverse_grid(self, step=1):
        h, w = core.H // step, core.W // step
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        x = (xs * step - core.W / 2) / self.R
        y = -(ys * step - core.H / 2) / self.R
        if self.rot:
            a = -math.radians(self.rot)
            x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        rho = np.sqrt(x * x + y * y)
        valid = rho < 1.0
        c = np.arcsin(np.clip(rho, 0, 1))
        p0, l0 = math.radians(self.lat0), math.radians(self.lon0)
        with np.errstate(invalid='ignore', divide='ignore'):
            phi = np.arcsin(np.cos(c) * math.sin(p0) + np.where(rho > 0, y * np.sin(c) * math.cos(p0) / rho, 0))
            lam = l0 + np.arctan2(x * np.sin(c), rho * np.cos(c) * math.cos(p0) - y * np.sin(c) * math.sin(p0))
        return np.degrees(lam), np.degrees(phi), valid


def lerp_cam(keys, t):
    """keys: list of (time, lon, lat, scale[, rot]); smooth interpolation (log-scale zoom)."""
    if t <= keys[0][0]:
        k = keys[0]
        return MapCam(*k[1:4], k[4] if len(k) > 4 else 0)
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            u = ease_io(seg(t, a[0], b[0]))
            lon = a[1] + (b[1] - a[1]) * u
            lat = a[2] + (b[2] - a[2]) * u
            sc = math.exp(math.log(a[3]) + (math.log(b[3]) - math.log(a[3])) * u)
            rot = (a[4] if len(a) > 4 else 0) + ((b[4] if len(b) > 4 else 0) - (a[4] if len(a) > 4 else 0)) * u
            return MapCam(lon, lat, sc, rot)
    k = keys[-1]
    return MapCam(*k[1:4], k[4] if len(k) > 4 else 0)


# ------------------------------------------------------------------ base map
# Land/lake masks are pre-rasterized in lon/lat (equirectangular) space and resampled per frame.
GLOBAL_PPD = 24            # pixels per degree for the global mask (2.5 arcmin)
REGION = (-104.0, 46.0, -94.0, 53.5)   # Red River / Assiniboine detail window
REGION_PPD = 240


def _raster_eq(sources, bbox, ppd, lakes=True):
    lo0, la0, lo1, la1 = bbox
    w, h = int((lo1 - lo0) * ppd), int((la1 - la0) * ppd)
    m = np.zeros((h, w), np.uint8)

    def pts(a):
        x = (a[:, 0] - lo0) * ppd
        y = (la1 - a[:, 1]) * ppd
        return (np.c_[x, y] * 16).astype(np.int32)
    for src in sources:
        for a, _ in src:
            if a[:, 0].max() < lo0 or a[:, 0].min() > lo1 or a[:, 1].max() < la0 or a[:, 1].min() > la1:
                continue
            cv2.fillPoly(m, [pts(a)], 255, lineType=cv2.LINE_AA, shift=4)
    if lakes:
        for a, _ in layer('ne_10m_lakes'):
            if a[:, 0].max() < lo0 or a[:, 0].min() > lo1 or a[:, 1].max() < la0 or a[:, 1].min() > la1:
                continue
            cv2.fillPoly(m, [pts(a)], 0, lineType=cv2.LINE_AA, shift=4)
    return m


@functools.lru_cache(maxsize=4)
def land_raster(which):
    cp = os.path.join(CACHE, f'land_{which}.png')
    if os.path.exists(cp):
        return cv2.imread(cp, cv2.IMREAD_GRAYSCALE)
    if which == 'global':
        m = _raster_eq([layer('ne_10m_land', (-180, -90, 180, 90))], (-180, -90, 180, 90), GLOBAL_PPD)
    else:
        m = _raster_eq([layer('ne_10m_land')], REGION, REGION_PPD)
    cv2.imwrite(cp, m)
    return m


def _land_mask(cam):
    lon, lat, valid = cam.inverse_grid(step=2)
    g = land_raster('global')
    mx = ((lon + 180) * GLOBAL_PPD).astype(np.float32) % g.shape[1]
    my = ((90 - lat) * GLOBAL_PPD).astype(np.float32)
    m = cv2.remap(g, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP).astype(np.float32) / 255
    if cam.scale > 40:
        r = land_raster('region')
        lo0, la0, lo1, la1 = REGION
        rx = ((lon - lo0) * REGION_PPD).astype(np.float32)
        ry = ((la1 - lat) * REGION_PPD).astype(np.float32)
        inside = (lon > lo0 + 0.05) & (lon < lo1 - 0.05) & (lat > la0 + 0.05) & (lat < la1 - 0.05)
        rm = cv2.remap(r, rx, ry, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT).astype(np.float32) / 255
        m = np.where(inside, rm, m)
    m = m * valid
    return cv2.resize(m, (core.W, core.H), interpolation=cv2.INTER_LINEAR)


def _view_bbox(cam):
    lon, lat, valid = cam.inverse_grid(step=48)
    if not valid.any():
        return (-180, -90, 180, 90)
    lo, la = lon[valid], lat[valid]
    pad = 2.0
    return (lo.min() - pad, la.min() - pad, lo.max() + pad, la.max() + pad)


@functools.lru_cache(maxsize=None)
def _feature_bboxes(name, bbox):
    data = layer(name, bbox)
    return np.array([[a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()] for a, _ in data])


def _cv_lines(img, cam, name, col, alpha, width, bbox=NA_BBOX, max_rank=None, dash=False, vb=None):
    data = layer(name, bbox)
    if not data:
        return
    bbs = _feature_bboxes(name, bbox)
    vb = vb or _view_bbox(cam)
    sel = (bbs[:, 2] >= vb[0]) & (bbs[:, 0] <= vb[2]) & (bbs[:, 3] >= vb[1]) & (bbs[:, 1] <= vb[3])
    polys = []
    step = 1 if cam.scale > 30 else 2 if cam.scale > 12 else 4
    for i in np.nonzero(sel)[0]:
        a, pr = data[i]
        if max_rank is not None:
            r = pr.get('scalerank')
            if r is not None and r > max_rank:
                continue
        a = a[::step] if len(a) > 2 * step else a
        x, y, v = cam.project(a[:, 0], a[:, 1])
        if not v.all():
            continue
        pts = (np.c_[x, y] * 16).astype(np.int32)
        if dash:
            for k in range(0, len(pts) - 1, 2):
                polys.append(pts[k:k + 2])
        else:
            polys.append(pts)
    if not polys:
        return
    layer_ = np.zeros(img.shape[:2], np.float32)
    w = max(1, int(round(width * core.W / 1920)))
    cv2.polylines(layer_, polys, False, 1.0, thickness=w, lineType=cv2.LINE_AA, shift=4)
    a = (layer_ * alpha)[:, :, None]
    img *= (1 - a)
    img += np.array(core.hexc(col), np.float32) * a


def _lakes_edges(img, cam, vb):
    _cv_lines(img, cam, 'ne_10m_lakes', LAKE_EDGE, 0.7, 1.0, vb=vb)


def base(cam, relief=1.0, borders=0.35, graticule=0.06, rivers=1.0, detail='10m'):
    """Return float RGB base map for camera."""
    frame = core.blank(WATER)
    lon, lat, valid = cam.inverse_grid(step=2)
    tex = relief_tex()
    th, tw = tex.shape[:2]
    mx = ((lon + 180) / 360 * tw).astype(np.float32) % tw
    my = ((90 - lat) / 180 * th).astype(np.float32)
    rel = cv2.remap(tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    rel = cv2.resize(rel, (core.W, core.H), interpolation=cv2.INTER_LINEAR)
    vmask = cv2.resize(valid.astype(np.float32), (core.W, core.H), interpolation=cv2.INTER_LINEAR)[:, :, None]
    land = _land_mask(cam)[:, :, None]
    flat = np.array(LAND, np.float32)
    landc = flat + (rel - flat) * relief
    frame = frame * (1 - land) + landc * land
    frame = frame * vmask + np.array(core.hexc('#0b0d0f'), np.float32) * (1 - vmask)
    vb = _view_bbox(cam)
    if graticule:
        _cv_lines(frame, cam, 'ne_10m_graticules_10', '#c8bfae', graticule, 1.0, bbox=None, vb=vb)
    _lakes_edges(frame, cam, vb)
    if rivers:
        lw = 1.2 * clamp(cam.scale / 40, 0.8, 2.4)
        rank = 3 if cam.scale < 12 else 5 if cam.scale < 30 else 7 if cam.scale < 80 else 12
        _cv_lines(frame, cam, 'ne_10m_rivers_lake_centerlines', RIVER, 0.8 * rivers, lw, max_rank=rank, vb=vb)
        if cam.scale >= 30:
            _cv_lines(frame, cam, 'ne_10m_rivers_north_america', RIVER, 0.6 * rivers, lw * 0.8,
                      max_rank=9 if cam.scale < 80 else 12, vb=vb)
    _cv_lines(frame, cam, 'ne_10m_coastline' if cam.scale > 12 else 'ne_50m_coastline', COAST, 0.6, 1.0,
              bbox=NA_BBOX if cam.scale > 12 else None, vb=vb)
    if borders:
        _cv_lines(frame, cam, 'ne_10m_admin_0_boundary_lines_land', BORDER, borders, 1.3, dash=True, vb=vb)
        if cam.scale > 15:
            _cv_lines(frame, cam, 'ne_10m_admin_1_states_provinces_lines', BORDER, borders * 0.5, 1.0, dash=True, vb=vb)
    return frame


# ------------------------------------------------------------------ overlays
def route(L, cam, pts, progress, col=T.OCHRE, width=4.0, alpha=1.0, dash=None, glow=True, head=True,
          smooth=True):
    """Draw a lon/lat polyline up to `progress` (0..1 of its length) with a leading dot."""
    if progress <= 0:
        return None
    pts = np.array(pts, np.float64)
    if smooth and len(pts) > 2:
        pts = _catmull(pts, 12)
    x, y, v = cam.project(pts[:, 0], pts[:, 1])
    d = np.r_[0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    total = d[-1]
    cut = total * clamp(progress)
    k = np.searchsorted(d, cut)
    xs, ys = list(x[:k]), list(y[:k])
    if 0 < k < len(x):
        f = (cut - d[k - 1]) / max(d[k] - d[k - 1], 1e-6)
        xs.append(x[k - 1] + (x[k] - x[k - 1]) * f)
        ys.append(y[k - 1] + (y[k] - y[k - 1]) * f)
    if len(xs) < 2:
        return None
    path = skia.Path()
    path.moveTo(float(xs[0]), float(ys[0]))
    for a, b in zip(xs[1:], ys[1:]):
        path.lineTo(float(a), float(b))
    s = core.W / 1920
    if glow:
        gp = skia.Paint(AntiAlias=True, Color4f=T.color(col, 0.35 * alpha), Style=skia.Paint.kStroke_Style,
                        StrokeWidth=width * 3.2 * s)
        gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6 * s))
        gp.setStrokeCap(skia.Paint.kRound_Cap)
        L.c.drawPath(path, gp)
    p = skia.Paint(AntiAlias=True, Color4f=T.color(col, alpha), Style=skia.Paint.kStroke_Style, StrokeWidth=width * s)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    if dash:
        p.setPathEffect(skia.DashPathEffect.Make([q * s for q in dash], 0))
    L.c.drawPath(path, p)
    if head and progress < 0.999:
        L.c.drawCircle(float(xs[-1]), float(ys[-1]), width * 1.6 * s, skia.Paint(AntiAlias=True, Color4f=T.color('#fff3dc', alpha)))
    return xs[-1], ys[-1]


def _catmull(p, n):
    out = []
    P = np.vstack([p[0], p, p[-1]])
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(p[-1])
    return np.array(out)


def marker(L, cam, lon, lat, label=None, alpha=1.0, kind='dot', col=T.INK, label_dx=14, label_dy=-12,
           size=1.0, align='left', label_size=30, italic=False, pulse=0.0):
    if alpha <= 0:
        return
    x, y = cam.p(lon, lat)
    s = core.W / 1920
    X, Y = x / s, y / s
    if kind == 'dot':
        if pulse:
            L.circle(X, Y, 8 + 22 * pulse, col, alpha * (1 - pulse) * 0.6, stroke=2)
        L.circle(X, Y, 6 * size, '#0e1012', alpha * 0.7)
        L.circle(X, Y, 4.2 * size, col, alpha)
    elif kind == 'fort':
        L.rect(X - 7 * size, Y - 7 * size, 14 * size, 14 * size, '#0e1012', alpha * 0.8)
        L.rect(X - 5 * size, Y - 5 * size, 10 * size, 10 * size, col, alpha)
    elif kind == 'diamond':
        path = skia.Path()
        r = 7 * size * s
        path.addPoly([skia.Point(x, y - r), skia.Point(x + r, y), skia.Point(x, y + r), skia.Point(x - r, y)], True)
        L.c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=T.color(col, alpha)))
    if label:
        f = T.font('serif_i' if italic else 'serif', label_size, 600)
        L.text(label, X + label_dx, Y + label_dy, f, col if col != T.INK else T.INK, alpha, align=align, shadow=1.0)


def area_label(L, cam, lon, lat, txt, alpha=1.0, size=22, col=T.INK_DIM, tracking=7, italic=False):
    if alpha <= 0:
        return
    x, y = cam.p(lon, lat)
    s = core.W / 1920
    f = T.font('serif_i', size * 1.4, 500) if italic else T.font('sans', size, 600)
    L.text(txt if italic else txt.upper(), x / s, y / s, f, col, alpha, align='center',
           tracking=0 if italic else tracking, shadow=0.8)


def polygon(L, cam, pts, alpha=1.0, fill='#d39b45', fill_a=0.18, stroke='#d39b45', stroke_a=0.9, width=2.0,
            dash=(8, 6), progress=1.0):
    pts = np.array(pts, np.float64)
    x, y, v = cam.project(pts[:, 0], pts[:, 1])
    path = skia.Path()
    path.addPoly([skia.Point(float(a), float(b)) for a, b in zip(x, y)], True)
    s = core.W / 1920
    if fill_a:
        L.c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=T.color(fill, fill_a * alpha * progress)))
    if stroke_a:
        p = skia.Paint(AntiAlias=True, Color4f=T.color(stroke, stroke_a * alpha), Style=skia.Paint.kStroke_Style,
                       StrokeWidth=width * s)
        if dash:
            p.setPathEffect(skia.DashPathEffect.Make([d * s for d in dash], 0))
        if progress < 1:
            meas = skia.PathMeasure(path, False)
            seg_path = skia.Path()
            meas.getSegment(0, meas.getLength() * progress, seg_path, True)
            L.c.drawPath(seg_path, p)
        else:
            L.c.drawPath(path, p)


def country_outline(name):
    """Largest ring of a Natural Earth 50m country polygon (lon/lat)."""
    best = None
    for a, pr in layer('ne_50m_admin_0_countries', None):
        if (pr.get('ADMIN') or pr.get('NAME')) == name:
            if best is None or len(a) > len(best):
                best = a
    return best


def transplant(ring, src_center, dst_center):
    """Move a lon/lat ring so it keeps its true ground size at a new location (local tangent plane)."""
    lo0, la0 = src_center
    lo1, la1 = dst_center
    kx0 = math.cos(math.radians(la0))
    dx = (ring[:, 0] - lo0) * kx0
    dy = ring[:, 1] - la0
    out = np.empty_like(ring)
    out[:, 1] = la1 + dy
    out[:, 0] = lo1 + dx / np.cos(np.radians(out[:, 1]))
    return out
