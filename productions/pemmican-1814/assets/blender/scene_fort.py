"""A palisaded fur-trade/colony post on a river terrace, in winter (F1, F2) and summer (F3).

Generic reconstruction of the kind of log post built along the Red River in the 1810s: a
picket palisade, corner blockhouse, squared-log houses with bark/plank roofs. It is not a
plan-accurate model of Fort Douglas or Fort Gibraltar, and the film labels it as illustrative.
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import lib, props as P
from lib import srgb
import scene_dock as SD


def ground_z(x, y):
    """River terrace: flat to y=34, bank down to the river at y=46..128, far bank rises again."""
    n = P.Terrain(amp=0.6, scale=0.02, seed=3, amp2=0.08, scale2=0.15).z(x, y)
    if y < 34:
        return n
    if y < 46:
        f = (y - 34) / 12
        return n * (1 - f) - 4.2 * (f * f * (3 - 2 * f))
    if y < 128:
        return -4.2
    if y < 140:
        f = (y - 128) / 12
        return -4.2 * (1 - f * f * (3 - 2 * f)) + n * f
    return n


class _T:
    z = staticmethod(ground_z)


def build(variant='winter'):
    scn = lib.reset()
    summer = variant == 'summer'
    if summer:
        lib.sky_world(scn, sun_elev_deg=9.0, sun_rot_deg=-35.0, strength=0.6, air=1.2, dust=1.8)
        lib.sun('SunKey', elev=9.0, azim=35, strength=3.0, color=(1.0, 0.75, 0.5), angle=1.0)
        lib.area_light('Fill', (0, -90, 40), (55, 0, 0), 60.0, 3500.0, color=(0.6, 0.7, 0.95))
    else:
        lib.sky_world(scn, sun_elev_deg=6.0, sun_rot_deg=-60.0, strength=0.75, air=1.6, dust=3.5, ozone=1.2)
        lib.sun('SunKey', elev=6.0, azim=60, strength=1.3, color=(1.0, 0.8, 0.62), angle=3.0)
        lib.area_light('Fill', (0, -90, 50), (50, 0, 0), 80.0, 26000.0, color=(0.72, 0.8, 1.0))

    if summer:
        gmat = P.mat_ground('Ground', '#5d5a32', '#3f4024', dry='#8a7d4a', scale=0.05, bump=0.2)
        gmat.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.12   # no backlit sheen
        far = P.mat_ground('FarGround', '#6c6a40', '#55532f', scale=0.01, emit='#b9b49a', emit_strength=0.1, bump=0)
    else:
        gmat = P.mat_ground('Snow', '#e9eef4', '#b9c4d3', scale=0.09, bump=0.25)
        gmat.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.2
        gmat.node_tree.nodes['Principled BSDF'].inputs['Subsurface Radius'].default_value = (0.3, 0.5, 0.9)
        far = P.mat_ground('FarSnow', '#dfe5ee', '#c9d2de', scale=0.01, emit='#c4ccd8', emit_strength=0.25, bump=0)
    logs = P.mat_principled('Logs', '#7b6e60' if not summer else '#7a6450', rough=0.85, var=0.7, dark='#3f372f', var_scale=3, bump_scale=40, bump_strength=0.35)
    roof = P.mat_principled('Roof', '#4a4036', rough=0.9, var=0.5, dark='#2a241f', var_scale=4, bump_scale=30, bump_strength=0.3)
    snow = P.mat_principled('RoofSnow', '#eef2f7', rough=0.6, sss=0.25, sss_rad=(0.3, 0.5, 0.9), bump_scale=12, bump_strength=0.15)
    clay = P.mat_principled('Chimney', '#7d7166', rough=0.9, var=0.6, dark='#4d443c', var_scale=8, bump_scale=30, bump_strength=0.4)
    bark = P.mat_principled('Bark', '#4b4540', rough=0.9, var=0.6, dark='#2d2925', var_scale=2, bump_scale=50, bump_strength=0.4)
    leaves = P.mat_leaves('Leaves', '#4a5228', '#2a3116', '#7d8a33')
    far_bark = P.mat_principled('FarBark', '#4b4540', rough=0.9, emit='#c4ccd8' if not summer else '#b9b49a', emit_strength=0.08)
    far_leaves = P.mat_leaves('FarLeaves', '#4a5228', '#2a3116', '#7d8a33', emit='#b9b49a', emit_strength=0.08)

    # ---------- terrain
    P.Terrain().mesh  # noqa (keeps API symmetric)
    xs = (-160, 160)
    verts, faces = [], []
    nx, ny = 160, 140
    import numpy as np
    X = np.linspace(xs[0], xs[1], nx)
    Y = np.concatenate([np.linspace(-120, 30, 50), np.linspace(30.5, 150, 90)])
    for y in Y:
        for x in X:
            verts.append((x, y, ground_z(x, y)))
    for j in range(len(Y) - 1):
        for i in range(nx - 1):
            faces.append((j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i))
    P.mesh_obj('Land_near', verts, faces, gmat)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, -0.3))
    fo = bpy.context.active_object; fo.name = 'Land_far'; fo.scale = (5000, 5000, 1); fo.data.materials.append(far)
    # river
    if summer:
        wm = SD.mat_water()
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 87, -3.9))
        r = bpy.context.active_object; r.name = 'Land_river'; r.scale = (900, 86, 1); r.data.materials.append(wm)
    else:
        ice = P.mat_ground('Ice', '#d5dde6', '#9fb0bf', scale=0.04, bump=0.05)
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 87, -4.0))
        r = bpy.context.active_object; r.name = 'Land_river'; r.scale = (900, 86, 1); r.data.materials.append(ice)

    # ---------- trees along both banks
    tb = P.Batch()
    rnd = random.Random(5)
    tips_all = []
    for i in range(120):
        x = rnd.uniform(-150, 150)
        y = rnd.uniform(28, 44)
        if abs(x) < 26 and y < 36:
            continue
        tp = P.tree(tb, (x, y), rnd.uniform(12, 19), seed=i, kind='oak' if rnd.random() < 0.6 else 'elm', depth=4,
                    leaves='cards' if summer else False, z0=ground_z(x, y))
        if summer and tp:
            tips_all += tp
    tb.build('Trees_near', [bark, leaves])
    if summer:
        P.leaf_cards('Trees_near_leaves', tips_all, P.mat_leafcards('Leafcards', transl=0.4), per_tip=120, size=(0.2, 0.36), spread=1.8, seed=5,
                     min_z=lambda p: ground_z(p[0], p[1]) + 3.0)
    tf = P.Batch()
    for i in range(170):
        x = rnd.uniform(-260, 260)
        y = rnd.uniform(132, 190)
        P.tree(tf, (x, y), rnd.uniform(10, 17), seed=200 + i, kind='elm', depth=3, leaves=summer, z0=ground_z(x, y))
    tf.build('Trees_far', [far_bark, far_leaves])
    spr = [SD.make_spruce_proto(s) for s in range(3)]
    sp_mat = SD.mat_simple('Spruce', '#1b241c', 0.85, emit='#c4ccd8' if not summer else '#b9b49a', emit_strength=0.1)
    SD.scatter_trees(spr, sp_mat, 140, (-300, 300), (150, 240), (12, 22), seed=7, ground_z=0.0, name='Trees_spruce')

    # ---------- the post
    fb = P.Batch()
    pal = [(-22, -18), (22, -18), (22, 18), (-22, 18)]
    P.palisade(fb, pal, height=4.0, r=0.15, seed=1, gaps=[(0, 0.46, 0.54)], mat_index=0)
    chim = []
    for k, (c, sz, wh, rh, rot) in enumerate([((-9, 4), (14, 7), 3.0, 2.4, 0.0), ((10, 5), (12, 7), 3.0, 2.3, math.pi / 2),
                                             ((0, 12.5), (11, 6), 2.8, 2.1, 0.0), ((-12, -9), (8, 6), 2.6, 2.0, 0.0)]):
        ch = P.log_building(fb, c, sz, wh, rh, rot, seed=10 + k, wall_mi=0, roof_mi=1, snow_mi=None if summer else 2,
                            chimney_mi=3 if k < 3 else None)
        if ch:
            chim.append(ch)
    # corner blockhouses (two storeys, upper one overhanging)
    for k, (bx, by) in enumerate([(22, 18), (-22, -18)]):
        P.log_building(fb, (bx, by), (5, 5), 3.2, 0.1, math.pi / 4, seed=40 + k, wall_mi=0, roof_mi=1, snow_mi=None)
        cb = P.Batch()
        P.log_building(fb, (bx, by), (6, 6), 6.0, 2.6, math.pi / 4, seed=50 + k, wall_mi=0, roof_mi=1,
                       snow_mi=None if summer else 2)
    # gate leaves, slightly open
    for side in (-1, 1):   # gate leaves of pickets, the right one swung slightly open
        ang = 0.0 if side < 0 else -0.55
        hinge = Vector((side * 1.85, -18.15, 0))
        for k in range(6):
            off = (k + 0.5) * 0.3 * -side
            p = hinge + Vector((off * math.cos(ang), off * math.sin(ang) * -side, 0))
            fb.tube([p + Vector((0, 0, -0.2)), p + Vector((0, 0, 3.7)), p + Vector((0, 0, 4.0))], [0.14, 0.13, 0.01], segs=7)
        for zz in (0.8, 2.9):
            a = hinge + Vector((0, 0, zz))
            b = hinge + Vector((1.8 * -side * math.cos(ang), 1.8 * math.sin(ang), zz))
            fb.tube([a + Vector((0, -0.17, 0)), b + Vector((0, -0.17, 0))], 0.07, segs=6)
    # flagstaff without flag
    fb.tube([(3, -6, 0), (3, -6, 13)], [0.09, 0.05], segs=6)
    fort = fb.build('Fort', [logs, roof, snow, clay])

    # snow drifts against the palisade (winter)
    if not summer:
        db = P.Batch()
        rnd2 = random.Random(9)
        for i in range(140):
            side = rnd2.randrange(4)
            a, b = Vector((*pal[side], 0)), Vector((*pal[(side + 1) % 4], 0))
            p = a.lerp(b, rnd2.random())
            out = Vector((p.x, p.y, 0)).normalized() * 0.8
            # sunk so only the soft crown shows above the ground snow (no dark undersides)
            r = rnd2.uniform(0.8, 1.6)
            x, y = p.x + out.x, p.y + out.y
            db.ico((x, y, ground_z(x, y) - 0.3 * r), r, (1.6, 1.6, 0.5), subdiv=3, jitter=0.15, seed=i)
        db.build('Drifts', [gmat])
    # dry grass and willow scrub poking through the snow in the foreground
    if not summer:
        gm = P.mat_strand('DryGrass', '#5a4c33', '#b59a6a', transl=0.2)
        P.grass_curves('Grass_fg', _T, (-90, 60, -110, -24), 9, (0.15, 0.6), gm, seed=3,
                       lean=(0.1, 0.05), lean_var=0.3, radius=0.0025, max_strands=420000, clump=0.5)
    else:
        # June grass only where the F3 camera sees it (18-80 m in front of it), dense enough to hide the ground
        gm = P.mat_strand('Grass', '#3f4a24', '#a8a060', transl=0.35)
        P.grass_curves('Grass_fg', _T, (-45, 62, -64, -19), 230, (0.25, 0.7), gm, seed=3,
                       lean=(0.06, 0.03), lean_var=0.18, radius=0.004, max_strands=1100000, clump=0.3)
        for k, reg in enumerate([(22.5, 75, -19, 25), (-80, -22.5, -19, 25)]):     # beside the palisade
            P.grass_curves(f'Grass_side{k}', _T, reg, 110, (0.25, 0.7), gm, seed=11 + k,
                           lean=(0.06, 0.03), lean_var=0.18, radius=0.005, max_strands=600000, clump=0.3)
    sb = P.Batch()
    rnd3 = random.Random(17)
    for i in range(26):
        x, y = rnd3.uniform(-90, 50), rnd3.uniform(-100, -40)
        P.tree(sb, (x, y), rnd3.uniform(1.4, 3.0), seed=500 + i, kind='elm', depth=3, z0=ground_z(x, y))
    sb.build('Trees_scrub', [bark])
    if not summer:
        # trampled path to the gate (decal strip over the snow) and a snow-capped woodpile
        wb = P.Batch()
        rw = random.Random(4)
        for layer in range(5):
            for k in range(7 - layer):
                x0 = 5.0 + k * 0.32 + layer * 0.16
                z = 0.17 + layer * 0.28
                wb.tube([(x0, -20.6, z), (x0 + rw.uniform(-0.05, 0.05), -19.2, z)], 0.15 * rw.uniform(0.85, 1.1), segs=8)
        wb.build('Woodpile', [logs])
        sb = P.Batch()
        sb.ico((5.95, -19.9, 1.62), 1.0, (1.25, 0.85, 0.22), subdiv=3, jitter=0.25, seed=2)
        sb.build('WoodpileSnow', [snow])
    global POINTS
    POINTS = {f'chimney{i}': c for i, c in enumerate(chim)}

    for o in scn.objects:
        o['layer'] = 'fg' if o.name in ('Fort', 'Drifts', 'Woodpile', 'WoodpileSnow') else 'bg'
    return scn, fort


POINTS = {}
CAMS = {
    'F1': dict(cam=(-33.0, -60.0, 5.5), tgt=(2.0, 0.0, 3.6), lens=40, fstop=11.0, focus_dist=65.0, variant='winter',
               fg_holdout=True),
    'F2': dict(cam=(9.0, -36.0, 1.75), tgt=(0.0, -18.0, 3.4), lens=30, fstop=8.0, focus_dist=21.0, variant='winter',
               fg_holdout=True),
    'F3': dict(cam=(46.0, -66.0, 6.0), tgt=(0.0, 2.0, 3.0), lens=35, fstop=11.0, focus_dist=80.0, variant='summer',
               fg_holdout=True),
}
MIST = (30.0, 900.0)


def composite(scn, strength=-1):
    summer = bpy.data.objects.get('Land_river') and bpy.data.objects['Land_river'].data.materials[0].name.startswith('Water')
    lib.mist_compositor(scn, fog_color=srgb('#d5dce5' if not summer else '#c9c3ae'), gamma=0.85,
                        strength=0.6 if strength < 0 else strength, blur_fog=0.4, blur_px=140)
