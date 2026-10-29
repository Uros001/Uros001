"""Inside a log storehouse at a provisioning post: stacked rawhide pemmican bags, kegs of grease, bales.

Generic reconstruction of a depot store (no specific post). Daylight enters through the doorway.
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import lib, props as P
from lib import srgb
import scene_dock as SD


def keg(name, loc, mat, hoop, r=0.2, h=0.45):
    prof = [(0, 0), (r * 0.85, 0), (r * 0.86, 0.02), (r, h * 0.5), (r * 0.86, h - 0.02), (r * 0.85, h), (0, h)]
    o = P.lathe(name, prof, mat, segs=32)
    o.location = loc
    for k, z in enumerate((0.06, h * 0.32, h * 0.68, h - 0.06)):
        rr = r * (0.88 + 0.12 * math.sin(math.pi * z / h)) + 0.004
        bpy.ops.mesh.primitive_torus_add(major_radius=rr, minor_radius=0.006, location=(loc[0], loc[1], loc[2] + z))
        bpy.context.active_object.data.materials.append(hoop)
    return o


def build(variant='default'):
    scn = lib.reset()
    lib.sky_world(scn, sun_elev_deg=22.0, sun_rot_deg=80.0, strength=0.5)
    lib.sun('SunKey', elev=22.0, azim=-80, strength=5.0, color=(1.0, 0.84, 0.64), angle=0.6)
    logs = P.mat_principled('Logs', '#6d5c4a', rough=0.9, var=0.7, dark='#33291f', var_scale=3, bump_scale=30, bump_strength=0.45)
    floor = P.mat_principled('Floor', '#5d4b39', rough=0.85, var=0.6, dark='#2e251c', var_scale=5, bump_scale=60, bump_strength=0.25)
    keg_m = P.mat_principled('KegWood', '#7b5f40', rough=0.7, var=0.6, dark='#3c2c1d', var_scale=20)
    hoop = P.mat_principled('Hoop', '#3a3a38', rough=0.5, metallic=0.7)
    canvas = SD.mat_simple('Canvas', '#6d6556', 0.9)
    rope = SD.mat_simple('Rope', '#5e4a33', 0.8)
    hide = SD.mat_rawhide('Rawhide1', base='#8a6d47', dark='#3f2e1d', seed=3)
    hide2 = SD.mat_rawhide('Rawhide2', base='#7a5a38', dark='#3a281a', seed=4)
    hmat = lib.mat_hair('BisonHair', melanin=0.82, redness=0.55, rough=0.45)
    thong = SD.mat_thong()

    W, D, H = 7.0, 5.0, 2.7
    b = P.Batch()
    HH = H + 0.35
    P.log_wall(b, (-W / 2, D / 2), (W / 2, D / 2), 0, HH, r=0.15, seed=1)
    P.log_wall(b, (-W / 2, -D / 2), (W / 2, -D / 2), 0, HH, r=0.15, seed=6)
    P.log_wall(b, (-W / 2, -D / 2), (-W / 2, D / 2), 0.15, HH, r=0.15, seed=2)
    # right wall with a doorway (two wall pieces + lintel logs)
    P.log_wall(b, (W / 2, -D / 2), (W / 2, -0.6), 0.15, HH, r=0.15, seed=3, overhang=0.0)
    P.log_wall(b, (W / 2, 0.8), (W / 2, D / 2), 0.15, HH, r=0.15, seed=4, overhang=0.0)
    P.log_wall(b, (W / 2, -0.6), (W / 2, 0.8), 2.0, HH - 2.0, r=0.15, seed=5, overhang=0.0)
    # roof: poles and planks
    top = 0.15 + int(H / (2 * 0.15 * 0.92)) * 2 * 0.15 * 0.92
    for i in range(12):
        x = -W / 2 + i * W / 11
        b.tube([(x, -D / 2 - 0.3, top - 0.05), (x, D / 2 + 0.3, top - 0.05)], 0.09, segs=8)
    b.box((0, 0, top + 0.08), (W + 0.8, D + 0.8, 0.12))
    b.build('Walls', [logs], smooth=True)
    fb = P.Batch()
    for i in range(16):
        fb.box((-W / 2 + (i + 0.5) * W / 16, 0, 0.02), (W / 16 - 0.01, D, 0.04))
    fb.build('Floor', [floor], smooth=False)
    # exterior ground plane for the doorway view
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(W / 2 + 30, 0, -0.02))
    g = bpy.context.active_object; g.name = 'Outside'; g.scale = (60, 60, 1)
    g.data.materials.append(P.mat_ground('OutGround', '#9c8a62', '#6e6247', scale=0.2, bump=0.1))

    rnd = random.Random(7)
    n = 0
    bags = []
    # stacks along the back wall and left wall
    rows = [((-2.9, 1.9), 0.0, 9), ((-3.0, -1.6), math.pi / 2, 5)]
    for (x0, y0), rot, count in rows:
        for c in range(count):
            for lvl in range(rnd.randint(3, 5)):
                if rot == 0.0:
                    x, y = x0 + c * 0.62 + rnd.uniform(-0.04, 0.04), y0 + rnd.uniform(-0.05, 0.05)
                else:
                    x, y = x0 + rnd.uniform(-0.05, 0.05), y0 + c * 0.62 + rnd.uniform(-0.04, 0.04)
                bg = SD.make_bag(f'SBag{n}', size=(0.56, 0.36, 0.22), loc=(x, y, 0.04 + lvl * 0.22),
                                 rot_z=rot + math.radians(rnd.uniform(-6, 6)), seed=100 + n, mat=hide if n % 3 else hide2, thong=thong)
                bags.append(bg)
                n += 1
    bpy.context.view_layer.update()
    for i, bg in enumerate(bags):
        lib.add_fur_curves(bg, hmat, density=260000.0, length=0.016, radius=0.0005, mask_scale=4.0,
                           mask_threshold=0.42, soft=0.12, seed=200 + i, curl=0.45, frizz=0.6, max_strands=30000)
    for k in range(5):
        keg(f'Keg{k}', (-0.4 + k * 0.48, -1.9, 0.04), keg_m, hoop)
    for k in range(3):
        SD.make_bale(f'Bale{k}', (0.7, 0.5, 0.35), (1.6 + k * 0.1, 1.6 - k * 0.55, 0.22), (0, 0, rnd.uniform(-0.2, 0.2)), canvas, rope)
    # a lantern-free interior: daylight bounced off the sunlit floor and door frame, facing into the room
    # (rotation (0, 90, 0) emits toward -x; the first version faced out of the door and lit nothing inside)
    lib.area_light('DoorBounce', (W / 2 - 0.3, 0.1, 1.1), (0, 90, 0), 1.4, 260.0, color=(1.0, 0.88, 0.72), size_y=2.0)
    for o in scn.objects:
        o['layer'] = 'bg' if o.name in ('Walls', 'Floor', 'Outside') else 'fg'
    return scn, bpy.data.objects.get('SBag4')


CAMS = {
    'S1': dict(cam=(2.6, -1.9, 1.35), tgt=(-1.2, 1.2, 0.65), lens=24, fstop=5.6, focus_dist=4.5),
    'S2': dict(cam=(-1.2, 0.2, 0.75), tgt=(-1.75, 1.9, 0.6), lens=50, fstop=2.8, focus_dist=1.75),
}
MIST = (1.0, 20.0)


def composite(scn, strength=-1):
    lib.mist_compositor(scn, fog_color=srgb('#5b5246'), gamma=1.0, strength=0.12 if strength < 0 else strength, blur_fog=0.3, blur_px=80)
