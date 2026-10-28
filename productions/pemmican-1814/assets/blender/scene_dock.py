"""S1 — The bag on the landing at dawn (cold open, ending, thumbnail).

Reconstruction: a sewn rawhide pemmican bag (~90 lb fur-trade "piece") on a log landing
by a northern river at dawn. Not a depiction of a specific documented place.

Run: python3 scene_dock.py <shot> <outdir> [--still N] [--res 1920x1080] [--samples 24]
"""
import sys, os, math, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import lib
from lib import node, link, srgb

DECK_Z = 0.55
FUR = True
FUR_DENSITY = 420000.0
HAZE = 0.0


# ---------------------------------------------------------------- materials
def mat_rawhide(name='Rawhide', base='#a58a62', dark='#4d3a26', grease=0.45, seed=0):
    """Stiff rawhide: cream-amber, translucent at thin edges, darker blotches, grease stains,
    fine creases, and a few patches of worn hair stubble."""
    m, nt, b, out = lib.mat_new(name)
    tc = node(nt, 'ShaderNodeTexCoord', (-1600, 0))
    mp = node(nt, 'ShaderNodeMapping', (-1400, 0)); link(nt, tc.outputs['Object'], mp.inputs['Vector'])
    mp.inputs['Location'].default_value = (seed * 3.1, seed * 1.7, seed * 0.7)
    blot = node(nt, 'ShaderNodeTexNoise', (-1100, 400), **{'Scale': 3.2, 'Detail': 9.0, 'Roughness': 0.66, 'Distortion': 0.4})
    stain = node(nt, 'ShaderNodeTexNoise', (-1100, 150), **{'Scale': 7.0, 'Detail': 4.0, 'Roughness': 0.5})
    fine = node(nt, 'ShaderNodeTexNoise', (-1100, -150), **{'Scale': 60.0, 'Detail': 6.0, 'Roughness': 0.6})
    crease = node(nt, 'ShaderNodeTexWave', (-1100, -450), wave_type='RINGS', **{'Scale': 9.0, 'Distortion': 14.0, 'Detail': 6.0, 'Detail Scale': 2.0})
    hair = node(nt, 'ShaderNodeTexNoise', (-1100, -750), **{'Scale': 420.0, 'Detail': 2.0})
    for t in (blot, stain, fine, crease, hair):
        link(nt, mp.outputs['Vector'], t.inputs['Vector'])
    ramp = lib.color_ramp(nt, [(0.25, srgb(dark)), (0.5, srgb(base)), (0.72, srgb('#d2b78a'))], (-800, 400))
    link(nt, blot.outputs['Fac'], ramp.inputs['Fac'])
    # grease stains: darker + glossier
    smask = lib.color_ramp(nt, [(0.52, (0, 0, 0)), (0.66, (1, 1, 1))], (-800, 150))
    link(nt, stain.outputs['Fac'], smask.inputs['Fac'])
    gmix = node(nt, 'ShaderNodeMix', (-500, 400), data_type='RGBA', blend_type='MULTIPLY')
    link(nt, smask.outputs['Color'], gmix.inputs['Factor'])
    link(nt, ramp.outputs['Color'], gmix.inputs[6]); gmix.inputs[7].default_value = (*srgb('#7a5a3a'), 1)
    # hair stubble patches
    hmask = lib.color_ramp(nt, [(0.60, (0, 0, 0)), (0.70, (1, 1, 1))], (-800, -700))
    link(nt, blot.outputs['Fac'], hmask.inputs['Fac'])
    hspk = lib.color_ramp(nt, [(0.45, (0, 0, 0)), (0.6, (1, 1, 1))], (-800, -900))
    link(nt, hair.outputs['Fac'], hspk.inputs['Fac'])
    hm = node(nt, 'ShaderNodeMath', (-600, -750), operation='MULTIPLY')
    link(nt, hmask.outputs['Color'], hm.inputs[0]); link(nt, hspk.outputs['Color'], hm.inputs[1])
    hmix = node(nt, 'ShaderNodeMix', (-300, 400), data_type='RGBA', blend_type='MIX')
    link(nt, hm.outputs[0], hmix.inputs['Factor'])
    link(nt, gmix.outputs[2], hmix.inputs[6]); hmix.inputs[7].default_value = (*srgb('#3a2818'), 1)
    link(nt, hmix.outputs[2], b.inputs['Base Color'])
    rough = node(nt, 'ShaderNodeMapRange', (-300, 100), **{'To Min': 0.62, 'To Max': 0.62 - grease * 0.5})
    link(nt, smask.outputs['Color'], rough.inputs['Value']); link(nt, rough.outputs['Result'], b.inputs['Roughness'])
    b.inputs['Subsurface Weight'].default_value = 0.04
    b.inputs['Subsurface Radius'].default_value = (0.5, 0.4, 0.3)
    b.inputs['Subsurface Scale'].default_value = 0.006
    b.inputs['Specular IOR Level'].default_value = 0.4
    # creases + fine grain
    cm = node(nt, 'ShaderNodeMath', (-700, -350), operation='MULTIPLY'); cm.inputs[1].default_value = 0.6
    link(nt, crease.outputs['Fac'], cm.inputs[0])
    add = node(nt, 'ShaderNodeMath', (-500, -300), operation='ADD')
    link(nt, fine.outputs['Fac'], add.inputs[0]); link(nt, cm.outputs[0], add.inputs[1])
    bump = node(nt, 'ShaderNodeBump', (-150, -300), **{'Strength': 0.22, 'Distance': 0.003})
    link(nt, add.outputs[0], bump.inputs['Height']); link(nt, bump.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_thong():
    m, nt, b, out = lib.mat_new('Thong')
    b.inputs['Base Color'].default_value = (*srgb('#3b2717'), 1)
    b.inputs['Roughness'].default_value = 0.55
    return m


def mat_wood(name='Wood', base='#76695a', dark='#3b342c', wet=0.5):
    m, nt, b, out = lib.mat_new(name)
    tc = node(nt, 'ShaderNodeTexCoord', (-1400, 0))
    mp = node(nt, 'ShaderNodeMapping', (-1200, 0)); link(nt, tc.outputs['Object'], mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (60.0, 1.5, 60.0)
    grain = node(nt, 'ShaderNodeTexNoise', (-950, 250), **{'Scale': 1.0, 'Detail': 10.0, 'Roughness': 0.7, 'Distortion': 0.2})
    link(nt, mp.outputs['Vector'], grain.inputs['Vector'])
    big = node(nt, 'ShaderNodeTexNoise', (-950, -100), **{'Scale': 2.5, 'Detail': 6.0})
    link(nt, tc.outputs['Object'], big.inputs['Vector'])
    ramp = lib.color_ramp(nt, [(0.3, srgb(dark)), (0.55, srgb(base)), (0.75, srgb('#9a8d7b'))], (-650, 250))
    link(nt, grain.outputs['Fac'], ramp.inputs['Fac'])
    wmask = lib.color_ramp(nt, [(0.48, (0, 0, 0)), (0.62, (1, 1, 1))], (-650, -100))
    link(nt, big.outputs['Fac'], wmask.inputs['Fac'])
    wetmix = node(nt, 'ShaderNodeMix', (-350, 200), data_type='RGBA', blend_type='MULTIPLY')
    link(nt, wmask.outputs['Color'], wetmix.inputs['Factor'])
    link(nt, ramp.outputs['Color'], wetmix.inputs[6]); wetmix.inputs[7].default_value = (0.5, 0.5, 0.5, 1)
    link(nt, wetmix.outputs[2], b.inputs['Base Color'])
    rough = node(nt, 'ShaderNodeMapRange', (-350, -100), **{'To Min': 0.85, 'To Max': 0.85 - wet * 0.6})
    link(nt, wmask.outputs['Color'], rough.inputs['Value']); link(nt, rough.outputs['Result'], b.inputs['Roughness'])
    bump = node(nt, 'ShaderNodeBump', (-150, -350), **{'Strength': 0.12, 'Distance': 0.004})
    link(nt, grain.outputs['Fac'], bump.inputs['Height']); link(nt, bump.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_water(frame_scale=1.0):
    m, nt, b, out = lib.mat_new('Water')
    b.inputs['Base Color'].default_value = (*srgb('#0b1418'), 1)
    b.inputs['Roughness'].default_value = 0.14
    b.inputs['IOR'].default_value = 1.33
    tc = node(nt, 'ShaderNodeTexCoord', (-1200, 0))
    nz = node(nt, 'ShaderNodeTexNoise', (-900, 0), noise_dimensions='4D', **{'Scale': 0.9, 'Detail': 7.0, 'Roughness': 0.55})
    link(nt, tc.outputs['Object'], nz.inputs['Vector'])
    # animate W for slow ripples
    nz.inputs['W'].default_value = 0.0
    nz.inputs['W'].keyframe_insert('default_value', frame=1)
    nz.inputs['W'].default_value = 1.2 * frame_scale
    nz.inputs['W'].keyframe_insert('default_value', frame=361)
    for fc in lib._fcurves(m.node_tree.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
        fc.extrapolation = 'LINEAR'
    bump = node(nt, 'ShaderNodeBump', (-400, -200), **{'Strength': 0.2, 'Distance': 0.05})
    link(nt, nz.outputs['Fac'], bump.inputs['Height']); link(nt, bump.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_simple(name, hexcol, rough=0.8, emit=None, emit_strength=0.0):
    m, nt, b, out = lib.mat_new(name)
    b.inputs['Base Color'].default_value = (*srgb(hexcol), 1)
    b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = (*srgb(emit), 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    return m


# ---------------------------------------------------------------- geometry
def make_bag(name, size=(0.56, 0.36, 0.22), loc=(0, 0, 0), rot_z=0.0, seed=1, mat=None, thong=None):
    """Stiff rawhide bag: flat-ish faces bulging from the packed contents, creased edges,
    an overlapping flap along the top laced shut with a rawhide thong, and a laced end."""
    sx, sy, sz = size
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    body = lib.obj_from_bmesh(name, bm, mat)
    bev = body.modifiers.new('Bevel', 'BEVEL'); bev.width = min(sx, sy, sz) * 0.22; bev.segments = 4
    sub = lib.add_subsurf(body, 2, 3)
    tex = bpy.data.textures.new(name + '_lumps', 'CLOUDS'); tex.noise_scale = 0.09 + rnd.uniform(0, 0.03); tex.noise_depth = 3
    disp = body.modifiers.new('Lumps', 'DISPLACE'); disp.texture = tex; disp.strength = 0.006; disp.texture_coords = 'OBJECT'
    tex2 = bpy.data.textures.new(name + '_wrink', 'VORONOI'); tex2.noise_scale = 0.03
    d2 = body.modifiers.new('Wrinkles', 'DISPLACE'); d2.texture = tex2; d2.strength = 0.0035; d2.texture_coords = 'OBJECT'
    cast = body.modifiers.new('Bulge', 'CAST'); cast.cast_type = 'SPHERE'; cast.factor = 0.10
    lib.shade_smooth(body)
    # overlapping flap along the top, near the front long edge
    fw = 0.075
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx * 0.96, fw, 0.006), verts=bm.verts)
    flap = lib.obj_from_bmesh(name + '_flap', bm, mat)
    fb = flap.modifiers.new('Bevel', 'BEVEL'); fb.width = 0.003; fb.segments = 2
    lib.add_subsurf(flap, 2, 2)
    fd = flap.modifiers.new('Wave', 'DISPLACE'); fd.texture = tex; fd.strength = 0.006; fd.texture_coords = 'OBJECT'
    lib.shade_smooth(flap)
    fy = -sy / 2 + fw / 2 + 0.02
    flap.location = (0, fy, sz / 2 + 0.006)
    flap.rotation_euler = (math.radians(-3), 0, 0)
    flap.parent = body
    # lacing: thong crossing the flap's free edge at irregular intervals
    x = -sx * 0.44
    i = 0
    while x < sx * 0.44:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.009, 0.05, 0.004), verts=bm.verts)
        st = lib.obj_from_bmesh(f'{name}_lace{i}', bm, thong)
        st.modifiers.new('Bevel', 'BEVEL').width = 0.0015
        st.location = (x, fy + fw / 2 - 0.004, sz / 2 + 0.011)
        st.rotation_euler = (math.radians(-6), rnd.uniform(-0.15, 0.15), math.radians(35) + rnd.uniform(-0.2, 0.2))
        st.parent = body
        x += rnd.uniform(0.045, 0.065)
        i += 1
    # laced end seam (right end), vertical
    zz = -sz * 0.35
    j = 0
    while zz < sz * 0.38:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.004, 0.009, 0.042), verts=bm.verts)
        st = lib.obj_from_bmesh(f'{name}_end{j}', bm, thong)
        st.location = (sx / 2 + 0.004, rnd.uniform(-0.01, 0.01), zz)
        st.rotation_euler = (math.radians(55) + rnd.uniform(-0.2, 0.2), 0, 0)
        st.parent = body
        zz += rnd.uniform(0.035, 0.05)
        j += 1
    body.location = Vector(loc) + Vector((0, 0, sz / 2))
    body.rotation_euler = (0, 0, rot_z)
    return body


