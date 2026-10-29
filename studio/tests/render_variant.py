"""Render a film time range with one clip's shot replaced (test only; the film's EDL file is not changed).
  python3 render_variant.py ANCHOR T0 T1 OUT.mp4 'python expr for the new shot (names: shots, edl, os, core)'
"""
import sys, os, subprocess
sys.path.insert(0, '/home/user/Uros001/productions/pemmican-1814/tools')
from film import core, edl, shots
anchor, t0, t1, out, expr = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5]
i = next(k for k, c in enumerate(edl.CLIPS) if c[0] == anchor)
old = edl.CLIPS[i][1]
new = eval(expr)
new.credit = getattr(old, 'credit', None)
edl.CLIPS[i] = (anchor, new, edl.CLIPS[i][2])
from film.render import Film
f = Film()
mix = os.path.join(core.ROOT, 'audio/mix/pemmican_mix_master.wav')
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '30',
       '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', mix, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '17',
       '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-shortest', out]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(int(round(t0 * 30)), int(round(t1 * 30))):
    p.stdin.write(f.frame(n).tobytes())
p.stdin.close(); p.wait()
print('written', out)
