"""Procedural props and environment pieces shared by the reconstruction scenes.

Everything here is generated from code (no third-party models). Shapes are deliberately
generic: they represent kinds of objects documented for the period (drying racks, hide lodges,
trade kettles, stone mauls, Red River carts, log forts), not specific surviving artifacts.
"""
import math, random
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import lib
from lib import node, link, srgb


# ---------------------------------------------------------------- mesh helpers
def mesh_obj(name, verts, faces, mat=None, smooth=True, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    o = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(o)
    if mat:
        me.materials.append(mat)
    if smooth:
        me.shade_smooth() if hasattr(me, 'shade_smooth') else None
        for p in me.polygons:
            p.use_smooth = True
    return o


def join(objs, name):
    """Join mesh objects into one (keeps material slots)."""
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    bm = bmesh.new()
    mats = []
    for o in objs:
        me = o.data
        tmp = bmesh.new()
        tmp.from_mesh(me)
        tmp.transform(o.matrix_world)
        offs = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            offs.append(mats.index(m))
        for f in tmp.faces:
            if offs:
                f.material_index = offs[min(f.material_index, len(offs) - 1)]
        me2 = bpy.data.meshes.new('tmp')
        tmp.to_mesh(me2)
        bm.from_mesh(me2)
        bpy.data.meshes.remove(me2)
        tmp.free()
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    return o


def tube(name, pts, radii, mat=None, segs=8, cap=True, twist=0.0):
    """Generalized cylinder along a polyline. radii: scalar or per-point list."""
    pts = [Vector(p) for p in pts]
    if not hasattr(radii, '__len__'):
        radii = [radii] * len(pts)
    verts, faces = [], []
    prev_n = None
    for i, p in enumerate(pts):
        if i == 0:
            d = (pts[1] - pts[0])
        elif i == len(pts) - 1:
            d = (pts[-1] - pts[-2])
        else:
            d = (pts[i + 1] - pts[i - 1])
        d.normalize()
        if prev_n is None:
            a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
            n = d.cross(a).normalized()
        else:
            n = (prev_n - d * prev_n.dot(d)).normalized()
        prev_n = n
        b = d.cross(n)
        for k in range(segs):
            ang = 2 * math.pi * k / segs + twist * i
            verts.append(p + (n * math.cos(ang) + b * math.sin(ang)) * radii[i])
    for i in range(len(pts) - 1):
        for k in range(segs):
            a0 = i * segs + k
            a1 = i * segs + (k + 1) % segs
            faces.append((a0, a1, a1 + segs, a0 + segs))
    if cap:
        verts.append(pts[0]); verts.append(pts[-1])
        c0, c1 = len(verts) - 2, len(verts) - 1
        last = (len(pts) - 1) * segs
        for k in range(segs):
            faces.append((c0, (k + 1) % segs, k))
            faces.append((c1, last + k, last + (k + 1) % segs))
    return mesh_obj(name, verts, faces, mat)


def pole(name, a, b, r0, r1=None, mat=None, segs=8, bend=0.0, seed=0, n=6):
    """Slightly irregular wooden pole from a to b."""
    rnd = random.Random(seed)
    a, b = Vector(a), Vector(b)
    side = (b - a).cross(Vector((0, 0, 1)))
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize()
    pts, rad = [], []
    for i in range(n):
        f = i / (n - 1)
        p = a.lerp(b, f) + side * (math.sin(f * math.pi) * bend) + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * r0 * 0.15
        pts.append(p)
        rad.append(lerp(r0, r1 if r1 is not None else r0 * 0.7, f) * rnd.uniform(0.92, 1.08))
    return tube(name, pts, rad, mat, segs)


def lerp(a, b, t):
    return a + (b - a) * t


def lathe(name, profile, mat=None, segs=40, close_top=False):
    """Surface of revolution about Z. profile: list of (r, z) from bottom centre outward/up."""
    verts, faces = [], []
    for (r, z) in profile:
        for k in range(segs):
            a = 2 * math.pi * k / segs
            verts.append((r * math.cos(a), r * math.sin(a), z))
    n = len(profile)
    for i in range(n - 1):
        for k in range(segs):
            a0 = i * segs + k
            a1 = i * segs + (k + 1) % segs
            faces.append((a0, a1, a1 + segs, a0 + segs))
    return mesh_obj(name, verts, faces, mat)


def displace(o, strength=0.01, scale=4.0, seed=0, axis=None):
    """Noise displacement of mesh vertices along normals (in object space)."""
    me = o.data
    me.update()
    off = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    for v in me.vertices:
        d = noise.noise(v.co * scale + off)
        if axis is None:
            v.co += v.normal * d * strength
        else:
            v.co += Vector(axis) * d * strength
    me.update()


# ---------------------------------------------------------------- materials
def mat_principled(name, base, rough=0.7, spec=0.5, sss=0.0, sss_col=None, sss_rad=(0.1, 0.05, 0.02),
                   emit=None, emit_strength=0.0, bump_scale=None, bump_strength=0.0, var=0.0, var_scale=6.0,
                   dark=None, transl=0.0, metallic=0.0, sheen=0.0, coat=0.0):
    """Principled material with optional noise colour variation (base<->dark) and bump."""
    m, nt, b, out = lib.mat_new(name)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metallic
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = spec
    if var > 0 and dark:
        tc = node(nt, 'ShaderNodeTexCoord', (-1100, 0))
        nz = node(nt, 'ShaderNodeTexNoise', (-900, 0))
        nz.inputs['Scale'].default_value = var_scale
        nz.inputs['Detail'].default_value = 6.0
        link(nt, tc.outputs['Object'], nz.inputs['Vector'])
        cr = lib.color_ramp(nt, [(0.5 - var * 0.5, srgb(dark)), (0.5 + var * 0.5, srgb(base))], (-650, 0))
        link(nt, nz.outputs['Fac'], cr.inputs['Fac'])
        link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    else:
        b.inputs['Base Color'].default_value = (*srgb(base), 1)
    if sss > 0:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = sss_rad
    if transl > 0 and 'Transmission Weight' in b.inputs:
        pass
    if emit:
        b.inputs['Emission Color'].default_value = (*srgb(emit), 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    if sheen and 'Sheen Weight' in b.inputs:
        b.inputs['Sheen Weight'].default_value = sheen
    if coat and 'Coat Weight' in b.inputs:
        b.inputs['Coat Weight'].default_value = coat
    if bump_strength:
        tc = nt.nodes.get('Texture Coordinate') or node(nt, 'ShaderNodeTexCoord', (-1100, -300))
        nz2 = node(nt, 'ShaderNodeTexNoise', (-700, -350))
        nz2.inputs['Scale'].default_value = bump_scale or 40.0
        nz2.inputs['Detail'].default_value = 8.0
        link(nt, tc.outputs['Object'], nz2.inputs['Vector'])
        bp = node(nt, 'ShaderNodeBump', (-300, -350))
        bp.inputs['Strength'].default_value = bump_strength
        link(nt, nz2.outputs['Fac'], bp.inputs['Height'])
        link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_translucent_mix(name, base, transl_col, mix=0.35, rough=0.6, var_dark=None, var=0.0, bump=0.0, scale=8.0):
    """Diffuse/principled mixed with translucency: thin backlit things (meat strips, hide lodge covers, leaves)."""
    m, nt, b, out = lib.mat_new(name)
    b.inputs['Roughness'].default_value = rough
    tc = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
    nz = node(nt, 'ShaderNodeTexNoise', (-1000, 0))
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 7.0
    link(nt, tc.outputs['Object'], nz.inputs['Vector'])
    if var_dark and var > 0:
        cr = lib.color_ramp(nt, [(0.5 - var * 0.5, srgb(var_dark)), (0.5 + var * 0.5, srgb(base))], (-750, 0))
        link(nt, nz.outputs['Fac'], cr.inputs['Fac'])
        link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    else:
        b.inputs['Base Color'].default_value = (*srgb(base), 1)
    tr = node(nt, 'ShaderNodeBsdfTranslucent', (-200, -250))
    tr.inputs['Color'].default_value = (*srgb(transl_col), 1)
    mx = node(nt, 'ShaderNodeMixShader', (200, 0))
    mx.inputs['Fac'].default_value = mix
    link(nt, b.outputs['BSDF'], mx.inputs[1])
    link(nt, tr.outputs['BSDF'], mx.inputs[2])
    link(nt, mx.outputs['Shader'], out.inputs['Surface'])
    if bump:
        bp = node(nt, 'ShaderNodeBump', (-400, -400))
        bp.inputs['Strength'].default_value = bump
        link(nt, nz.outputs['Fac'], bp.inputs['Height'])
        link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_emit(name, col, strength):
    m, nt, b, out = lib.mat_new(name)
    em = node(nt, 'ShaderNodeEmission', (0, 0))
    em.inputs['Color'].default_value = (*srgb(col), 1)
    em.inputs['Strength'].default_value = strength
    link(nt, em.outputs['Emission'], out.inputs['Surface'])
    return m


def mat_flame(name='Flame', strength=18.0):
    """Emissive flame with vertical falloff to transparent (object Z in 0..1)."""
    m, nt, b, out = lib.mat_new(name)
    tc = node(nt, 'ShaderNodeTexCoord', (-1000, 0))
    sep = node(nt, 'ShaderNodeSeparateXYZ', (-800, 0))
    link(nt, tc.outputs['Generated'], sep.inputs['Vector'])
    cr = lib.color_ramp(nt, [(0.0, (1.0, 0.55, 0.12)), (0.55, (1.0, 0.32, 0.04)), (1.0, (0.6, 0.08, 0.01))], (-550, 100))
    link(nt, sep.outputs['Z'], cr.inputs['Fac'])
    fade = lib.color_ramp(nt, [(0.0, (1, 1, 1)), (0.35, (0.9, 0.9, 0.9)), (1.0, (0, 0, 0))], (-550, -200))
    link(nt, sep.outputs['Z'], fade.inputs['Fac'])
    em = node(nt, 'ShaderNodeEmission', (-200, 100))
    link(nt, cr.outputs['Color'], em.inputs['Color'])
    em.inputs['Strength'].default_value = strength
    tr = node(nt, 'ShaderNodeBsdfTransparent', (-200, -100))
    mx = node(nt, 'ShaderNodeMixShader', (100, 0))
    link(nt, fade.outputs['Color'], mx.inputs['Fac'])
    link(nt, tr.outputs['BSDF'], mx.inputs[1])
    link(nt, em.outputs['Emission'], mx.inputs[2])
    link(nt, mx.outputs['Shader'], out.inputs['Surface'])
    return m


def mat_ground(name, base, dark, rough=0.95, scale=0.08, emit=None, emit_strength=0.0, bump=0.3, dry=None):
    """Large-scale ground: two-octave colour patches + fine bump, optional aerial-perspective emission."""
    m, nt, b, out = lib.mat_new(name)
    b.inputs['Roughness'].default_value = rough
    tc = node(nt, 'ShaderNodeTexCoord', (-1300, 0))
    n1 = node(nt, 'ShaderNodeTexNoise', (-1100, 100))
    n1.inputs['Scale'].default_value = scale
    n1.inputs['Detail'].default_value = 6
    link(nt, tc.outputs['Object'], n1.inputs['Vector'])
    stops = [(0.35, srgb(dark)), (0.65, srgb(base))]
    cr = lib.color_ramp(nt, stops, (-850, 100))
    link(nt, n1.outputs['Fac'], cr.inputs['Fac'])
    col = cr.outputs['Color']
    if dry:
        n3 = node(nt, 'ShaderNodeTexNoise', (-1100, -150))
        n3.inputs['Scale'].default_value = scale * 7
        n3.inputs['Detail'].default_value = 4
        link(nt, tc.outputs['Object'], n3.inputs['Vector'])
        cr3 = lib.color_ramp(nt, [(0.45, (0, 0, 0)), (0.7, (1, 1, 1))], (-850, -150))
        link(nt, n3.outputs['Fac'], cr3.inputs['Fac'])
        mx = node(nt, 'ShaderNodeMix', (-500, 50), data_type='RGBA')
        link(nt, cr3.outputs['Color'], mx.inputs['Factor'])
        link(nt, col, mx.inputs[6])
        mx.inputs[7].default_value = (*srgb(dry), 1)
        col = mx.outputs[2]
    link(nt, col, b.inputs['Base Color'])
    if bump:
        n2 = node(nt, 'ShaderNodeTexNoise', (-900, -400))
        n2.inputs['Scale'].default_value = 60
        n2.inputs['Detail'].default_value = 8
        link(nt, tc.outputs['Object'], n2.inputs['Vector'])
        bp = node(nt, 'ShaderNodeBump', (-400, -400))
        bp.inputs['Strength'].default_value = bump
        link(nt, n2.outputs['Fac'], bp.inputs['Height'])
        link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    if emit:
        b.inputs['Emission Color'].default_value = (*srgb(emit), 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    return m


def mat_strand(name, root, tip, rough=0.6, transl=0.25):
    """Material for grass curves: colour graded root->tip via the curve intercept."""
    m, nt, b, out = lib.mat_new(name)
    b.inputs['Roughness'].default_value = rough
    ci = node(nt, 'ShaderNodeHairInfo', (-900, 0))
    cr = lib.color_ramp(nt, [(0.0, srgb(root)), (1.0, srgb(tip))], (-650, 0))
    link(nt, ci.outputs['Intercept'], cr.inputs['Fac'])
    # per-strand random tint
    cr2 = lib.color_ramp(nt, [(0.0, (0.75, 0.75, 0.75)), (1.0, (1.15, 1.1, 1.0))], (-650, -250))
    link(nt, ci.outputs['Random'], cr2.inputs['Fac'])
    mul = node(nt, 'ShaderNodeMix', (-350, 0), data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    link(nt, cr.outputs['Color'], mul.inputs[6])
    link(nt, cr2.outputs['Color'], mul.inputs[7])
    link(nt, mul.outputs[2], b.inputs['Base Color'])
    if transl:
        tr = node(nt, 'ShaderNodeBsdfTranslucent', (-100, -250))
        link(nt, mul.outputs[2], tr.inputs['Color'])
        mx = node(nt, 'ShaderNodeMixShader', (200, 0))
        mx.inputs['Fac'].default_value = transl
        link(nt, b.outputs['BSDF'], mx.inputs[1])
        link(nt, tr.outputs['BSDF'], mx.inputs[2])
        link(nt, mx.outputs['Shader'], out.inputs['Surface'])
    return m


# ---------------------------------------------------------------- terrain + grass
class Terrain:
    """Heightfield z = f(x, y) built from layered noise; sampled for object placement."""

    def __init__(self, amp=1.0, scale=0.01, seed=0, amp2=0.15, scale2=0.08, flat_r=0.0, flat_c=(0, 0)):
        self.amp, self.scale, self.seed, self.amp2, self.scale2 = amp, scale, seed, amp2, scale2
        self.flat_r, self.flat_c = flat_r, flat_c

    def z(self, x, y):
        o = Vector((self.seed * 13.1, self.seed * 7.7, 0))
        h = noise.noise(Vector((x * self.scale, y * self.scale, 0)) + o) * self.amp
        h += noise.noise(Vector((x * self.scale2, y * self.scale2, 1.3)) + o) * self.amp2
        if self.flat_r:
            d = math.hypot(x - self.flat_c[0], y - self.flat_c[1])
            k = min(1.0, d / self.flat_r) ** 2
            h *= k
        return h

    def mesh(self, name, x0, x1, y0, y1, nx, ny, mat=None):
        xs = np.linspace(x0, x1, nx)
        ys = np.linspace(y0, y1, ny)
        verts = [(x, y, self.z(x, y)) for y in ys for x in xs]
        faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
        return mesh_obj(name, verts, faces, mat)


def grass_curves(name, terrain, region, density, height, mat, seed=0, lean=(0.0, 0.0), lean_var=0.25,
                 radius=0.0018, points=5, clump=0.0, max_strands=600000, mask=None, curl=0.0):
    """Grass blades as a native Curves object. region=(x0,x1,y0,y1); height=(min,max).
    mask(x, y) -> 0..1 optional density mask."""
    rng = np.random.default_rng(seed)
    x0, x1, y0, y1 = region
    n = int(min(max_strands * 2, (x1 - x0) * (y1 - y0) * density))
    xs = rng.uniform(x0, x1, n)
    ys = rng.uniform(y0, y1, n)
    keep = np.ones(n, bool)
    if mask is not None:
        mv = np.array([mask(x, y) for x, y in zip(xs, ys)])
        keep = rng.random(n) < mv
    if clump:
        cv = np.array([noise.noise(Vector((x * 0.9, y * 0.9, 5.0))) for x, y in zip(xs, ys)]) * 0.5 + 0.5
        keep &= rng.random(n) < np.clip((cv - clump * 0.5) / 0.3, 0.05, 1)
    xs, ys = xs[keep], ys[keep]
    if len(xs) > max_strands:
        pick = rng.choice(len(xs), max_strands, replace=False)
        xs, ys = xs[pick], ys[pick]
    m = len(xs)
    zs = np.array([terrain.z(x, y) for x, y in zip(xs, ys)]) if terrain else np.zeros(m)
    hn = np.array([noise.noise(Vector((x * 0.35, y * 0.35, 2.0))) for x, y in zip(xs, ys)]) * 0.5 + 0.5
    H = height[0] + (height[1] - height[0]) * (0.5 * rng.random(m) + 0.5 * hn)
    ang = rng.uniform(0, 2 * math.pi, m)
    lx = lean[0] + np.cos(ang) * lean_var
    ly = lean[1] + np.sin(ang) * lean_var
    t = np.linspace(0, 1, points)
    pos = np.empty((m, points, 3), np.float32)
    ph = rng.uniform(0, 6.28, m)
    for k, tk in enumerate(t):
        bend = tk ** 2
        pos[:, k, 0] = xs + lx * H * bend + (np.sin(ph + tk * 4) * curl * H * tk if curl else 0)
        pos[:, k, 1] = ys + ly * H * bend
        pos[:, k, 2] = zs - 0.02 + H * tk * (1 - 0.25 * bend * (lx ** 2 + ly ** 2))
    rad = np.repeat((radius * (1.0 - 0.85 * t))[None], m, 0).astype(np.float32)
    hc = bpy.data.hair_curves.new(name)
    hc.add_curves([points] * m)
    hc.attributes['position'].data.foreach_set('vector', pos.reshape(-1))
    rattr = hc.attributes.get('radius') or hc.attributes.new('radius', 'FLOAT', 'POINT')
    rattr.data.foreach_set('value', rad.reshape(-1))
    hc.materials.append(mat)
    o = bpy.data.objects.new(name, hc)
    bpy.context.scene.collection.objects.link(o)
    print(f'grass: {m} blades in {name}', flush=True)
    return o


# ---------------------------------------------------------------- camp props
def lodge(name, loc, r=2.4, h=4.4, cover=None, poles=None, seed=0, n_poles=12, terrain=None):
    """Hide-covered lodge: conical cover (open at top, door gap) with poles crossing above."""
    rnd = random.Random(seed)
    x, y = loc
    z0 = terrain.z(x, y) if terrain else 0.0
    segs = 28
    rings = 10
    verts, faces = [], []
    top = 0.86
    door = rnd.uniform(0, 6.28)
    for i in range(rings + 1):
        f = i / rings * top
        rr = r * (1 - f)
        for k in range(segs + 1):
            a = 2 * math.pi * k / segs
            sag = 0.035 * r * math.sin(a * n_poles / 2) ** 2 * (1 - f)     # cover sags between poles
            rr2 = rr - sag
            verts.append((x + rr2 * math.cos(a), y + rr2 * math.sin(a), z0 + h * f))
    for i in range(rings):
        for k in range(segs):
            a = 2 * math.pi * (k + 0.5) / segs
            if i < 3 and abs(((a - door + math.pi) % (2 * math.pi)) - math.pi) < 0.22:
                continue
            a0 = i * (segs + 1) + k
            faces.append((a0, a0 + 1, a0 + segs + 2, a0 + segs + 1))
    cov = mesh_obj(name, verts, faces, cover)
    sol = cov.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.01
    parts = [cov]
    apex = Vector((x, y, z0 + h * 0.9))
    for k in range(n_poles):
        a = 2 * math.pi * k / n_poles + rnd.uniform(-0.05, 0.05)
        base = Vector((x + r * 1.0 * math.cos(a), y + r * 1.0 * math.sin(a), z0))
        d = (apex - base)
        tip = apex + d.normalized() * rnd.uniform(0.9, 1.6)
        parts.append(pole(f'{name}_pole{k}', base, tip, 0.035, 0.018, poles, segs=6, seed=seed * 31 + k, n=4))
    return parts


def rack(name, a, b, height=1.55, wood=None, seed=0, terrain=None, lower=None):
    """Meat-drying rack: forked uprights at each end carrying a horizontal pole (and an optional lower pole)."""
    rnd = random.Random(seed)
    a, b = Vector(a), Vector(b)
    za = terrain.z(a.x, a.y) if terrain else 0
    zb = terrain.z(b.x, b.y) if terrain else 0
    objs = []
    for i, (p, z) in enumerate(((a, za), (b, zb))):
        lean = Vector((rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), 0))
        top = Vector((p.x, p.y, z + height)) + lean
        objs.append(pole(f'{name}_up{i}', (p.x, p.y, z - 0.1), top, 0.045, 0.035, wood, seed=seed + i))
        # fork
        objs.append(pole(f'{name}_fk{i}', top - Vector((0, 0, 0.18)), top + Vector((0.09, 0.05, 0.12)), 0.025, 0.015, wood, seed=seed + 7 + i, n=3))
    pa = Vector((a.x, a.y, za + height)) + (a - b).normalized() * 0.25
    pb = Vector((b.x, b.y, zb + height)) + (b - a).normalized() * 0.25
    objs.append(pole(f'{name}_bar', pa, pb, 0.032, 0.028, wood, seed=seed + 3, bend=-0.03, n=8))
    bars = [(pa, pb)]
    if lower:
        la = Vector((a.x, a.y, za + lower)); lb = Vector((b.x, b.y, zb + lower))
        objs.append(pole(f'{name}_bar2', la, lb, 0.028, 0.025, wood, seed=seed + 5, bend=-0.02, n=8))
        bars.append((la, lb))
    return objs, bars


def meat_strip(name, bar_pt, bar_dir, mat, width=0.14, length=0.8, seed=0, bar_r=0.035, split=0.5):
    """Thin sheet of meat draped over a pole: hangs on both sides, wrinkled, slightly twisted."""
    rnd = random.Random(seed)
    bar_dir = Vector(bar_dir).normalized()
    side = bar_dir.cross(Vector((0, 0, 1))).normalized()
    nl = 20
    nw = 6
    la = length * split
    lb = length * (1 - split)
    pts = []
    # path: down side A, over the bar, down side B
    for i in range(nl + 1):
        f = i / nl
        if f < 0.42:
            g = f / 0.42
            off = side * (bar_r + 0.004 + g * 0.02 * rnd.uniform(0.5, 1.5)) + Vector((0, 0, -la * (1 - g)))
        elif f > 0.58:
            g = (f - 0.58) / 0.42
            off = -side * (bar_r + 0.004 + g * 0.02 * rnd.uniform(0.5, 1.5)) + Vector((0, 0, -lb * g))
        else:
            g = (f - 0.42) / 0.16
            ang = math.pi * g
            off = side * math.cos(ang) * (bar_r + 0.004) + Vector((0, 0, math.sin(ang) * (bar_r + 0.004)))
        pts.append(Vector(bar_pt) + off)
    verts, faces = [], []
    tw = rnd.uniform(-0.35, 0.35)
    cut0, cut1 = rnd.uniform(0.0, 0.06), rnd.uniform(0.0, 0.06)
    for i, p in enumerate(pts):
        f = i / nl
        wv = width * (0.75 + 0.5 * (noise.noise(Vector((f * 4.5, seed * 0.37, 0.5))) * 0.5 + 0.5))
        if f < 0.08 or f > 0.92:
            wv *= rnd.uniform(0.45, 0.8)
        for j in range(nw + 1):
            g = j / nw - 0.5
            gg = g + (cut0 * (1 - f) - cut1 * f) * (1 if g > 0 else -1)
            curl = (abs(g) * 2) ** 2 * 0.018 * (0.5 + noise.noise(Vector((f * 6, seed, 1.0))))
            q = p + bar_dir * (gg * wv) + side * (math.sin(f * 11 + j * 0.7 + seed) * 0.008 + tw * g * 0.08 * abs(f - 0.5) + curl)
            q += Vector((noise.noise(q * 25 + Vector((seed, 0, 0))), noise.noise(q * 25 + Vector((0, seed, 0))), 0)) * 0.012
            verts.append(q)
    for i in range(nl):
        for j in range(nw):
            a0 = i * (nw + 1) + j
            faces.append((a0, a0 + 1, a0 + nw + 2, a0 + nw + 1))
    o = mesh_obj(name, verts, faces, mat)
    sol = o.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.0032
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    return o


def drape_bar(prefix, pa, pb, mat, spacing=0.17, seed=0, length=(0.55, 0.95), fill=0.85, bar_r=0.035):
    rnd = random.Random(seed)
    pa, pb = Vector(pa), Vector(pb)
    d = pb - pa
    L = d.length
    n = int(L / spacing)
    out = []
    for i in range(n):
        if rnd.random() > fill:
            continue
        f = (i + 0.5 + rnd.uniform(-0.2, 0.2)) / n
        p = pa.lerp(pb, f)
        out.append(meat_strip(f'{prefix}{i}', p, d, mat, width=rnd.uniform(0.10, 0.16),
                              length=rnd.uniform(*length), seed=seed * 100 + i, bar_r=bar_r, split=rnd.uniform(0.4, 0.6)))
    return out


def stone(name, size, loc, mat, seed=0, rough=0.25, scale=2.5):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.data.materials.append(mat)
    displace(o, rough, scale, seed)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def maul(name, loc, rot_z, stone_mat, wood, thong, seed=0):
    """Stone maul: egg-shaped grooved stone hafted on a short wooden handle with a rawhide wrap."""
    x, y, z = loc
    s = stone(name + '_head', (0.075, 0.062, 0.058), (0, 0, 0), stone_mat, seed, 0.08, 3.0)
    h = pole(name + '_handle', (-0.02, 0, 0.0), (-0.42, 0.01, 0.03), 0.018, 0.015, wood, seed=seed)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.064, minor_radius=0.011, location=(0, 0, 0), rotation=(0, math.pi / 2, 0))
    t = bpy.context.active_object; t.name = name + '_wrap'; t.scale = (1.0, 0.97, 0.92); t.data.materials.append(thong)
    o = join([s, h, t], name)
    o.location = (x, y, z + 0.055)
    o.rotation_euler = (0, 0, rot_z)
    return o


def hide_flat(name, loc, size, mat, seed=0, rot=0.0, wrinkle=0.012, terrain=None):
    """A hide spread on the ground: irregular outline with leg lobes, gentle wrinkles."""
    rnd = random.Random(seed)
    nx, ny = 26, 20
    sx, sy = size
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx - 0.5, j / ny - 0.5
            verts.append([u * sx, v * sy, 0.0])
    for j in range(ny):
        for i in range(nx):
            u, v = (i + 0.5) / nx - 0.5, (j + 0.5) / ny - 0.5
            ang = math.atan2(v / sy * sx, u)
            r = math.hypot(u * 2, v * 2)
            lobes = 0.86 + 0.12 * math.cos(4 * ang + 0.6) + 0.05 * noise.noise(Vector((math.cos(ang) * 2, math.sin(ang) * 2, seed)))
            if r < lobes:
                a0 = j * (nx + 1) + i
                faces.append((a0, a0 + 1, a0 + nx + 2, a0 + nx + 1))
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for vx, vy, vz in verts:
        X = loc[0] + vx * c - vy * s
        Y = loc[1] + vx * s + vy * c
        Z = (terrain.z(X, Y) if terrain else loc[2]) + 0.012 + noise.noise(Vector((vx * 3.5, vy * 3.5, seed))) * wrinkle
        out.append((X, Y, Z))
    o = mesh_obj(name, out, faces, mat)
    sol = o.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.006
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    return o


def mound(name, loc, r, h, mat, seed=0, chunks=0, chunk_mat=None, terrain_z=0.0):
    """Pile of pounded dried meat: a lumpy low mound plus scattered crumbs."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=1.0, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    me = o.data
    for v in me.vertices:
        z = v.co.z
        if z < 0:
            v.co.z = z * 0.05
        v.co.x *= r; v.co.y *= r; v.co.z *= h
    displace(o, r * 0.12, 4.0 / r, seed)
    displace(o, r * 0.05, 22.0 / r, seed + 3)
    displace(o, r * 0.025, 70.0 / r, seed + 5)
    o.location = (loc[0], loc[1], terrain_z + 0.01)
    o.data.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    parts = [o]
    if chunks:
        rnd = random.Random(seed)
        bm = bmesh.new()
        for i in range(chunks):
            a = rnd.uniform(0, 6.28); d = r * math.sqrt(rnd.uniform(0.0, 1.0)) * 1.25
            px, py = loc[0] + d * math.cos(a), loc[1] + d * math.sin(a)
            rr = rnd.uniform(0.002, 0.008)
            g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rr)
            for v in g['verts']:
                v.co.x *= rnd.uniform(0.6, 1.6); v.co.z *= 0.6
                v.co += Vector((px, py, terrain_z + 0.014 + max(0, h * (1 - (d / r) ** 2)) * (1 if d < r else 0)))
        me2 = bpy.data.meshes.new(name + '_crumbs')
        bm.to_mesh(me2); bm.free()
        c = bpy.data.objects.new(name + '_crumbs', me2)
        bpy.context.scene.collection.objects.link(c)
        me2.materials.append(chunk_mat or mat)
        parts.append(c)
    return parts


def kettle(name, loc, mat, liquid=None, scale=1.0, bail_mat=None):
    """Trade kettle (sheet copper/brass): flat-bottomed, flared, with rolled rim and iron bail."""
    prof = [(0.0, 0.0), (0.11, 0.0), (0.135, 0.012), (0.15, 0.05), (0.158, 0.12), (0.162, 0.17), (0.166, 0.185),
            (0.172, 0.19), (0.168, 0.196), (0.158, 0.19), (0.152, 0.17), (0.148, 0.12), (0.14, 0.05), (0.125, 0.014),
            (0.105, 0.008), (0.0, 0.008)]
    prof = [(r * scale, z * scale) for r, z in prof]
    o = lathe(name, prof, mat, segs=48)
    parts = [o]
    if liquid:
        bpy.ops.mesh.primitive_circle_add(vertices=48, radius=0.148 * scale, fill_type='NGON', location=(0, 0, 0.16 * scale))
        lq = bpy.context.active_object; lq.name = name + '_fat'; lq.data.materials.append(liquid)
        parts.append(lq)
    if bail_mat:
        pts = [(0.17 * scale * math.cos(a), 0, 0.18 * scale + 0.17 * scale * math.sin(a)) for a in np.linspace(0, math.pi, 16)]
        parts.append(tube(name + '_bail', pts, 0.0035 * scale, bail_mat, segs=6))
    for p in parts:
        p.location = Vector(p.location) + Vector(loc)
    return parts


def fire(name, loc, log_mat, flame_mat, ember_mat, seed=0, scale=1.0):
    """Small cooking fire: crossed logs, a few emissive flame tongues, ember bed and a warm point light."""
    rnd = random.Random(seed)
    x, y, z = loc
    parts = []
    for i in range(5):
        a = rnd.uniform(0, 6.28)
        L = rnd.uniform(0.35, 0.55) * scale
        c = Vector((x, y, z + 0.04 * scale))
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(pole(f'{name}_log{i}', c - d * L * 0.15 + Vector((0, 0, 0.03)), c + d * L, 0.035 * scale, 0.03 * scale, log_mat, seed=seed + i, n=4))
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=0.2 * scale, fill_type='NGON', location=(x, y, z + 0.015))
    eb = bpy.context.active_object; eb.name = name + '_embers'; eb.data.materials.append(ember_mat)
    parts.append(eb)
    flames = []
    for i in range(7):
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=rnd.uniform(0.04, 0.08) * scale, radius2=0.0,
                                        depth=rnd.uniform(0.18, 0.38) * scale,
                                        location=(x + rnd.uniform(-0.08, 0.08) * scale, y + rnd.uniform(-0.08, 0.08) * scale, z))
        f = bpy.context.active_object
        f.name = f'{name}_flame{i}'
        me = f.data
        for v in me.vertices:
            v.co.z += f.dimensions.z / 2
            k = v.co.z / max(f.dimensions.z, 1e-3)
            v.co.x += math.sin(k * 5 + i) * 0.02 * scale * k
        f.location.z = z + 0.03 * scale
        f.data.materials.append(flame_mat)
        sub = f.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
        flames.append(f)
    parts += flames
    lib.point_light(name + '_light', (x, y, z + 0.35 * scale), 160 * scale, color=(1.0, 0.55, 0.22), radius=0.12 * scale)
    return parts


def bowl(name, loc, mat, r=0.13, h=0.07):
    prof = [(0, 0.0), (r * 0.55, 0.0), (r * 0.8, h * 0.25), (r * 0.97, h * 0.75), (r, h), (r * 0.94, h * 1.0),
            (r * 0.9, h * 0.75), (r * 0.74, h * 0.3), (r * 0.5, h * 0.12), (0, h * 0.12)]
    o = lathe(name, prof, mat, segs=48)
    o.location = loc
    return o


def berries(name, centre, radius, height, mat, n=160, seed=0, size=(0.006, 0.0085), dome=True):
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        a = rnd.uniform(0, 6.28); d = radius * math.sqrt(rnd.random())
        zz = height * (1 - (d / radius) ** 2) * (rnd.uniform(0.4, 1.0) if dome else 0)
        rr = rnd.uniform(*size)
        g = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=rr)
        for v in g['verts']:
            v.co *= 1 + 0.18 * noise.noise(v.co * 900 + Vector((i, 0, 0)))   # wrinkled, drying skin
            v.co += Vector((centre[0] + d * math.cos(a), centre[1] + d * math.sin(a), centre[2] + zz + rr * 0.8))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return o


def frame_hide(name, loc, rot_z, wood, hide_mat, w=1.6, h=1.9, seed=0, terrain=None):
    """A hide laced into a pole frame for scraping/drying, leaning back slightly."""
    x, y = loc
    z0 = terrain.z(x, y) if terrain else 0
    parts = []
    corners = [(-w / 2, 0), (w / 2, 0)]
    lean = 0.18
    for i, (dx, _) in enumerate(corners):
        parts.append(pole(f'{name}_side{i}', (dx, 0, -0.05), (dx * 0.96, -lean * h, h + 0.25), 0.03, 0.022, wood, seed=seed + i))
    parts.append(pole(f'{name}_top', (-w / 2 - 0.12, -lean * h * 0.93, h * 0.93), (w / 2 + 0.12, -lean * h * 0.93, h * 0.93), 0.026, 0.022, wood, seed=seed + 3))
    parts.append(pole(f'{name}_bot', (-w / 2 - 0.12, -lean * 0.12, 0.12 * h), (w / 2 + 0.12, -lean * 0.12, 0.12 * h), 0.026, 0.022, wood, seed=seed + 4))
    # the hide itself: a slightly cupped panel inside the frame
    nx, ny = 14, 16
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx - 0.5, j / ny
            inset = 0.86 + 0.06 * math.sin(v * math.pi * 3 + seed)
            X = u * w * inset
            Z = 0.18 * h + v * h * 0.7
            Y = -lean * Z + 0.03 * math.sin(math.pi * (u + 0.5)) * math.sin(math.pi * v) + noise.noise(Vector((u * 4, v * 4, seed))) * 0.01
            verts.append((X, Y, Z))
    for j in range(ny):
        for i in range(nx):
            a0 = j * (nx + 1) + i
            faces.append((a0, a0 + 1, a0 + nx + 2, a0 + nx + 1))
    panel = mesh_obj(f'{name}_hide', verts, faces, hide_mat)
    parts.append(panel)
    o = join(parts, name)
    o.location = (x, y, z0)
    o.rotation_euler = (0, 0, rot_z)
    return o


# ---------------------------------------------------------------- batched geometry
class Batch:
    """Accumulates many primitive pieces into one mesh (fast for hundreds of logs/branches)."""

    def __init__(self):
        self.v, self.f, self.mi = [], [], []

    def add(self, verts, faces, mat_index=0):
        o = len(self.v)
        self.v.extend(verts)
        self.f.extend([tuple(i + o for i in fc) for fc in faces])
        self.mi.extend([mat_index] * len(faces))

    def tube(self, pts, radii, segs=8, cap=True, mat_index=0):
        pts = [Vector(p) for p in pts]
        if not hasattr(radii, '__len__'):
            radii = [radii] * len(pts)
        verts, faces = [], []
        prev_n = None
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
            d.normalize()
            if prev_n is None:
                a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
                n = d.cross(a).normalized()
            else:
                n = (prev_n - d * prev_n.dot(d))
                n = n.normalized() if n.length > 1e-6 else d.orthogonal().normalized()
            prev_n = n
            b = d.cross(n)
            for k in range(segs):
                ang = 2 * math.pi * k / segs
                verts.append(tuple(p + (n * math.cos(ang) + b * math.sin(ang)) * radii[i]))
        for i in range(len(pts) - 1):
            for k in range(segs):
                a0 = i * segs + k
                a1 = i * segs + (k + 1) % segs
                faces.append((a0, a1, a1 + segs, a0 + segs))
        if cap:
            verts.append(tuple(pts[0])); verts.append(tuple(pts[-1]))
            c0, c1 = len(verts) - 2, len(verts) - 1
            last = (len(pts) - 1) * segs
            for k in range(segs):
                faces.append((c0, (k + 1) % segs, k))
                faces.append((c1, last + k, last + (k + 1) % segs))
        self.add(verts, faces, mat_index)

    def box(self, centre, size, rot_z=0.0, mat_index=0):
        cx, cy, cz = centre
        sx, sy, sz = (s / 2 for s in size)
        c, s = math.cos(rot_z), math.sin(rot_z)
        pts = []
        for z in (-sz, sz):
            for (x, y) in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
                pts.append((cx + x * c - y * s, cy + x * s + y * c, cz + z))
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(pts, faces, mat_index)

    def ico(self, centre, radius, scale=(1, 1, 1), subdiv=2, mat_index=0, jitter=0.0, seed=0):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
        verts = []
        for v in bm.verts:
            co = v.co.copy()
            if jitter:
                co *= 1 + jitter * noise.noise(co * (2.5 / radius) + Vector((seed, seed * 0.3, 0)))
            verts.append((centre[0] + co.x * scale[0], centre[1] + co.y * scale[1], centre[2] + co.z * scale[2]))
        faces = [tuple(v.index for v in f.verts) for f in bm.faces]
        bm.free()
        self.add(verts, faces, mat_index)

    def build(self, name, mats, smooth=True, coll=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        for m in mats:
            me.materials.append(m)
        if len(mats) > 1:
            me.polygons.foreach_set('material_index', self.mi)
        if smooth:
            me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        o = bpy.data.objects.new(name, me)
        (coll or bpy.context.scene.collection).objects.link(o)
        return o


def tree(batch, loc, height=9.0, seed=0, kind='oak', depth=4, leaves=False, z0=0.0, crown=1.0, leaf_size=1.0):
    """Recursive branching tree into a Batch (mat 0 = bark, mat 1 = leaf clumps)."""
    rnd = random.Random(seed)
    x, y = loc
    base = Vector((x, y, z0 - 0.2))
    trunk_len = height * (0.38 if kind == 'oak' else 0.5)
    r0 = height * (0.028 if kind == 'oak' else 0.018)
    tips = []

    def grow(p0, d, L, r, level):
        n = 5 if level < 2 else 3
        pts, rad = [p0], [r]
        p = p0.copy()
        dd = d.copy()
        crook = 0.35 if kind == 'oak' else 0.15
        for i in range(1, n + 1):
            dd = (dd + Vector((rnd.uniform(-crook, crook), rnd.uniform(-crook, crook), rnd.uniform(-crook, crook) * 0.5 + (0.05 if kind != 'oak' else -0.02)))).normalized()
            p = p + dd * (L / n)
            pts.append(p.copy())
            rad.append(r * (1 - 0.45 * i / n))
        batch.tube(pts, rad, segs=7 if level < 2 else 4, cap=False)
        if level >= depth:
            tips.append((p, L))
            return
        kids = rnd.randint(2, 3) if level > 0 else rnd.randint(3, 5)
        for k in range(kids):
            ang = rnd.uniform(0, 2 * math.pi)
            spread = math.radians(rnd.uniform(25, 55) if kind == 'oak' else rnd.uniform(15, 35))
            axis = dd.orthogonal().normalized()
            q = Matrix.Rotation(spread, 3, axis)
            nd = (q @ dd)
            nd = (Matrix.Rotation(ang, 3, dd) @ nd).normalized()
            if kind == 'oak' and level == 0:
                nd.z *= 0.55
                nd.normalize()
            grow(p, nd, L * rnd.uniform(0.58, 0.75) * (crown if level == 0 else 1.0), r * rnd.uniform(0.5, 0.65), level + 1)

    grow(base, Vector((rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), 1)).normalized(), trunk_len, r0, 0)
    if leaves:
        for (p, L) in tips:
            if rnd.random() < 0.9:
                R = rnd.uniform(0.7, 1.2) * height * 0.075 * leaf_size
                for k in range(7):
                    q = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.6))) * R * 0.6
                    rr = R * rnd.uniform(0.25, 0.45)
                    batch.ico(tuple(p + q), rr, (1.0, 1.0, 0.8), subdiv=1, mat_index=1, jitter=0.45, seed=rnd.random() * 50)
    return tips


def mat_leaves(name='Leaves', base='#3d4a22', dark='#222b14', transl='#6f7d2a', emit=None, emit_strength=0.0):
    m = mat_translucent_mix(name, base, transl, mix=0.25, rough=0.7, var_dark=dark, var=0.8, scale=3.0, bump=0.6)
    if emit:
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Emission Color'].default_value = (*srgb(emit), 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    return m


def log_wall(batch, a, b, z0, height, r=0.14, mat_index=0, seed=0, overhang=0.25):
    """Horizontal stacked logs from a to b (2D points), saddle-notched look via overhang."""
    rnd = random.Random(seed)
    a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
    d = (b - a).normalized()
    n = int(height / (2 * r * 0.92))
    for i in range(n):
        z = z0 + r + i * 2 * r * 0.92
        rr = r * rnd.uniform(0.88, 1.08)
        p0 = a - d * overhang * rnd.uniform(0.6, 1.2) + Vector((0, 0, z))
        p1 = b + d * overhang * rnd.uniform(0.6, 1.2) + Vector((0, 0, z))
        mid = (p0 + p1) / 2 + Vector((0, 0, rnd.uniform(-0.02, 0.02)))
        batch.tube([p0, mid, p1], [rr, rr * 1.03, rr * 0.95], segs=8)


def log_building(batch, centre, size, wall_h, roof_h, rot=0.0, seed=0, wall_mi=0, roof_mi=1, snow_mi=None, r=0.14,
                 chimney_mi=None):
    """Log house with a gable roof (roof slab + optional snow slab)."""
    cx, cy = centre
    sx, sy = size
    c, s = math.cos(rot), math.sin(rot)

    def W(x, y):
        return (cx + x * c - y * s, cy + x * s + y * c)

    corners = [W(-sx / 2, -sy / 2), W(sx / 2, -sy / 2), W(sx / 2, sy / 2), W(-sx / 2, sy / 2)]
    for i in range(4):
        log_wall(batch, corners[i], corners[(i + 1) % 4], 0.0 + (r if i % 2 else 0), wall_h, r, wall_mi, seed + i)
    # gable ends (triangles of logs approximated by a plank triangle)
    for side in (-1, 1):
        x = side * sx / 2
        pts = [(*W(x, -sy / 2), wall_h), (*W(x, sy / 2), wall_h), (*W(x, 0), wall_h + roof_h)]
        batch.add(pts, [(0, 1, 2)], wall_mi)
    # roof planes (thick slabs) overhanging
    ov = 0.45
    for side in (-1, 1):
        y0 = 0
        y1 = side * (sy / 2 + ov)
        z1 = wall_h - ov * roof_h / (sy / 2)
        th = 0.12
        quad = [(-sx / 2 - ov, y0, wall_h + roof_h), (sx / 2 + ov, y0, wall_h + roof_h), (sx / 2 + ov, y1, z1), (-sx / 2 - ov, y1, z1)]
        top = [(*W(px, py), pz + th) for px, py, pz in quad]
        bot = [(*W(px, py), pz) for px, py, pz in quad]
        batch.add(bot + top, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], roof_mi)
        if snow_mi is not None:
            sn = [(*W(px, py), pz + th + 0.02) for px, py, pz in quad]
            sn2 = [(*W(px, py), pz + th + 0.2) for px, py, pz in quad]
            batch.add(sn + sn2, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], snow_mi)
    if chimney_mi is not None:
        px, py = W(sx / 2 - 0.9, 0.0)
        batch.box((px, py, (wall_h + roof_h) / 2 + 0.6), (0.8, 0.8, wall_h + roof_h + 1.2), rot, chimney_mi)
        return (px, py, wall_h + roof_h + 1.2)
    return None


def palisade(batch, pts, height=4.0, r=0.14, seed=0, gaps=(), mat_index=0):
    """Vertical pointed pickets along a closed polyline; gaps = list of (segment index, t0, t1)."""
    rnd = random.Random(seed)
    n = len(pts)
    for i in range(n):
        a, b = Vector((*pts[i], 0)), Vector((*pts[(i + 1) % n], 0))
        L = (b - a).length
        k = int(L / (2 * r * 0.98))
        for j in range(k):
            t = (j + 0.5) / k
            if any(gi == i and g0 <= t <= g1 for gi, g0, g1 in gaps):
                continue
            p = a.lerp(b, t)
            h = height * rnd.uniform(0.94, 1.06)
            rr = r * rnd.uniform(0.85, 1.1)
            lean = Vector((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), 0))
            batch.tube([p + Vector((0, 0, -0.3)), p + Vector((0, 0, h * 0.5)) + lean * 0.5, p + Vector((0, 0, h)) + lean,
                        p + Vector((0, 0, h + rr * 2.2)) + lean], [rr, rr * 0.98, rr * 0.95, 0.01], segs=7)


# ---------------------------------------------------------------- animals and carts
def _mb_mesh(name, elements, resolution=0.06):
    """Build a mesh from metaball elements: list of (type, co, radius, size(xyz), rot_quat or None)."""
    from mathutils import Quaternion
    mb = bpy.data.metaballs.new(name + '_mb')
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = 0.6
    for typ, co, r, size, rot in elements:
        e = mb.elements.new()
        e.type = typ
        e.co = co
        e.radius = r
        e.stiffness = 2.0
        if typ in ('ELLIPSOID', 'CAPSULE', 'CUBE'):
            e.size_x, e.size_y, e.size_z = size
        if rot is not None:
            e.rotation = rot
    o = bpy.data.objects.new(name + '_mbo', mb)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    me.name = name
    bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.metaballs.remove(mb)
    for p in me.polygons:
        p.use_smooth = True
    return me


def _leg(x0, y0, z_top, length, r, ang_fwd=0.0):
    """Capsule element hanging down from (x0, y0, z_top)."""
    from mathutils import Quaternion
    # capsule axis is local X: rotate X to point down (-Z), tilted by ang_fwd about Y
    q = Quaternion((0, 1, 0), math.pi / 2 + ang_fwd)
    cz = z_top - length / 2 * math.cos(ang_fwd)
    cx = x0 + length / 2 * math.sin(ang_fwd)
    return ('CAPSULE', (cx, y0, cz), r, (length / 2, 1, 1), q)


def bison_mesh(name='Bison', pose='graze', seed=0, ox=False):
    """Stylised plains bison (or, with ox=True, a draught ox) built from metaballs. X forward, ~3 m long."""
    rnd = random.Random(seed)
    s = rnd.uniform(0.9, 1.08)
    E = []
    if not ox:
        E += [('ELLIPSOID', (0.35, 0, 1.30), 0.62, (1.0, 0.62, 0.95), None),     # hump / shoulders
              ('ELLIPSOID', (0.80, 0, 1.00), 0.55, (0.8, 0.70, 0.95), None),     # chest
              ('ELLIPSOID', (-0.25, 0, 1.00), 0.50, (1.35, 0.78, 0.72), None),   # barrel
              ('ELLIPSOID', (-0.95, 0, 1.02), 0.40, (0.9, 0.85, 0.9), None)]     # rump
        hz = 0.62 if pose == 'graze' else 1.0
        hx = 1.45 if pose == 'graze' else 1.42
        E += [('ELLIPSOID', (hx, 0, hz), 0.34, (1.15, 0.85, 1.05), None),     # head
              ('ELLIPSOID', (hx - 0.3, 0, hz - 0.12), 0.26, (0.8, 0.8, 1.1), None),   # beard / dewlap
              ('ELLIPSOID', (1.12, 0, (hz + 1.25) / 2), 0.38, (0.9, 0.75, 1.0), None)]   # neck / mane
        legs = [(0.62, 0.2, 0.95, 0.95, 0.11), (0.62, -0.2, 0.95, 0.95, 0.11), (-1.0, 0.2, 0.95, 0.95, 0.10), (-1.0, -0.2, 0.95, 0.95, 0.10)]
    else:
        E += [('ELLIPSOID', (0.55, 0, 1.15), 0.45, (0.9, 0.62, 0.85), None),
              ('ELLIPSOID', (-0.2, 0, 1.12), 0.48, (1.45, 0.72, 0.72), None),
              ('ELLIPSOID', (-0.95, 0, 1.12), 0.40, (0.8, 0.8, 0.85), None),
              ('ELLIPSOID', (1.25, 0, 1.15), 0.26, (1.3, 0.75, 0.9), None),
              ('ELLIPSOID', (0.95, 0, 1.05), 0.3, (1.0, 0.7, 1.1), None)]
        legs = [(0.55, 0.2, 1.0, 1.05, 0.09), (0.55, -0.2, 1.0, 1.05, 0.09), (-1.0, 0.2, 1.0, 1.05, 0.09), (-1.0, -0.2, 1.0, 1.05, 0.09)]
    walk = rnd.uniform(-0.25, 0.25) if pose != 'graze' else rnd.uniform(-0.1, 0.1)
    for i, (x, y, zt, L, r) in enumerate(legs):
        a = walk * (1 if i in (0, 3) else -1)
        E.append(_leg(x, y, zt, L, r, a))
        E.append(('ELLIPSOID', (x + math.sin(a) * L * 0.95, y, 0.08), 0.12, (1.0, 0.8, 0.8), None))   # hoof
    E.append(_leg(-1.25, 0, 1.15, 0.6, 0.04, 0.25))    # tail
    me = _mb_mesh(name, E, resolution=0.07)
    me.transform(Matrix.Diagonal((s, s, s, 1.0)))
    return me


def mat_bison(name='BisonCoat', ox=False):
    """Dark coat with lighter, woollier forequarters (graded along object X), noise bump."""
    m, nt, b, out = lib.mat_new(name)
    b.inputs['Roughness'].default_value = 0.95
    tc = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
    sep = node(nt, 'ShaderNodeSeparateXYZ', (-1000, 0))
    link(nt, tc.outputs['Object'], sep.inputs['Vector'])
    mp = node(nt, 'ShaderNodeMapRange', (-800, 0))
    mp.inputs['From Min'].default_value = -0.4
    mp.inputs['From Max'].default_value = 0.9
    link(nt, sep.outputs['X'], mp.inputs['Value'])
    if ox:
        cr = lib.color_ramp(nt, [(0.0, srgb('#5a3a24')), (1.0, srgb('#6e4a2e'))], (-600, 0))
    else:
        cr = lib.color_ramp(nt, [(0.0, srgb('#2c1e15')), (0.55, srgb('#3d2a1c')), (1.0, srgb('#6a4a2d'))], (-600, 0))
    link(nt, mp.outputs['Result'], cr.inputs['Fac'])
    nz = node(nt, 'ShaderNodeTexNoise', (-800, -300))
    nz.inputs['Scale'].default_value = 40
    nz.inputs['Detail'].default_value = 10
    link(nt, tc.outputs['Object'], nz.inputs['Vector'])
    mul = node(nt, 'ShaderNodeMix', (-350, 0), data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 0.5
    link(nt, cr.outputs['Color'], mul.inputs[6])
    link(nt, nz.outputs['Color'], mul.inputs[7])
    link(nt, mul.outputs[2], b.inputs['Base Color'])
    bp = node(nt, 'ShaderNodeBump', (-300, -350))
    bp.inputs['Strength'].default_value = 0.6
    link(nt, nz.outputs['Fac'], bp.inputs['Height'])
    link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    return m


def horns(batch, s=1.0, x=1.45, z=0.62):
    for side in (-1, 1):
        p0 = Vector((x - 0.05, side * 0.2, z + 0.18)) * 1.0
        batch.tube([p0, p0 + Vector((0.0, side * 0.12, 0.05)), p0 + Vector((0.03, side * 0.14, 0.17))], [0.04, 0.03, 0.006], segs=6)


def cart(batch, loc, rot_z, seed=0, wheel_mi=0, body_mi=0, load_mi=1, load=True):
    """Red River cart: two large dished wooden wheels, a light box frame and long shafts (all wood)."""
    rnd = random.Random(seed)
    cx, cy, cz = loc
    c, s = math.cos(rot_z), math.sin(rot_z)

    def W(x, y, z):
        return (cx + x * c - y * s, cy + x * s + y * c, cz + z)

    R = 0.85
    for side in (-1, 1):
        yy = side * 0.85
        pts = [W(R * math.cos(a), yy, R + R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 33)]
        batch.tube(pts, 0.045, segs=6, cap=False, mat_index=wheel_mi)
        for k in range(12):
            a = 2 * math.pi * k / 12 + rnd.uniform(-0.05, 0.05)
            batch.tube([W(0, yy - side * 0.1, R), W(R * 0.95 * math.cos(a), yy, R + R * 0.95 * math.sin(a))], 0.018, segs=4, mat_index=wheel_mi)
        batch.tube([W(0, yy - side * 0.18, R), W(0, yy + side * 0.08, R)], 0.09, segs=8, mat_index=wheel_mi)
    batch.tube([W(0, -0.95, R), W(0, 0.95, R)], 0.05, segs=6, mat_index=body_mi)   # axle
    for side in (-1, 1):   # shafts, running forward to the animal
        batch.tube([W(-1.0, side * 0.55, R + 0.15), W(1.0, side * 0.55, R + 0.12), W(2.9, side * 0.38, R - 0.05)], 0.04, segs=5, mat_index=body_mi)
    batch.box(W(-0.1, 0, R + 0.2), (2.0, 1.15, 0.05), rot_z, body_mi)
    for side in (-1, 1):
        for k in range(6):
            x = -1.0 + k * 0.38
            batch.tube([W(x, side * 0.56, R + 0.2), W(x, side * 0.56, R + 0.75)], 0.02, segs=4, mat_index=body_mi)
        batch.tube([W(-1.05, side * 0.56, R + 0.75), W(0.9, side * 0.56, R + 0.75)], 0.025, segs=4, mat_index=body_mi)
    if load:
        for k in range(rnd.randint(2, 4)):
            batch.box(W(rnd.uniform(-0.7, 0.4), rnd.uniform(-0.25, 0.25), R + 0.42 + k * 0.18),
                      (rnd.uniform(0.5, 0.7), rnd.uniform(0.35, 0.5), 0.2), rot_z + rnd.uniform(-0.3, 0.3), load_mi)


def _loft(batch, sections, segs=16, mat_index=0, cap=True, power=2.2):
    """sections: list of (centre Vector, axis-aligned frame (u, v) vectors, ru, rv). Rings are superellipses."""
    verts, faces = [], []
    for (c, u, v, ru, rv) in sections:
        for k in range(segs):
            a = 2 * math.pi * k / segs
            ca, sa = math.cos(a), math.sin(a)
            cu = math.copysign(abs(ca) ** (2 / power), ca)
            sv = math.copysign(abs(sa) ** (2 / power), sa)
            verts.append(tuple(c + u * (cu * ru) + v * (sv * rv)))
    n = len(sections)
    for i in range(n - 1):
        for k in range(segs):
            a0 = i * segs + k
            a1 = i * segs + (k + 1) % segs
            faces.append((a0, a1, a1 + segs, a0 + segs))
    if cap:
        for ring, rev in ((0, True), (n - 1, False)):
            c = sections[ring][0]
            verts.append(tuple(c))
            ci = len(verts) - 1
            for k in range(segs):
                a0 = ring * segs + k
                a1 = ring * segs + (k + 1) % segs
                faces.append((ci, a1, a0) if rev else (ci, a0, a1))
    batch.add(verts, faces, mat_index)


def bison2(batch, loc=(0, 0, 0), rot_z=0.0, pose='graze', seed=0, scale=1.0, mat_index=0, horn_mi=None, ox=False):
    """Lofted plains bison (or draught ox): body, head, legs, tail, into a Batch. X forward."""
    rnd = random.Random(seed)
    s = scale * rnd.uniform(0.9, 1.08)
    R = Matrix.Rotation(rot_z, 3, 'Z')
    L0 = Vector(loc)
    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

    def P_(x, y, z):
        return L0 + R @ (Vector((x, y, z)) * s)

    if not ox:
        prof = [(-1.36, 1.14, 0.94, 0.10), (-1.25, 1.30, 0.74, 0.30), (-0.95, 1.38, 0.60, 0.40), (-0.5, 1.42, 0.56, 0.46),
                (-0.1, 1.56, 0.52, 0.49), (0.25, 1.80, 0.50, 0.52), (0.55, 1.86, 0.46, 0.52), (0.85, 1.68, 0.44, 0.48),
                (1.06, 1.44, 0.50, 0.42), (1.18, 1.2, 0.62, 0.32)]
    else:
        prof = [(-1.3, 1.3, 1.1, 0.10), (-1.2, 1.42, 0.92, 0.26), (-0.9, 1.46, 0.82, 0.32), (-0.4, 1.44, 0.8, 0.35),
                (0.1, 1.46, 0.82, 0.35), (0.5, 1.5, 0.84, 0.32), (0.8, 1.44, 0.9, 0.26), (1.0, 1.36, 0.98, 0.2)]
    secs = []
    for x, top, bot, hw in prof:
        jit = 1 + rnd.uniform(-0.03, 0.03)
        c = P_(x, 0, (top + bot) / 2)
        secs.append((c, R @ Y, R @ Z, hw * s * jit, (top - bot) / 2 * s))
    _loft(batch, secs, segs=18, mat_index=mat_index, power=2.6)
    # head
    if not ox:
        if pose == 'graze':
            hp = [(1.0, 1.15, 0.36), (1.2, 0.9, 0.36), (1.38, 0.62, 0.30), (1.5, 0.42, 0.22), (1.55, 0.3, 0.14)]
        else:
            hp = [(0.98, 1.35, 0.36), (1.22, 1.22, 0.36), (1.45, 1.06, 0.29), (1.62, 0.9, 0.21), (1.68, 0.8, 0.13)]
    else:
        hp = [(0.95, 1.3, 0.24), (1.15, 1.22, 0.2), (1.35, 1.08, 0.17), (1.5, 0.95, 0.12)]
    hs = []
    for i, (x, z, r) in enumerate(hp):
        nx = hp[min(i + 1, len(hp) - 1)][0] - hp[max(i - 1, 0)][0]
        nz = hp[min(i + 1, len(hp) - 1)][1] - hp[max(i - 1, 0)][1]
        d = Vector((nx, 0, nz)).normalized()
        v = Vector((-d.z, 0, d.x))
        hs.append((P_(x, 0, z), R @ Y, R @ v, r * s * 0.85, r * s))
    _loft(batch, hs, segs=14, mat_index=mat_index, power=2.2)
    if not ox:   # beard / dewlap
        bx, bz = (hp[2][0] - 0.12, hp[2][1] - 0.22) if pose == 'graze' else (hp[2][0] - 0.15, hp[2][1] - 0.3)
        batch.ico(tuple(P_(bx, 0, bz)), 0.18 * s, (0.9, 0.7, 1.4), subdiv=2, mat_index=mat_index, jitter=0.25, seed=seed)
    # legs
    walk = rnd.uniform(-0.18, 0.18) if pose != 'graze' else rnd.uniform(-0.06, 0.06)
    fr = 0.16 if not ox else 0.1
    for side in (-1, 1):
        a = walk * side
        batch.tube([P_(0.62, side * 0.24, 0.85), P_(0.64 + a * 0.3, side * 0.22, 0.42), P_(0.62 + a, side * 0.21, 0.12), P_(0.63 + a, side * 0.21, 0.0)],
                   [fr * s, fr * 0.7 * s, fr * 0.5 * s, fr * 0.62 * s], segs=8, mat_index=mat_index)
        batch.tube([P_(-0.92, side * 0.25, 0.95), P_(-1.0 - a * 0.3, side * 0.22, 0.5), P_(-0.93 - a, side * 0.2, 0.12), P_(-0.92 - a, side * 0.2, 0.0)],
                   [fr * 0.95 * s, fr * 0.6 * s, fr * 0.48 * s, fr * 0.6 * s], segs=8, mat_index=mat_index)
    batch.tube([P_(-1.34, 0, 1.12), P_(-1.42, 0, 0.85), P_(-1.42, 0, 0.6)], [0.05 * s, 0.03 * s, 0.05 * s], segs=6, mat_index=mat_index)
    if horn_mi is not None and not ox:
        hx, hz = hp[1][0] + 0.05, hp[1][1] + 0.25
        for side in (-1, 1):
            batch.tube([P_(hx, side * 0.24, hz), P_(hx, side * 0.36, hz + 0.05), P_(hx + 0.04, side * 0.38, hz + 0.17)],
                       [0.045 * s, 0.03 * s, 0.006 * s], segs=6, mat_index=horn_mi)


def bison_proto(name, pose='graze', seed=0, ox=False, coat=None, horn=None, shag=0.05):
    """One reusable bison/ox mesh at the origin (object-space X forward), with a shaggy forequarter."""
    b = Batch()
    bison2(b, (0, 0, 0), 0.0, pose, seed=seed, mat_index=0, horn_mi=1 if horn else None, ox=ox)
    o = b.build(name, [m for m in (coat, horn) if m])
    me = o.data
    if shag and not ox:
        off = Vector((seed * 1.3, 0, 0))
        for v in me.vertices:
            w = max(0.0, min(1.0, (v.co.x + 0.2) / 0.8)) * (1.0 if v.co.z > 0.45 else 0.3)
            if w > 0:
                d = noise.noise(v.co * 7.0 + off)
                v.co += Vector((d * 0.4, d * 0.6, abs(d))) * shag * w
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 1
    bpy.context.scene.collection.objects.unlink(o)
    return o


def herd(protos, placements, coll_name='Herd'):
    """Linked duplicates of prototype objects: placements = list of (proto_index, (x, y, z), rot_z, scale)."""
    col = bpy.data.collections.new(coll_name)
    bpy.context.scene.collection.children.link(col)
    out = []
    for i, (pi, loc, rz, sc) in enumerate(placements):
        src = protos[pi]
        o = bpy.data.objects.new(f'{coll_name}_{i}', src.data)
        for m in src.modifiers:
            mm = o.modifiers.new(m.name, m.type)
            if m.type == 'SUBSURF':
                mm.levels, mm.render_levels = m.levels, m.render_levels
        col.objects.link(o)
        o.location = loc
        o.rotation_euler = (0, 0, rz)
        o.scale = (sc, sc, sc)
        o.pass_index = i + 1
        out.append(o)
    return out