def make_spruce_proto(seed=0):
    rnd = random.Random(seed)
    bm = bmesh.new()
    tiers = 16
    for i in range(tiers):
        f = i / tiers
        z0 = 0.08 + f * 0.86
        r = (0.26 * (1 - f) ** 0.9 + 0.015) * rnd.uniform(0.8, 1.2)
        geom = bmesh.ops.create_cone(bm, cap_ends=False, segments=11, radius1=r, radius2=r * 0.15,
                                     depth=0.11 + 0.04 * (1 - f))
        for v in geom['verts']:
            ang = math.atan2(v.co.y, v.co.x)
            jag = 1.0 + 0.35 * math.sin(ang * rnd.randint(3, 6) + rnd.uniform(0, 6))
            v.co.x *= jag; v.co.y *= jag
            if v.co.z < 0:  # droop the outer rim
                v.co.z -= 0.02 * (math.hypot(v.co.x, v.co.y) / max(r, 1e-3))
        bmesh.ops.translate(bm, vec=(rnd.uniform(-0.01, 0.01), rnd.uniform(-0.01, 0.01), z0), verts=geom['verts'])
    geom = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.02, radius2=0.004, depth=1.0)
    bmesh.ops.translate(bm, vec=(0, 0, 0.5), verts=geom['verts'])
    return bm


