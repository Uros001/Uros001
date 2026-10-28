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
        lib.sky_world(scn, sun_elev_deg=1.2, sun_rot_deg=4.0, strength=0.8, air=1.4, dust=3.0)
        lib.sun('SunKey', elev=1.2, azim=-4, strength=1.6, color=(1.0, 0.55, 0.3), angle=1.5)
        lib.area_light('Sky', (0, -60, 40), (40, 0, 0), 80.0, 5000.0, color=(0.55, 0.62, 0.9))
    elif variant == 'herd':
        lib.sky_world(scn, sun_elev_deg=9.0, sun_rot_deg=-70.0, strength=0.4, air=1.2, dust=1.8)
        lib.sun('SunKey', elev=9.0, azim=70, strength=3.4, color=(1.0, 0.74, 0.5), angle=1.0)
        lib.area_light('Fill', (0, -80, 40), (55, 0, 0), 60.0, 1200.0, color=(0.6, 0.7, 0.95))
    elif variant == 'carts':
        lib.sky_world(scn, sun_elev_deg=8.0, sun_rot_deg=-60.0, strength=0.4, air=1.3, dust=2.2)
        lib.sun('SunKey', elev=8.0, azim=60, strength=3.2, color=(1.0, 0.74, 0.5), angle=1.0)
        lib.area_light('Fill', (0, -80, 40), (55, 0, 0), 60.0, 1200.0, color=(0.6, 0.7, 0.95))
    else:
        lib.sky_world(scn, sun_elev_deg=5.0, sun_rot_deg=-8.0, strength=0.6, air=1.3, dust=2.4)
        lib.sun('SunKey', elev=5.0, azim=8, strength=3.0, color=(1.0, 0.7, 0.45), angle=1.0)
        lib.area_light('Fill', (0, -80, 30), (65, 0, 0), 60.0, 4000.0, color=(0.6, 0.7, 0.95))


def build(variant='plain'):
    if variant == 'default':
        variant = 'plain'
    scn = lib.reset()
    _light(scn, variant)
    T = TP if variant in ('plain', 'dusk') else TH
    emit = {'dusk': '#6f7b92', 'horizon': '#c79a7a'}.get(variant, '#c9b79a')
    ground = P.mat_ground('Ground', '#6e6640', '#4d4a2c', dry='#8d7f4f', scale=0.05, bump=0.25)
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
        for i, (x, y, h) in enumerate([(-8, 52, 13), (4, 60, 15), (14, 48, 12), (22, 66, 14), (-18, 70, 12), (9, 78, 13),
                                       (30, 56, 11), (-30, 90, 12), (8, 52 - 30, 9)]):
            P.tree(tb, (x, y), h, seed=60 + i, kind='oak', depth=4, leaves=True, z0=T.z(x, y), crown=1.15)
        tb.build('Trees_oaks', [bark, leaves])
        tf = P.Batch()
        for i in range(420):
            x = rnd.uniform(-700, 700)
            y = rnd.uniform(320, 440) + 40 * math.sin(x / 150)
            P.tree(tf, (x, y), rnd.uniform(14, 22), seed=300 + i, kind='oak', depth=3, leaves=True, z0=0.0, leaf_size=2.2)
        tf.build('Trees_far', [far_bark, far_leaves])
        focus = bpy.data.objects['Trees_oaks']
    elif variant == 'herd':
        P.grass_curves('Grass_near', T, (-40, 40, -45, 20), 500, (0.12, 0.35), grass, seed=1, max_strands=600000, clump=0.4)
        P.grass_curves('Grass_mid', T, (-150, 170, 20, 260), 30, (0.12, 0.3), grass, seed=2, radius=0.006, max_strands=1000000, clump=0.4)
        protos = [P.bison_proto(f'BisonP{i}', 'stand' if i % 3 else 'graze', seed=i, coat=coat, horn=horn) for i in range(6)]
        pl = []
        for g in range(14):   # loose groups
            gx, gy = rnd.uniform(-90, 120), rnd.uniform(45, 235)
            for k in range(rnd.randint(10, 26)):
                x, y = gx + rnd.gauss(0, 12), gy + rnd.gauss(0, 9)
                pl.append((rnd.randrange(6), (x, y, T.z(x, y) - 0.05), rnd.uniform(0, 6.28), rnd.uniform(0.85, 1.1)))
        herd = P.herd(protos, pl, 'Bison')
        focus = herd[0]
    elif variant == 'horizon':
        protos = [P.bison_proto(f'BisonP{i}', 'graze' if i % 2 else 'stand', seed=10 + i, coat=coat, horn=horn) for i in range(5)]
        pl = []
        n = 15
        for k in range(n):
            x = -62 + k * 124 / (n - 1) + rnd.uniform(-2.5, 2.5)
            y = 160 + rnd.uniform(-4, 4)
            ridge = T.z(x, y)
            pl.append((k % 5, (x, y, ridge - 0.05), (0 if rnd.random() < 0.5 else math.pi) + rnd.uniform(-0.3, 0.3), rnd.uniform(0.9, 1.1)))
        herd = P.herd(protos, pl, 'Bison')
        focus = herd[7]
    elif variant == 'carts':
        P.grass_curves('Grass_near', T, (-40, 40, -40, 20), 500, (0.1, 0.35), grass, seed=1, max_strands=600000, clump=0.4)
        P.grass_curves('Grass_mid', T, (-150, 170, 20, 260), 30, (0.15, 0.35), grass, seed=2, radius=0.006, max_strands=1000000, clump=0.4)
        wood = P.mat_principled('CartWood', '#8a7457', rough=0.85, var=0.6, dark='#5a4a38', var_scale=8)
        load = P.mat_principled('Load', '#9a8a6e', rough=0.95)
        ox_coat = P.mat_bison('OxCoat', ox=True)
        cb = P.Batch()
        ox_protos = [P.bison_proto(f'OxP{i}', 'stand', seed=40 + i, ox=True, coat=ox_coat) for i in range(3)]
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
        P.herd(ox_protos, pl, 'Oxen')
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
    'B1': dict(cam=_c(TH, 10.0, -20.0, 4.0), tgt=_c(TH, 20.0, 160.0, 0.5), lens=70, fstop=11.0, focus_dist=150.0, variant='herd'),
    'B2': dict(cam=_c(TH, 0.0, -40.0, 1.6), tgt=_c(TH, 0.0, 160.0, 2.2), lens=85, fstop=11.0, focus_dist=200.0, variant='horizon', bg_clean=True),
    'B3': dict(cam=_c(TH, -40.0, -6.0, 2.2), tgt=_c(TH, 10.0, 75.0, 1.4), lens=75, fstop=11.0, focus_dist=95.0, variant='carts'),
}
MIST = (40.0, 1400.0)


def composite(scn, strength=-1):
    v = 'dusk' if 'Sky' in bpy.data.objects and bpy.data.lights['SunKey'].energy < 0.5 else 'day'
    col = '#6f7b92' if v == 'dusk' else '#cdb89a'
    busy = 'Bison' in bpy.data.collections and 'Sky' not in bpy.data.objects or 'Carts' in bpy.data.objects
    st = 0.35 if busy else 0.6
    lib.mist_compositor(scn, fog_color=srgb(col), gamma=0.9, strength=st if strength < 0 else strength, blur_fog=0.4, blur_px=140)
