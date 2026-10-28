"""A governor's writing table on a winter night: candle, quill, inkwell, a written sheet, sealed letters.

Illustrative only. The sheet carries generated, illegible pen strokes and is NOT a facsimile of
Miles Macdonell's proclamation of 8 January 1814 or of any other document.
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector
import lib, props as P
from lib import node, link, srgb

TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../textures/paper_scribble.png')
TOP = 0.76


def mat_paper(name='Paper', tex=TEX, blank=False):
    m, nt, b, out = lib.mat_new(name)
    b.inputs['Roughness'].default_value = 0.85
    b.inputs['Subsurface Weight'].default_value = 0.08
    b.inputs['Subsurface Radius'].default_value = (0.01, 0.008, 0.005)
    if blank:
        b.inputs['Base Color'].default_value = (*srgb('#d7c9a8'), 1)
    else:
        im = node(nt, 'ShaderNodeTexImage', (-500, 0))
        im.image = bpy.data.images.load(os.path.abspath(tex))
        tc = node(nt, 'ShaderNodeTexCoord', (-800, 0))
        link(nt, tc.outputs['UV'], im.inputs['Vector'])
        link(nt, im.outputs['Color'], b.inputs['Base Color'])
    return m


def sheet(name, size, loc, rot_z, mat, curl=0.012, seed=0, nx=24, ny=30):
    """Slightly cockled sheet with UVs (0..1)."""
    sx, sy = size
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new()
    verts = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            z = curl * (abs(u - 0.5) * 2) ** 3 + 0.002 * math.sin(u * 7 + seed) * math.sin(v * 5 + seed)
            row.append(bm.verts.new(((u - 0.5) * sx, (v - 0.5) * sy, z)))
        verts.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
            for lp, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = (uu / nx, vv / ny)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    sol = o.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.0004
    return o


def quill(name, base, tip, shaft_mat, vane_mat):
    """Goose quill: curved shaft with a vane on each side, tapering to a cut nib."""
    base, tip = Vector(base), Vector(tip)
    d = tip - base
    L = d.length
    dn = d.normalized()
    side = dn.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(dn).normalized()
    pts = [base + d * t + up * (math.sin(t * math.pi) * 0.025) for t in [i / 20 for i in range(21)]]
    rad = [0.0035 * (1 - 0.6 * (i / 20)) if i < 19 else 0.0012 for i in range(21)]
    P.tube(name + '_shaft', pts, rad, shaft_mat, segs=8)
    verts, faces = [], []
    n = 30
    for sgn in (-1, 1):
        o = len(verts)
        for i in range(n + 1):
            t = 0.08 + 0.62 * i / n    # vane over the back two-thirds
            p = base + d * (1 - t) + up * (math.sin((1 - t) * math.pi) * 0.025)
            w = 0.017 * math.sin(math.pi * i / n) ** 0.6 * (1.3 if sgn > 0 else 0.7)
            verts.append(tuple(p))
            q = p + side * sgn * w + up * (-0.004) - dn * 0.012
            verts.append(tuple(q))
        for i in range(n):
            a = o + i * 2
            faces.append((a, a + 2, a + 3, a + 1))
    return P.mesh_obj(name + '_vane', verts, faces, vane_mat)


def build(variant='default'):
    scn = lib.reset()
    lib.flat_world(scn, srgb('#05070b'), 1.0)
    wood = P.mat_principled('TableWood', '#5a3f2a', rough=0.62, var=0.7, dark='#2e1f15', var_scale=6, bump_scale=120, bump_strength=0.1)
    logs = P.mat_principled('WallLogs', '#4a3b2e', rough=0.9, var=0.6, dark='#241c16', var_scale=3, bump_scale=30, bump_strength=0.4)
    paper = mat_paper()
    blank = mat_paper('PaperBlank', blank=True)
    glass = P.mat_principled('Inkwell', '#14161a', rough=0.12, spec=0.8, coat=0.6)
    ink = P.mat_principled('Ink', '#020203', rough=0.03, spec=1.0)
    wax = P.mat_principled('CandleWax', '#e9dfc4', rough=0.4, sss=0.6, sss_rad=(0.06, 0.04, 0.02))
    brass = P.mat_principled('Brass', '#b08a4a', rough=0.32, metallic=1.0, var=0.4, dark='#5d4523', var_scale=12)
    seal = P.mat_principled('SealWax', '#7a1410', rough=0.35, coat=0.3)
    shaft = P.mat_principled('QuillShaft', '#d9cfb8', rough=0.35, sss=0.3, sss_rad=(0.01, 0.01, 0.01))
    vane = P.mat_translucent_mix('QuillVane', '#cfc6b3', '#e0d4bb', mix=0.35, rough=0.75, var_dark='#8e8371', var=0.6, scale=180, bump=0.4)
    leather = P.mat_principled('Leather', '#3a2416', rough=0.6, var=0.6, dark='#1c110a', var_scale=10, bump_scale=200, bump_strength=0.2)
    flame = P.mat_flame('CandleFlame', strength=26.0)
    frost = P.mat_emit('Window', '#3d5878', 1.4)

    # table and wall
    b = P.Batch()
    for i in range(5):
        b.box((0, -0.45 + i * 0.22, TOP - 0.025), (2.2, 0.215, 0.05), 0.0)
    b.box((-0.95, 0.0, TOP / 2), (0.08, 0.9, TOP - 0.05))
    b.box((0.95, 0.0, TOP / 2), (0.08, 0.9, TOP - 0.05))
    b.build('Table', [wood], smooth=False)
    wb = P.Batch()
    P.log_wall(wb, (-4, 0.9), (4, 0.9), -0.2, 3.0, r=0.16, seed=3)
    wb.build('Wall', [logs])
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.55, 0.75, 1.55), rotation=(math.pi / 2, 0, 0))
    win = bpy.context.active_object; win.name = 'WindowGlow'; win.scale = (0.7, 0.55, 1); win.data.materials.append(frost)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    fl = bpy.context.active_object; fl.name = 'Floor'; fl.scale = (8, 8, 1); fl.data.materials.append(logs)

    # writing
    sh = sheet('Sheet', (0.32, 0.41), (-0.05, -0.12, TOP + 0.0045), math.radians(-6), paper, curl=0.004, seed=1)
    sheet('Sheet2', (0.30, 0.39), (0.12, 0.06, TOP + 0.0005), math.radians(9), blank, curl=0.003, seed=2)
    for k, (x, y, r) in enumerate([(0.5, 0.18, 0.2), (0.48, 0.2, -0.1)]):
        lt = sheet(f'Letter{k}', (0.2, 0.12), (x, y, TOP + 0.002 + k * 0.004), r, blank, curl=0.003, seed=5 + k, nx=8, ny=6)
        P.stone(f'Seal{k}', (0.017, 0.017, 0.004), (x + 0.01, y - 0.005, TOP + 0.008 + k * 0.004), seal, seed=k, rough=0.08)
    iw = P.lathe('Inkwell', [(0, 0), (0.035, 0), (0.042, 0.01), (0.044, 0.04), (0.03, 0.055), (0.016, 0.058), (0.016, 0.066),
                             (0.012, 0.066), (0.012, 0.05), (0, 0.05)], glass, segs=40)
    iw.location = (0.27, -0.02, TOP)
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=0.0115, fill_type='NGON', location=(0.27, -0.02, TOP + 0.063))
    bpy.context.active_object.data.materials.append(ink)
    quill('Quill', (0.25, 0.06, TOP + 0.075), (0.02, -0.16, TOP + 0.004), shaft, vane)
    # candle in a brass stick
    cx, cy = -0.3, 0.22
    stick = P.lathe('Candlestick', [(0, 0), (0.06, 0), (0.062, 0.008), (0.05, 0.014), (0.018, 0.02), (0.014, 0.08), (0.022, 0.1),
                                    (0.026, 0.11), (0.012, 0.112), (0, 0.112)], brass, segs=40)
    stick.location = (cx, cy, TOP)
    cnd = P.lathe('Candle', [(0, 0), (0.011, 0), (0.011, 0.14), (0.009, 0.147), (0.003, 0.149), (0, 0.149)], wax, segs=24)
    cnd.location = (cx, cy, TOP + 0.105)
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.006, radius2=0.0, depth=0.035, location=(cx, cy, TOP + 0.272))
    f = bpy.context.active_object; f.name = 'Flame'; f.data.materials.append(flame)
    sub = f.modifiers.new('s', 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
    lib.point_light('CandleLight', (cx, cy, TOP + 0.285), 26.0, color=(1.0, 0.62, 0.3), radius=0.008)
    lib.area_light('WinFill', (0.55, 0.6, 1.55), (-80, 0, 0), 0.8, 2.0, color=(0.5, 0.65, 1.0))
    # ledger
    lb = P.Batch()
    lb.box((-0.62, -0.18, TOP + 0.025), (0.24, 0.32, 0.05), math.radians(12))
    lb.build('Ledger', [leather], smooth=False)
    for o in scn.objects:
        o['layer'] = 'bg' if o.name in ('Wall', 'WindowGlow', 'Floor') else 'fg'
    return scn, sh


CAMS = {
    'W1': dict(cam=(-0.62, -1.05, 1.3), tgt=(-0.02, 0.0, 0.82), lens=38, fstop=2.8, focus_dist=1.25),
    'W2': dict(cam=(-0.12, -0.44, 0.9), tgt=(0.0, -0.16, 0.765), lens=85, fstop=3.5, focus_dist=0.33),
}
MIST = None


def composite(scn, strength=-1):
    scn.render.use_compositing = False