def scatter_trees(protos, mat, count, xr, yr, hr, seed, ground_z=0.0, name='Trees'):
    rnd = random.Random(seed)
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    meshes = []
    for i, bm in enumerate(protos):
        me = bpy.data.meshes.new(f'{name}_proto{i}')
        bm.to_mesh(me)
        me.materials.append(mat)
        meshes.append(me)
    for i in range(count):
        o = bpy.data.objects.new(f'{name}_{i}', meshes[i % len(meshes)])
        col.objects.link(o)
        h = rnd.uniform(*hr)
        o.scale = (h * rnd.uniform(0.85, 1.15), h * rnd.uniform(0.85, 1.15), h)
        o.location = (rnd.uniform(*xr), rnd.uniform(*yr), ground_z)
        o.rotation_euler = (rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), rnd.uniform(0, 6.28))
    return col


def make_dock(mat_wood_, mat_post):
    rnd = random.Random(7)
    planks = []
    x = -1.35
    while x < 1.35:
        w = rnd.uniform(0.15, 0.21)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        L = 7.6 + rnd.uniform(-0.25, 0.25)
        bmesh.ops.scale(bm, vec=(w - 0.012, L, 0.065), verts=bm.verts)
        o = lib.obj_from_bmesh('plank', bm, mat_wood_)
        b = o.modifiers.new('Bevel', 'BEVEL'); b.width = 0.012; b.segments = 2
        o.location = (x + w / 2, -0.4 + rnd.uniform(-0.2, 0.2), DECK_Z - 0.0325 + rnd.uniform(-0.008, 0.008))
        o.rotation_euler = (rnd.uniform(-0.004, 0.004), rnd.uniform(-0.02, 0.02), rnd.uniform(-0.006, 0.006))
        planks.append(o)
        x += w
    # stringers + posts
    for px in (-1.25, 1.25):
        for py in (-3.8, -1.3, 1.2, 3.3):
            bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=0.11, depth=2.6, location=(px, py, DECK_Z - 1.2))
            p = bpy.context.active_object; p.data.materials.append(mat_post)
            p.rotation_euler = (rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), 0)
    for px in (-1.15, 1.15):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.09, depth=7.8, location=(px, -0.4, DECK_Z - 0.13))
        s = bpy.context.active_object; s.rotation_euler = (math.pi / 2, 0, 0); s.data.materials.append(mat_post)
    return planks


