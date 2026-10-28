"""Prairie camp in late summer: drying racks, pounding, rendering fat, berries, hide lodges.

Reconstruction of the general process described for Plains pemmican making (thin-sliced meat
dried on racks, pounded on a hide with a stone maul, mixed with rendered fat, sometimes berries,
packed into rawhide). Not a depiction of a specific documented camp. No people are shown.
Variants: 'day' (golden hour, backlit) and 'dusk' (blue hour, racks empty, no fire).
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import lib, props as P
from lib import srgb
import scene_dock as SD

T = P.Terrain(amp=1.6, scale=0.012, seed=4, amp2=0.18, scale2=0.09, flat_r=26.0, flat_c=(0, 3))


def build(variant='day'):
    scn = lib.reset()
    dusk = variant == 'dusk'
    if dusk:
        lib.sky_world(scn, sun_elev_deg=-1.5, sun_rot_deg=0.0, strength=0.9, air=1.0, dust=1.5)
        lib.sun('SunKey', elev=1.0, azim=0, strength=0.5, color=(1.0, 0.55, 0.4), angle=2.0)
        lib.area_light('Sky', (0, -10, 12), (40, 0, 0), 30.0, 900.0, color=(0.55, 0.65, 0.95))
    else:
        lib.sky_world(scn, sun_elev_deg=7.0, sun_rot_deg=0.0, strength=0.55, air=1.3, dust=2.2)
        lib.sun('SunKey', elev=7.0, azim=0, strength=3.2, color=(1.0, 0.72, 0.46), angle=1.0)
        lib.area_light('Fill', (-4, -14, 6), (65, 0, -20), 12.0, 120.0, color=(0.6, 0.7, 0.92))

    ground = P.mat_ground('Ground', '#867650', '#5b5034', dry='#a59263', scale=0.15, bump=0.25)
    far_ground = P.mat_ground('FarGround', '#8a7c58', '#6a5e40', scale=0.02, emit='#c9b79a' if not dusk else '#6d7890',
                              emit_strength=0.12 if not dusk else 0.05, bump=0.0)
    grass = P.mat_strand('Grass', '#4d4628', '#cdb67c', transl=0.35)
    grass_far = P.mat_strand('GrassFar', '#5e5434', '#b9a372', transl=0.3)
    wood = P.mat_principled('PoleWood', '#7d6c58', rough=0.8, var=0.5, dark='#4e4236', var_scale=14, bump_scale=60, bump_strength=0.15)
    cover = P.mat_translucent_mix('LodgeCover', '#d9c7a2', '#e8a868', mix=0.28, rough=0.85, var_dark='#9c8b6c', var=0.5, scale=2.5, bump=0.08)
    meat = P.mat_translucent_mix('MeatStrip', '#3e1710', '#5e170a', mix=0.12, rough=0.5, var_dark='#1c0907', var=0.8, scale=30, bump=0.5)
    pounded = P.mat_principled('Pounded', '#6d4a32', rough=0.95, var=0.8, dark='#3a2419', var_scale=90, bump_scale=260, bump_strength=0.9)
    hide_side = P.mat_principled('HideFlesh', '#a88e66', rough=0.8, var=0.7, dark='#6e5a40', var_scale=4, bump_scale=30, bump_strength=0.25)
    stone_m = P.mat_principled('Stone', '#827d73', rough=0.7, var=0.6, dark='#4d4a44', var_scale=9, bump_scale=80, bump_strength=0.3)
    thong = SD.mat_thong()
    copper = P.mat_principled('Copper', '#b8774a', rough=0.38, metallic=1.0, var=0.5, dark='#4e3424', var_scale=7, bump_scale=30, bump_strength=0.05)
    iron = P.mat_principled('Iron', '#2f2c2a', rough=0.6, metallic=0.8)
    fat = P.mat_principled('HotFat', '#8a6526', rough=0.04, spec=0.9)
    berry = P.mat_principled('Berry', '#2c0c24', rough=0.45, var=0.6, dark='#0d050c', var_scale=300, bump_scale=900, bump_strength=0.35)
    bowlw = P.mat_principled('BowlWood', '#6e5034', rough=0.6, var=0.5, dark='#3e2b1b', var_scale=20)
    charcoal = P.mat_principled('Charred', '#1b1612', rough=0.9)
    ember = P.mat_principled('Ember', '#1a0d08', rough=0.9, emit='#ff4a10', emit_strength=3.0)
    flame = P.mat_flame()
    hide = SD.mat_rawhide(seed=11)

    # ---------- terrain
    T.mesh('Land_near', -30, 30, -20, 40, 150, 150, ground)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, -0.6))
    far = bpy.context.active_object; far.name = 'Land_far'; far.scale = (4000, 4000, 1)
    far.data.materials.append(far_ground)
    # gentle far rises so the horizon is not ruler-straight
    T2 = P.Terrain(amp=9.0, scale=0.004, seed=9, amp2=1.5, scale2=0.02)
    T2.mesh('Land_hills', -700, 700, 40, 900, 120, 80, far_ground)
    for v in bpy.data.objects['Land_hills'].data.vertices:
        v.co.z = v.co.z * min(1.0, (v.co.y - 40) / 120.0) - 0.4

    clear = [(-1.5, -2.0, 1.35), (2.6, -1.1, 0.9), (-2.7, -1.2, 0.7)]   # bare ground: hide, fire, bags

    def trample(x, y):
        for cx, cy, r in clear:
            d = math.hypot(x - cx, y - cy)
            if d < r:
                return 0.0
        d = math.hypot((x - 0.5) / 1.3, y - 1.5)
        return 0.15 + 0.85 * min(1.0, max(0.0, (d - 5.5) / 6.0))

    P.grass_curves('Grass_near', T, (-14, 14, -13, 16), 1300, (0.12, 0.42), grass, seed=1, lean=(0.08, 0.15),
                   lean_var=0.35, max_strands=650000, mask=trample, clump=0.3)
    P.grass_curves('Grass_mid', T, (-40, 40, 16, 60), 120, (0.3, 0.6), grass_far, seed=2, lean=(0.05, 0.1),
                   radius=0.003, max_strands=380000, clump=0.4)

    # ---------- lodges (background)
    for i, (x, y, r, h) in enumerate([(-7, 11, 2.5, 4.6), (2.5, 15, 2.7, 4.9), (9, 10, 2.3, 4.3), (-14, 18, 2.6, 4.7),
                                      (14, 21, 2.4, 4.5), (-24, 30, 2.6, 4.8), (26, 38, 2.5, 4.6), (-3, 34, 2.6, 4.8)]):
        parts = P.lodge(f'Lodge{i}', (x, y), r, h, cover, wood, seed=i + 1, terrain=T)
        P.join(parts[1:], f'LodgePoles{i}')

    # ---------- racks (foreground)
    racks = [((-3.2, 1.0), (0.6, 1.7), 1.6, 1.0), ((1.6, 3.6), (4.8, 3.1), 1.55, None), ((-1.4, 6.2), (2.2, 6.8), 1.6, 1.05)]
    strips_on = not dusk
    for i, (a, b, hgt, low) in enumerate(racks):
        objs, bars = P.rack(f'Rack{i}', (*a, 0), (*b, 0), hgt, wood, seed=i * 10, terrain=T, lower=low)
        P.join(objs, f'Rack{i}')
        if strips_on:
            for j, (pa, pb) in enumerate(bars):
                s = P.drape_bar(f'Strip{i}_{j}_', pa, pb, meat, seed=i * 7 + j, length=(0.5, 0.9) if j == 0 else (0.35, 0.6), bar_r=0.032)
    # ---------- pounding: hide, pounded meat, maul, finished bags
    hx, hy = -1.5, -2.0
    P.hide_flat('HideSpread', (hx, hy, 0), (1.9, 1.5), hide_side, seed=3, rot=0.3, terrain=T)
    z = T.z(hx, hy) + 0.012
    if not dusk:
        P.mound('Pounded', (hx + 0.1, hy + 0.05), 0.26, 0.07, pounded, seed=5, chunks=1400, terrain_z=z)
        P.maul('Maul', (hx + 0.55, hy - 0.25, z), 2.4, stone_m, wood, thong, seed=2)
        P.stone('Anvil', (0.16, 0.13, 0.07), (hx - 0.38, hy + 0.38, z + 0.04), stone_m, seed=6, rough=0.04)
        bwx, bwy = hx + 0.7, hy + 0.32
        P.bowl('Bowl', (bwx, bwy, z + 0.004), bowlw)
        P.berries('Berries', (bwx, bwy, z + 0.02), 0.105, 0.05, berry, n=230, seed=3)
        P.berries('Berries_spill', (bwx + 0.16, bwy - 0.1, z), 0.06, 0.0, berry, n=14, seed=4, dome=False)
    b1 = SD.make_bag('PBag1', size=(0.56, 0.36, 0.22), loc=(hx - 1.05, hy + 0.55, T.z(hx - 1.05, hy + 0.55)), rot_z=math.radians(30), seed=21, mat=hide, thong=thong)
    b2 = SD.make_bag('PBag2', size=(0.54, 0.35, 0.21), loc=(hx - 1.3, hy + 1.0, T.z(hx - 1.3, hy + 1.0)), rot_z=math.radians(12), seed=22, mat=hide, thong=thong)

    # ---------- rendering fat
    fx, fy = 2.6, -1.1
    fz = T.z(fx, fy)
    if not dusk:
        P.fire('Fire', (fx, fy, fz), charcoal, flame, ember, seed=4, scale=1.0)
        for k in range(3):
            a = k * 2.094 + 0.3
            P.stone(f'FireStone{k}', (0.1, 0.09, 0.09), (fx + 0.2 * math.cos(a), fy + 0.2 * math.sin(a), fz + 0.05), stone_m, seed=10 + k, rough=0.04)
        P.kettle('Kettle', (fx, fy, fz + 0.12), copper, liquid=fat, scale=1.25, bail_mat=iron)
    else:
        P.stone('FireStone0', (0.1, 0.09, 0.09), (fx + 0.2, fy, fz + 0.05), stone_m, seed=10, rough=0.04)
        bpy.ops.mesh.primitive_circle_add(vertices=24, radius=0.24, fill_type='NGON', location=(fx, fy, fz + 0.01))
        bpy.context.active_object.data.materials.append(charcoal)
    P.frame_hide('HideFrame', (6.2, 6.5), math.radians(-25), wood, cover, seed=8, terrain=T)

    for o in scn.objects:
        bg = o.name.startswith(('Land', 'Grass', 'Lodge'))
        o['layer'] = 'bg' if bg else 'fg'
    return scn, bpy.data.objects.get('HideSpread')


CAMS = {
    'R1': dict(cam=(-7.8, -10.5, 1.75), tgt=(0.4, 4.0, 1.35), lens=32, fstop=8.0, focus_dist=11.0),
    'R2': dict(cam=(-2.4, -0.75, 1.22), tgt=(-1.0, 1.35, 1.18), lens=70, fstop=2.8, focus_dist=2.3),
    'K1': dict(cam=(-0.75, -3.15, 0.95), tgt=(-1.42, -1.98, 0.08), lens=50, fstop=4.0, focus_dist=1.45),
    'K2': dict(cam=(1.85, -1.95, 0.58), tgt=(2.6, -1.1, 0.28), lens=50, fstop=2.8, focus_dist=1.15),
    'K3': dict(cam=(-0.52, -2.05, 0.36), tgt=(-0.8, -1.68, 0.06), lens=85, fstop=2.8, focus_dist=0.52),
    'R3': dict(cam=(9.5, -3.0, 1.5), tgt=(1.0, 5.5, 1.5), lens=35, fstop=8.0, focus_dist=9.0),
    'R3b': dict(cam=(-4.8, -4.0, 1.35), tgt=(0.0, 2.6, 1.45), lens=35, fstop=5.6, focus_dist=6.0, variant='dusk'),
}
MIST = (10.0, 700.0)


def composite(scn, strength=-1):
    dusk = 'Sky' in bpy.data.objects
    lib.mist_compositor(scn, fog_color=srgb('#cdbb9c' if not dusk else '#6f7b92'), gamma=0.9,
                        strength=0.55 if strength < 0 else strength, blur_fog=0.5, blur_px=160)
