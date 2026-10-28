"""Render a list of plate jobs serially (skips jobs whose outputs exist). Usage: python3 render_queue.py jobs.txt
jobs.txt lines: <scene_module> <cam> [extra args...]"""
import sys, os, subprocess, time
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../renders/plates')
for line in open(sys.argv[1]):
    line = line.split('#')[0].strip()
    if not line:
        continue
    parts = line.split()
    mod, cam, extra = parts[0], parts[1], parts[2:]
    force = '--force' in extra
    extra = [e for e in extra if e != '--force']
    base = os.path.join(OUT, f"{mod.replace('scene_', '')}_{cam}")
    if not force and os.path.exists(base + '_meta.json') and os.path.exists(base + '_bg.png'):
        print('skip', base, flush=True)
        continue
    t = time.time()
    with open(base + '.log', 'w') as lf:
        r = subprocess.run([sys.executable, 'plates.py', mod, cam, OUT] + extra, stdout=lf, stderr=subprocess.STDOUT,
                           cwd=os.path.dirname(os.path.abspath(__file__)))
    print(f'{mod} {cam} rc={r.returncode} {time.time() - t:.0f}s', flush=True)