def mat_birchbark():
    """Birchbark hull: cream-grey outer bark with dark horizontal lenticels and pitch-sealed seams;
    reddish-brown inner bark visible on the inside (backfacing)."""
    m, nt, b, out = lib.mat_new('Birchbark')
    tc = node(nt, 'ShaderNodeTexCoord', (-1500, 0))
    mp = node(nt, 'ShaderNodeMapping', (-1300, 0)); link(nt, tc.outputs['Object'], mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (3.0, 3.0, 45.0)
    lent = node(nt, 'ShaderNodeTexNoise', (-1050, 300), **{'Scale': 6.0, 'Detail': 3.0, 'Roughness': 0.4})
    link(nt, mp.outputs['Vector'], lent.inputs['Vector'])
    lr = lib.color_ramp(nt, [(0.62, (1, 1, 1)), (0.7, (0.25, 0.22, 0.2))], (-800, 300))
    link(nt, lent.outputs['Fac'], lr.inputs['Fac'])
    var = node(nt, 'ShaderNodeTexNoise', (-1050, 0), **{'Scale': 2.0, 'Detail': 6.0})
    link(nt, tc.outputs['Object'], var.inputs['Vector'])
    base = lib.color_ramp(nt, [(0.3, srgb('#a99f8a')), (0.7, srgb('#d6ccb4'))], (-800, 0))
    link(nt, var.outputs['Fac'], base.inputs['Fac'])
    mul = node(nt, 'ShaderNodeMix', (-550, 150), data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    link(nt, base.outputs['Color'], mul.inputs[6]); link(nt, lr.outputs['Color'], mul.inputs[7])
    # pitch seams every ~0.9 m along the hull
    sx = node(nt, 'ShaderNodeSeparateXYZ', (-1300, -300)); link(nt, tc.outputs['Object'], sx.inputs['Vector'])
    wv = node(nt, 'ShaderNodeTexWave', (-1050, -300), wave_type='BANDS', bands_direction='X',
              **{'Scale': 0.55, 'Distortion': 2.0, 'Detail': 2.0})
    link(nt, tc.outputs['Object'], wv.inputs['Vector'])
    sr = lib.color_ramp(nt, [(0.0, (1, 1, 1)), (0.04, (1, 1, 1)), (0.06, (0, 0, 0)), (1.0, (0, 0, 0))], (-800, -300))
    link(nt, wv.outputs['Fac'], sr.inputs['Fac'])
    seam = node(nt, 'ShaderNodeMix', (-300, 100), data_type='RGBA', blend_type='MIX')
    link(nt, sr.outputs['Color'], seam.inputs['Factor'])
    link(nt, mul.outputs[2], seam.inputs[6]); seam.inputs[7].default_value = (*srgb('#1b1612'), 1)
    geo = node(nt, 'ShaderNodeNewGeometry', (-300, -200))
    inside = node(nt, 'ShaderNodeMix', (-100, 100), data_type='RGBA', blend_type='MIX')
    link(nt, geo.outputs['Backfacing'], inside.inputs['Factor'])
    link(nt, seam.outputs[2], inside.inputs[6]); inside.inputs[7].default_value = (*srgb('#6a3f24'), 1)
    link(nt, inside.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.7
    bump = node(nt, 'ShaderNodeBump', (-100, -300), **{'Strength': 0.25, 'Distance': 0.003})
    link(nt, lent.outputs['Fac'], bump.inputs['Height']); link(nt, bump.outputs['Normal'], b.inputs['Normal'])
    return m


def make_canoe(name='Canoe', L=7.4, B=1.32, G=0.62, rise=0.55, keel=0.22, loc=(2.2, 1.5, -0.2), hull_mat=None, wood=None):
    """Lofted canot du nord style hull with high, upturned ends."""
    NS, NP = 64, 22
    bm = bmesh.new()
    rows = []
    for i in range(NS + 1):
        u = -1 + 2 * i / NS
        x = u * L / 2
        b = B / 2 * max(1e-3, (1 - u * u)) ** 0.55
        g = G + rise * u ** 8
        k = keel * u ** 6
        row = []
        for j in range(NP + 1):
            th = -math.pi / 2 + math.pi * j / NP
            y = b * math.sin(th)
            z = g - (g - k) * abs(math.cos(th)) ** 0.75
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for i in range(NS):
        for j in range(NP):
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    hull = lib.obj_from_bmesh(name, bm, hull_mat)
    sol = hull.modifiers.new('Thick', 'SOLIDIFY'); sol.thickness = 0.012
    lib.add_subsurf(hull, 1, 2)
    lib.shade_smooth(hull)
    hull.location = loc
    parts = [hull]
    # gunwales
    for side in (-1, 1):
        pts = []
        for i in range(2, NS - 1):
            u = -1 + 2 * i / NS
            x = u * L / 2
            b = B / 2 * max(1e-3, (1 - u * u)) ** 0.55
            pts.append((x, side * b, G + rise * u ** 8 + 0.01))
        cu = bpy.data.curves.new(f'{name}_gw{side}', 'CURVE'); cu.dimensions = '3D'
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for pnt, co in zip(sp.points, pts):
            pnt.co = (*co, 1)
        cu.bevel_depth = 0.022; cu.bevel_resolution = 2
        go = bpy.data.objects.new(f'{name}_gw{side}', cu); bpy.context.collection.objects.link(go)
        go.data.materials.append(wood); go.location = loc; parts.append(go)
    # thwarts
    for u in (-0.55, -0.2, 0.2, 0.55):
        x = u * L / 2
        b = B / 2 * (1 - u * u) ** 0.55
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.025, depth=2 * b, location=(loc[0] + x, loc[1], loc[2] + G - 0.03))
        th = bpy.context.active_object; th.rotation_euler = (math.pi / 2, 0, 0); th.data.materials.append(wood)
        th.name = f'{name}_thwart'; parts.append(th)
    return hull, parts


def make_bale(name, size, loc, rot, mat, rope):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    o = lib.obj_from_bmesh(name, bm, mat)
    o.modifiers.new('Bevel', 'BEVEL').width = 0.04
    lib.add_subsurf(o, 2, 2)
    tex = bpy.data.textures.new(name + 'n', 'CLOUDS'); tex.noise_scale = 0.12
    d = o.modifiers.new('D', 'DISPLACE'); d.texture = tex; d.strength = 0.02
    lib.shade_smooth(o)
    o.location = loc; o.rotation_euler = rot
    for k in (-0.28, 0.28):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.012, major_segments=32, minor_segments=6)
        r = bpy.context.active_object; r.data.materials.append(rope)
        r.scale = (size[1] / 2 + 0.02, size[2] / 2 + 0.02, 1)
        r.rotation_euler = (0, math.pi / 2, 0)
        r.location = (k * size[0], 0, 0); r.parent = o; r.name = name + '_rope'
    return o


def build(variant='default'):
    scn = lib.reset()
    w, _ = lib.sky_world(scn, sun_elev_deg=3.5, sun_rot_deg=90.0, strength=0.6, air=1.2, dust=2.5, ozone=1.0)
    lib.sun('SunKey', elev=3.5, azim=0, strength=2.6, color=(1.0, 0.70, 0.45), angle=1.2)
    lib.area_light('Fill', (0.0, -6.0, 3.0), (60, 0, 0), 6.0, 60.0, color=(0.62, 0.72, 0.9))

    wood = mat_wood()
    post = mat_wood('Post', base='#4a4036', dark='#231d17', wet=0.7)
    hide = mat_rawhide(seed=1)
    hide2 = mat_rawhide('Rawhide2', base='#8c6a42', dark='#463020', seed=2)
    thong = mat_thong()
    hmat = lib.mat_hair('BisonHair', melanin=0.82, redness=0.55, rough=0.45)

    water = mat_water()
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, 0))
    wo = bpy.context.active_object; wo.name = 'Water'; wo.data.materials.append(water)

    make_dock(wood, post)
    hero = make_bag('BagHero', loc=(0.0, 1.15, DECK_Z), rot_z=math.radians(8), seed=3, mat=hide, thong=thong)
    b2 = make_bag('Bag2', size=(0.58, 0.37, 0.21), loc=(-0.55, 2.05, DECK_Z), rot_z=math.radians(-12), seed=5, mat=hide2, thong=thong)
    b3 = make_bag('Bag3', size=(0.55, 0.35, 0.23), loc=(-0.48, 2.0, DECK_Z + 0.215), rot_z=math.radians(-3), seed=8, mat=hide, thong=thong)
    bpy.context.view_layer.update()
    if FUR:
        lib.add_fur_curves(hero, hmat, density=FUR_DENSITY, length=0.017, radius=0.00045, mask_scale=5.0,
                           mask_threshold=0.36, soft=0.1, seed=3, curl=0.45, frizz=0.6)
        lib.add_fur_curves(bpy.data.objects['BagHero_flap'], hmat, density=FUR_DENSITY, length=0.012, radius=0.0004,
                           mask_scale=5.0, mask_threshold=0.42, soft=0.1, seed=4, curl=0.4, frizz=0.6, comb=(0, 1, -0.2))
        lib.add_fur_curves(b3, hmat, density=FUR_DENSITY * 0.6, length=0.016, radius=0.00045, mask_scale=4.0,
                           mask_threshold=0.45, soft=0.12, seed=8, curl=0.45, frizz=0.6, max_strands=120000)

    if variant == 'canoe':
        bark = mat_birchbark()
        gw = mat_wood('Gunwale', base='#7a6248', dark='#4a3a2a', wet=0.3)
        canoe, parts = make_canoe(hull_mat=bark, wood=gw)
        canvas = mat_simple('Canvas', '#8d8270', 0.9)
        rope = mat_simple('Rope', '#5e4a33', 0.8)
        rnd = random.Random(21)
        k = 0
        for x in (-2.3, -1.5, -0.7, 0.1, 0.9, 1.7):
            if k % 2 == 0:
                bg = make_bag(f'CBag{k}', size=(0.52, 0.34, 0.21), loc=(2.2 + x, 1.5 + rnd.uniform(-0.12, 0.12), -0.02),
                              rot_z=math.radians(90 + rnd.uniform(-10, 10)), seed=30 + k, mat=hide if k % 4 else hide2, thong=thong)
            else:
                make_bale(f'CBale{k}', (0.62, 0.45, 0.32), (2.2 + x, 1.5 + rnd.uniform(-0.1, 0.1), 0.12),
                          (0, 0, math.radians(90 + rnd.uniform(-8, 8))), canvas, rope)
            k += 1

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 420, 0.2))
    land = bpy.context.active_object; land.name = 'Land'; land.scale = (2400, 300, 1)
    land.data.materials.append(mat_simple('Land', '#1c2218', 0.9, emit='#8f98a0', emit_strength=0.22))
    protos = [make_spruce_proto(s) for s in range(4)]
    tree_mat = mat_simple('Spruce', '#18241c', 0.85, emit='#8f98a0', emit_strength=0.2)
    near_tree_mat = mat_simple('Spruce2', '#18241c', 0.85, emit='#8f98a0', emit_strength=0.1)
    scatter_trees(protos, tree_mat, 900, (-1100, 1100), (275, 560), (14, 26), seed=11, ground_z=0.2)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(-230, 190, 0.15))
    pt = bpy.context.active_object; pt.name = 'Land2'; pt.scale = (160, 60, 1)
    pt.data.materials.append(mat_simple('Land2', '#1c2218', 0.9, emit='#8f98a0', emit_strength=0.1))
    scatter_trees([make_spruce_proto(9), make_spruce_proto(10)], near_tree_mat, 220, (-300, -150), (165, 215), (12, 24), seed=12, ground_z=0.15, name='Trees2')
    # layer tags: far scenery is background, everything else foreground
    for o in scn.objects:
        o['layer'] = 'bg' if o.name.startswith(('Water', 'Land', 'Trees')) else 'fg'
    return scn, hero


