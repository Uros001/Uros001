"""Look-dev helper: render any scene module's build() from an arbitrary camera."""
import sys, os, importlib, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, lib
ap = argparse.ArgumentParser()
ap.add_argument('module'); ap.add_argument('out'); ap.add_argument('--cam', required=True)
ap.add_argument('--tgt', required=True); ap.add_argument('--lens', type=float, default=50)
ap.add_argument('--fstop', type=float, default=0); ap.add_argument('--res', default='960x540')
ap.add_argument('--samples', type=int, default=16); ap.add_argument('--shot', default='open')
ap.add_argument('--fog', type=float, default=-1)
a = ap.parse_args()
mod = importlib.import_module(a.module)
scn, hero = mod.build(a.shot)
lib.render_settings(scn, res=tuple(int(v) for v in a.res.split('x')), samples=a.samples, frames=(1, 1), mist=getattr(mod, 'MIST', (4.0, 260.0)))
if hasattr(mod, 'composite'):
    mod.composite(scn, a.fog)
cam = lib.camera(lens=a.lens, fstop=a.fstop or None, focus_obj=hero if a.fstop else None)
cam.location = [float(v) for v in a.cam.split(',')]
lib.look_at(cam, [float(v) for v in a.tgt.split(',')])
scn.render.filepath = a.out
bpy.ops.render.render(write_still=True)
