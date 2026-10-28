"""Open-country scenes: Frog Plain (la Grenouillère) with bur oaks; bison herds; a Red River cart line.

Variants
  plain    low ground with tall grass and oak groves at golden hour (G1, G2, G4)
  dusk     the same after sunset (G3)
  herd     bison grazing over rolling prairie, late afternoon (B1)
  horizon  a line of bison on a ridge against the evening sky (B2; one object per animal for fades)
  carts    a long line of Red River carts drawn by oxen (B3)
Illustrative reconstructions only: no specific event, place layout or person is depicted.
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import lib, props as P
from lib import srgb

TP = P.Terrain(amp=0.5, scale=0.01, seed=21, amp2=0.12, scale2=0.08)          # Frog Plain: low and flat
TH = P.Terrain(amp=7.0, scale=0.006, seed=5, amp2=0.8, scale2=0.03)             # rolling prairie


def _light(scn, variant):
    if variant == 'dusk':
        lib.sky_world(scn, sun_elev_deg=-2.0, sun_rot_deg=10.0, strength=1.0, air=1.0, dust=1.2)
        lib.sun('SunKey', elev=0.5, azim=-10, strength=0.35, color=(1.0, 0.5, 0.35), angle=2.0)
        lib.area_light('Sky', (0, -30, 40), (30, 0, 0), 80.0, 9000.0, color=(0.5, 0.6, 0.95))
    elif variant == 'horizon':
        lib.sky_world(scn, sun_elev_deg=0.5, sun_rot_deg=0.0, strength=0.8, air=1.4, dust=3.0)
        lib.sun('SunKey', elev=0.5, azim=0, strength=1.6, color=(1.0, 0.55, 0.3), angle=1.5)
        lib.area_light('Sky', (0, -60, 40), (40, 0, 0), 80.0, 5000.0, color=(0.55, 0.62, 0.9))
    elif variant == 'herd':     # backlit, late afternoon: rim light on fur, haze
        lib.sky_world(scn, sun_elev_deg=6.0, sun_rot_deg=12.0, strength=0.45, air=1.3, dust=2.6)
        lib.sun('SunKey', elev=6.0, azim=-12, strength=3.6, color=(1.0, 0.72, 0.46), angle=1.0)
        lib.area_light('Fill', (0, -80, 40), (55, 0, 0), 60.0, 900.0, color=(0.6, 0.7, 0.95))
    elif variant == 'carts':
        lib.sky_world(scn, sun_elev_deg=8.0, sun_rot_deg=-60.0, strength=0.4, air=1.3, dust=2.2)
        lib.sun('SunKey', elev=8.0, azim=60, strength=3.2, color=(1.0, 0.74, 0.5), angle=1.0)
        lib.area_light('Fill', (0, -80, 40), (55, 0, 0), 60.0, 1200.0, color=(0.6, 0.7, 0.95))
    else:
        lib.sky_world(scn, sun_elev_deg=5.0, sun_rot_deg=-8.0, strength=0.6, air=1.3, dust=2.4)
        lib.sun('SunKey', elev=5.0, azim=8, strength=3.0, color=(1.0, 0.7, 0.45), angle=1.0)
        lib.area_light('Fill', (0, -80, 30), (65, 0, 0), 60.0, 4000.0, color=(0.6, 0.7, 0.95))


def bison_fur(proto, hmat, ox=False, max_strands=200000):
    """Woolly forequarters, beard and head; short hair behind. Proto is at the origin, X forward."""
    import lib as _lib

    def lf(r):
        x, z = r[0], r[2]
        if ox:
            return 1.0 if z > 0.6 else 0.4
        if z < 0.5:                       # legs and belly: short hair, except the woolly front 'chaps'
            return 0.35 + (0.9 if (x > 0.35 and z > 0.25) else 0.0)
        front = min(1.0, max(0.0, (x + 0.1) / 0.7))
        return 0.6 + 2.0 * front
    _lib.add_fur_curves(proto, hmat, density=60000.0, length=0.045 if not ox else 0.018, radius=0.0016, mask_scale=2.0,
                        mask_threshold=0.0, soft=0.02, comb=(-1.0, 0.0, -0.7), frizz=0.8, seed=hash(proto.name) % 997,
                        points=5, max_strands=max_strands, curl=0.7 if not ox else 0.2, length_fn=lf)
    fur = bpy.data.objects[proto.name + '_fur']
    bpy.context.scene.collection.objects.unlink(fur)
    return fur


def _fur_on(proto, hmat, ox=False):
    bpy.context.scene.collection.objects.link(proto)
    bpy.context.view_layer.update()
    fur = bison_fur(proto, hmat, ox=ox, max_strands=90000 if ox else 200000)
    bpy.context.scene.collection.objects.unlink(proto)
    return fur


def herd_with_fur(protos, furs, placements, name):
    out = P.herd(protos, placements, name)
    col = bpy.data.collections[name]
    for o, (pi, loc, rz, sc) in zip(out, placements):
        f = bpy.data.objects.new(o.name + '_fur', furs[pi].data)
        col.objects.link(f)
        f.location, f.rotation_euler, f.scale = o.location, o.rotation_euler, o.scale
    return out


def build(variant='plain'):
    if variant == 'default':
        variant = 'plain'
    scn = lib.reset()
    _light(scn, variant)
    T = TP if variant in ('plain', 'dusk') else TH
    emit = {'dusk': '#6f7b92', 'horizon': '#c79a7a'}.get(variant, '#c9b79a')
    ground = P.mat_ground('Ground', '#6e6640', '#4d4a2c', dry='#8d7f4f', scale=0.05, bump=0.25)
    ground.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.12
    far = P.mat_ground('FarGround', '#857a56', '#625a3e', scale=0.01, emit=emit,
                       emit_strength=0.12 if variant in ('plain', 'dusk', 'horizon') else 0.04, bump=0.0)
    grass = P.mat_strand('Grass', '#4a4728', '#c6b27a', transl=0.35)
    if variant in ('plain', 'dusk'):
        grass = P.mat_strand('Grass', '#3f4a24', '#b9ad6c', transl=0.35)     # greener low ground in June
    bark = P.mat_principled('Bark', '#463f38', rough=0.9, var=0.6, dark='#2a2622', var_scale=2, bump_scale=50, bump_strength=0.5)
    leaves = P.mat_leaves('Leaves', '#46512a', '#273016', '#7d8a33')
    far_bark = P.mat_principled('FarBark', '#463f38', rough=0.9, emit=emit, emit_strength=0.1)
    far_leaves = P.mat_leaves('FarLeaves', '#4a5530', '#2b3318', '#7d8a33', emit=emit, emit_strength=0.12)
    coat = P.mat_bison()
    horn = P.mat_principled('Horn', '#1a1714', 0.4)

    T.mesh('Land_near', -160, 160, -80, 260, 160, 170, ground)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, -1.0))
    fo = bpy.context.active_object; fo.name = 'Land_far'; fo.scale = (6000, 6000, 1); fo.data.materials.append(far)
    T2 = P.Terrain(amp=14.0, scale=0.003, seed=9, amp2=2.0, scale2=0.015)
    T2.mesh('Land_hills', -1500, 1500, 250, 2500, 120, 90, far)
    for v in bpy.data.objects['Land_hills'].data.vertices:
        v.co.z = v.co.z * min(1.0, (v.co.y - 250) / 400.0) - 0.8

    rnd = random.Random(3)
    focus = None
    if variant in ('plain', 'dusk'):
        P.grass_curves('Grass_near', T, (-25, 30, -48, 10), 900, (0.35, 0.95), grass, seed=1, lean=(0.12, 0.05),
                       lean_var=0.3, max_strands=700000, clump=0.35, radius=0.0022)
        P.grass_curves('Grass_mid', T, (-80, 90, 10, 120), 40, (0.5, 1.0), grass, seed=2, radius=0.004, max_strands=500000, clump=0.4)
        tb = P.Batch()
        tips = []
        for i, (x, y, h) in enumerate([(-8, 52, 13), (4, 60, 15), (14, 48, 12), (22, 66, 14), (-18, 70, 12), (9, 78, 13),
                                       (30, 56, 11), (-30, 90, 12), (8, 52 - 30, 9)]):
            tips += P.tree(tb, (x, y), h, seed=60 + i, kind='oak', depth=5, leaves='cards', z0=T.z(x, y), crown=1.15)
        tb.build('Trees_oaks', [bark, leaves])
        lc = P.mat_leafcards('OakLeaves', tint=(0.95, 0.95, 0.85) if variant == 'plain' else (0.8, 0.85, 0.9), transl=0.4)
        P.leaf_cards('Trees_oaks_leaves', tips, lc, per_tip=190, size=(0.2, 0.36), spread=1.75, seed=3,
                     min_z=lambda p: T.z(p[0], p[1]) + 3.0)
        tf = P.Batch()
        for i in range(420):
            x = rnd.uniform(-700, 700)
            y = rnd.uniform(320, 440) + 40 * math.sin(x / 150)
            P.tree(tf, (x, y), rnd.uniform(14, 22), seed=300 + i, kind='oak', depth=3, leaves=True, z0=0.0, leaf_size=2.2)
        tf.build('Trees_far', [far_bark, far_leaves])
        focus = bpy.data.objects['Trees_oaks']
    elif variant == 'herd':
        P.grass_curves('Grass_near', T, (-8, 8, -22, 2), 1400, (0.3, 0.75), grass, seed=1, max_strands=300000, clump=0.4)
        P.grass_curves('Grass_mid', T, (-70, 70, 2, 90), 40, (0.15, 0.35), grass, seed=2, radius=0.006, max_strands=500000, clump=0.4)
        P.grass_curves('Grass_mid2', T, (-90, 90, 90, 280), 14, (0.25, 0.5), grass, seed=5, radius=0.013, max_strands=500000, clump=0.4)
        P.grass_curves('Grass_far', T, (-170, 170, 280, 700), 4.5, (0.35, 0.7), grass, seed=4, radius=0.014, max_strands=700000, clump=0.5)
        protos = [P.bison_proto(f'BisonP{i}', 'stand' if i % 3 else 'graze', seed=i, coat=coat, horn=horn) for i in range(6)]
        hmat = lib.mat_hair('BisonFur', melanin=0.9, redness=0.45, rough=0.5)
        furs = [_fur_on(p, hmat) for p in protos]
        pl = []
        for g in range(12):   # loose groups inside the long-lens corridor
            gy = rnd.uniform(38, 240)
            gx = rnd.uniform(-0.16, 0.16) * gy
            for k in range(rnd.randint(8, 16)):
                x, y = gx + rnd.gauss(0, 0.05 * gy + 2), gy + rnd.gauss(0, 6)
                rz = (0.0 if rnd.random() < 0.5 else math.pi) + rnd.uniform(-0.55, 0.55)   # mostly broadside
                if rnd.random() < 0.15:
                    rz = rnd.uniform(0, 6.28)
                pl.append((rnd.randrange(6), (x, y, T.z(x, y) - 0.05), rz, rnd.uniform(0.85, 1.1)))
        herd = herd_with_fur(protos, furs, pl, 'Bison')
        focus = herd[0]
    elif variant == 'horizon':
        P.grass_curves('Grass_near', T, (-10, 10, -40, -28), 900, (0.25, 0.6), grass, seed=1, max_strands=300000, clump=0.4)
        P.grass_curves('Grass_mid', T, (-40, 40, -28, 70), 30, (0.08, 0.22), grass, seed=2, radius=0.008, max_strands=700000, clump=0.4)
        P.grass_curves('Grass_far', T, (-160, 160, 70, 420), 3.5, (0.3, 0.6), grass, seed=4, radius=0.02, max_strands=500000, clump=0.5)
        protos = [P.bison_proto(f'BisonP{i}', 'graze' if i % 2 else 'stand', seed=10 + i, coat=coat, horn=horn) for i in range(5)]
        hmat = lib.mat_hair('BisonFur', melanin=0.9, redness=0.45, rough=0.5)
        furs = [_fur_on(p, hmat) for p in protos]
        pl = []
        n = 7
        for k in range(n):
            x = -13.5 + k * 27 / (n - 1) + rnd.uniform(-0.6, 0.6)
            y = 55 + rnd.uniform(-2, 2)
            ridge = T.z(x, y)
            pl.append((k % 5, (x, y, ridge - 0.05), (0 if rnd.random() < 0.5 else math.pi) + rnd.uniform(-0.25, 0.25), rnd.uniform(0.9, 1.08)))
        herd = herd_with_fur(protos, furs, pl, 'Bison')
        focus = herd[3]
    elif variant == 'carts':
        P.grass_curves('Grass_near', T, (-40, 40, -40, 20), 500, (0.1, 0.35), grass, seed=1, max_strands=600000, clump=0.4)
        P.grass_curves('Grass_mid', T, (-150, 170, 20, 260), 16, (0.2, 0.45), grass, seed=2, radius=0.014, max_strands=900000, clump=0.4)
        wood = P.mat_principled('CartWood', '#8a7457', rough=0.85, var=0.6, dark='#5a4a38', var_scale=8)
        load = P.mat_principled('Load', '#9a8a6e', rough=0.95)
        ox_coat = P.mat_bison('OxCoat', ox=True)
        cb = P.Batch()
        ox_protos = [P.bison_proto(f'OxP{i}', 'stand', seed=40 + i, ox=True, coat=ox_coat) for i in range(3)]
        oxhair = lib.mat_hair('OxHair', melanin=0.75, redness=0.7, rough=0.5)
        ox_furs = [_fur_on(p, oxhair, ox=True) for p in ox_protos]
        pl = []
        a, b = Vector((-70, 32, 0)), Vector((150, 190, 0))
        d = (b - a).normalized()
        rz = math.atan2(d.y, d.x)
        n = 34
        for k in range(n):
            p = a.lerp(b, k / (n - 1)) + Vector((rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), 0))
            z = T.z(p.x, p.y)
            P.cart(cb, (p.x, p.y, z), rz + rnd.uniform(-0.05, 0.05), seed=k, wheel_mi=0, body_mi=0, load_mi=1)
            q = p + d * 4.3
            pl.append((k % 3, (q.x, q.y, T.z(q.x, q.y) - 0.05), rz, 0.9))
        cb.build('Carts', [wood, load])
        herd_with_fur(ox_protos, ox_furs, pl, 'Oxen')
        focus = bpy.data.objects['Carts']

    for o in scn.objects:
        fg = o.name.startswith(('Bison', 'Oxen', 'Carts', 'Trees_oaks'))
        o['layer'] = 'fg' if fg else 'bg'
    return scn, focus


def _c(T, x, y, h):
    return (x, y, T.z(x, y) + h)


CAMS = {
    'G1': dict(cam=_c(TP, 0.0, -40.0, 1.7), tgt=(4.0, 60.0, 5.0), lens=32, fstop=11.0, focus_dist=90.0, variant='plain'),
    'G2': dict(cam=_c(TP, 2.0, -38.0, 0.6), tgt=_c(TP, 3.0, -33.0, 0.62), lens=85, fstop=2.8, focus_dist=3.0, variant='plain'),
    'G3': dict(cam=_c(TP, -14.0, -44.0, 1.6), tgt=(6.0, 60.0, 4.5), lens=32, fstop=11.0, focus_dist=90.0, variant='dusk'),
    'G4': dict(cam=_c(TP, -2.0, 30.0, 1.4), tgt=(4.0, 60.0, 8.5), lens=26, fstop=8.0, focus_dist=30.0, variant='plain'),
    'B1': dict(cam=_c(TH, 0.0, -12.0, 1.5), tgt=_c(TH, 0.0, 110.0, 1.4), lens=100, fstop=5.6, focus_dist=80.0, variant='herd'),
    'B2': dict(cam=_c(TH, 0.0, -40.0, 1.7), tgt=_c(TH, 0.0, 55.0, 1.6), lens=135, fstop=8.0, focus_dist=95.0, variant='horizon', bg_clean=True),
    'B3': dict(cam=_c(TH, -40.0, -6.0, 2.2), tgt=_c(TH, 10.0, 75.0, 1.4), lens=75, fstop=11.0, focus_dist=95.0, variant='carts'),
}
MIST = (40.0, 1400.0)


def composite(scn, strength=-1):
    v = 'dusk' if 'Sky' in bpy.data.objects and bpy.data.lights['SunKey'].energy < 0.5 else 'day'
    col = '#6f7b92' if v == 'dusk' else '#cdb89a'
    busy = 'Bison' in bpy.data.collections and 'Sky' not in bpy.data.objects or 'Carts' in bpy.data.objects
    st = 0.35 if busy else 0.6
    lib.mist_compositor(scn, fog_color=srgb(col), gamma=0.9, strength=st if strength < 0 else strength, blur_fog=0.4, blur_px=140)