ANCHOR_BAG = (0.0, 1.15, 0.70)
CAMS = {
    'D1': dict(cam=(0.36, -0.90, 1.05), tgt=ANCHOR_BAG, lens=40, fstop=2.8),          # cold open push-in
    'D2': dict(cam=(0.30, 0.45, 0.96), tgt=(0.05, 1.02, 0.79), lens=85, fstop=3.2),    # seam macro
    'D3': dict(cam=(-0.55, 0.25, 0.74), tgt=(0.05, 1.18, 0.66), lens=35, fstop=2.8),   # low close, bag + mist
    'D4': dict(cam=(1.45, -3.7, 2.05), tgt=(-0.2, 6.0, 1.0), lens=30, fstop=5.6, anchor=ANCHOR_BAG),  # wide end
    'D5': dict(cam=(-0.62, 0.10, 0.80), tgt=(0.05, 1.2, 0.70), lens=30, fstop=2.8),    # thumbnail
    'C1': dict(cam=(-1.2, -7.0, 1.7), tgt=(2.2, 1.5, 0.45), lens=35, fstop=5.6, variant='canoe', focus='Canoe'),
    'C2': dict(cam=(5.6, -3.4, 0.45), tgt=(2.2, 1.4, 0.35), lens=50, fstop=4.0, variant='canoe', focus='Canoe'),
    'C3': dict(cam=(3.6, 4.6, 1.35), tgt=(2.3, 3.0, 0.40), lens=50, fstop=3.2, variant='canoe', focus='CBale1'),
    'C3b': dict(cam=(3.35, -0.35, 1.75), tgt=(2.05, 1.45, 0.05), lens=40, fstop=4.0, variant='canoe', focus='CBale1'),  # cargo seen from above
}
MIST = (4.0, 260.0)


def composite(scn, strength=-1):
    lib.mist_compositor(scn, fog_color=srgb('#a9b2b6'), gamma=0.8, strength=0.7 if strength < 0 else strength,
                        blur_fog=0.65, blur_px=220)
