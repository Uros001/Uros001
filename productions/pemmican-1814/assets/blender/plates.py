"""Render 2.5D plates for a scene camera: background + foreground layers.

  python3 plates.py <scene_module> <cam_name> <outdir> [--res 2304x1296] [--samples 28] [--only bg|fg]

* BG: full scene, objects tagged layer='fg' are invisible to camera rays (they still cast shadows
  and appear in reflections), scene fog compositing applied.
* FG: transparent film, only 'fg' objects visible to the camera; 'bg' objects still light/shadow
  (with CAMS[cam]['fg_holdout'] they are holdouts instead, so they occlude fg objects behind them).
Objects are tagged with obj['layer'] = 'fg' | 'bg' (default 'bg'); cameras may override with a
list of name prefixes in CAMS[cam]['fg'].
Outputs <outdir>/<scene>_<cam>_bg.png, _fg.png and _meta.json (camera, focal, anchor).
"""
import sys, os, json, argparse, importlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import lib


def is_fg(o, prefixes):
    if prefixes is not None:
        return any(o.name.startswith(p) for p in prefixes)
    return o.get('layer', 'bg') == 'fg'


def project_point(scn, cam, p):
    from bpy_extras.object_utils import world_to_camera_view
    co = world_to_camera_view(scn, cam, Vector(p))
    return [co.x, 1 - co.y, co.z]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('module'); ap.add_argument('cam'); ap.add_argument('outdir')
    ap.add_argument('--res', default='2304x1296'); ap.add_argument('--samples', type=int, default=28)
    ap.add_argument('--only', default='')
    ap.add_argument('--full', action='store_true', help='single combined look-dev render')
    ap.add_argument('--variant', default=None)
    a = ap.parse_args()
    mod = importlib.import_module(a.module)
    C = mod.CAMS[a.cam]
    scn, focus = mod.build(a.variant or C.get('variant', 'default'))
    res = tuple(int(v) for v in a.res.split('x'))
    lib.render_settings(scn, res=res, samples=C.get('samples', a.samples), frames=(1, 1), mist=getattr(mod, 'MIST', None))
    cam = lib.camera(lens=C['lens'], fstop=C.get('fstop'), focus_obj=bpy.data.objects.get(C['focus']) if C.get('focus') else focus)
    if C.get('focus_dist'):
        cam.data.dof.focus_object = None
        cam.data.dof.focus_distance = C['focus_dist']
    cam.location = C['cam']
    lib.look_at(cam, C['tgt'])
    if C.get('roll'):
        cam.rotation_euler.rotate_axis('Z', C['roll'])
    bpy.context.view_layer.update()
    os.makedirs(a.outdir, exist_ok=True)
    base = os.path.join(a.outdir, f"{a.module.replace('scene_', '')}_{a.cam}")
    prefixes = C.get('fg')
    objs = [o for o in scn.objects if o.type in ('MESH', 'CURVES', 'CURVE')]
    meta = dict(module=a.module, cam=a.cam, res=res, lens=C['lens'], location=list(C['cam']), target=list(C['tgt']),
                anchor=project_point(scn, cam, C.get('anchor', C['tgt'])))
    pts = dict(getattr(mod, 'POINTS', {}) or {})
    pts.update(C.get('points', {}))
    meta['points'] = {k: project_point(scn, cam, v) for k, v in pts.items()}
    if a.full:
        if hasattr(mod, 'composite'):
            mod.composite(scn, C.get('fog', -1))
        scn.render.filepath = base + '_full.png'
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print('FULL DONE', base, round(time.time() - t, 1))
        return
    if a.only in ('', 'bg'):
        t = time.time()
        for o in objs:
            o.visible_camera = not is_fg(o, prefixes)
            if C.get('bg_clean') and is_fg(o, prefixes):
                o.visible_shadow = False
        scn.render.film_transparent = False
        if hasattr(mod, 'composite'):
            mod.composite(scn, C.get('fog', -1))
        scn.render.filepath = base + '_bg.png'
        bpy.ops.render.render(write_still=True)
        meta['bg_seconds'] = round(time.time() - t, 1)
    if a.only in ('', 'fg') and not C.get('no_fg'):
        t = time.time()
        for o in objs:
            o.visible_camera = is_fg(o, prefixes)
            o.visible_shadow = True
            if C.get('fg_holdout') and not is_fg(o, prefixes):
                # bg objects cut the fg layer where they are in front (e.g. ground over the buried part of a drift)
                o.visible_camera = True
                o.is_holdout = True
        scn.render.film_transparent = True
        scn.render.use_compositing = False
        scn.render.image_settings.color_mode = 'RGBA'
        scn.render.filepath = base + '_fg.png'
        bpy.ops.render.render(write_still=True)
        meta['fg_seconds'] = round(time.time() - t, 1)
    json.dump(meta, open(base + '_meta.json', 'w'), indent=1)
    print('PLATES DONE', base, meta.get('bg_seconds'), meta.get('fg_seconds'))


if __name__ == '__main__':
    main()
