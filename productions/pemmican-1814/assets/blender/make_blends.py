"""Save an editable .blend for each scene variant (generated hair/grass curves stripped to keep files small;
re-run the scene module to regenerate them). Cameras from CAMS are added as named camera objects.
  python3 make_blends.py
"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import lib

JOBS = [('scene_dock', 'default'), ('scene_dock', 'canoe'), ('scene_camp', 'day'), ('scene_camp', 'dusk'),
        ('scene_fort', 'winter'), ('scene_fort', 'summer'), ('scene_plain', 'plain'), ('scene_plain', 'herd'),
        ('scene_plain', 'horizon'), ('scene_plain', 'carts'), ('scene_desk', 'default'), ('scene_store', 'default')]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blend')
only = sys.argv[1:]
for mod_name, variant in JOBS:
    if only and f'{mod_name}:{variant}' not in only:
        continue
    mod = importlib.import_module(mod_name)
    scn, focus = mod.build(variant)
    for o in list(scn.objects):
        if o.type == 'CURVES':
            bpy.data.objects.remove(o, do_unlink=True)
    for name, C in mod.CAMS.items():
        v = C.get('variant', 'default')
        if v not in (variant, 'default') and not (variant in ('day', 'winter', 'plain') and v == 'default'):
            continue
        cam = lib.camera(name=f'CAM_{name}', lens=C['lens'], fstop=C.get('fstop'))
        cam.location = C['cam']
        lib.look_at(cam, C['tgt'])
    path = os.path.join(OUT, f"{mod_name.replace('scene_', '')}_{variant}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print('saved', path, round(os.path.getsize(path) / 1e6, 1), 'MB', flush=True)
