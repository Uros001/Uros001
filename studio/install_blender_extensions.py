"""Download and install the Blender extensions listed in studio/blender_extensions.json (extensions.blender.org, all GPL).

  python3 studio/install_blender_extensions.py        (Blender as the Python module `bpy`)

Each archive is checked against the SHA-256 published by extensions.blender.org before it is installed. Scripts that
use an extension enable it first, e.g. addon_utils.enable('bl_ext.user_default.sun_position', default_set=True).
"""
import os, json, hashlib, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    import bpy
    exts = json.load(open(os.path.join(HERE, 'blender_extensions.json')))
    tmp = tempfile.mkdtemp(prefix='blext_')
    for name, m in exts.items():
        z = os.path.join(tmp, f"{name}-{m['version']}.zip")
        subprocess.run(['curl', '-sS', '-L', '-m', '300', '-o', z, m['url']], check=True)
        h = hashlib.sha256(open(z, 'rb').read()).hexdigest()
        want = (m.get('hash') or '').split(':')[-1]
        if want and h != want:
            print(name, 'HASH MISMATCH, not installed')
            continue
        bpy.ops.extensions.package_install_files(filepath=z, repo='user_default', enable_on_install=True)
        print(name, m['version'], 'installed')
    bpy.ops.wm.save_userpref()


if __name__ == '__main__':
    main()
