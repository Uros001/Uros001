"""Fetch the shared CC0 asset library used for realistic Blender scenes (all CC0 / public domain dedication).

  python3 -I studio/fetch_assets.py            (skips files that are already there)

Sources: Poly Haven (polyhaven.com, CC0: HDRI skies, PBR textures, scanned models) and ambientCG (ambientcg.com, CC0:
PBR materials). Files go to studio/library/<kind>/<id>/ (not kept in git; this script and LIBRARY.json are).
One plain request at a time. Licence of every item: CC0 1.0 (checked on each site's licence page).
"""
import os, json, time, zipfile, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(ROOT, 'library')

# Skies (pure sky HDRIs: no buildings or modern objects), 4k .hdr
HDRIS = ['kloofendal_48d_partly_cloudy_puresky', 'kloppenheim_06_puresky', 'belfast_sunset_puresky',
         'qwantani_dusk_2_puresky', 'kloofendal_misty_morning_puresky', 'overcast_soil_puresky', 'snow_field_puresky',
         'autumn_field_puresky', 'qwantani_sunrise_puresky', 'kloofendal_overcast_puresky']
# Ground, wood, bark, hide, snow (2k JPG maps)
TEXTURES = ['brown_mud_leaves_01', 'forrest_ground_01', 'brown_mud_dry', 'forest_leaves_02', 'rocks_ground_02',
            'ganges_river_pebbles', 'weathered_brown_planks', 'weathered_planks', 'rough_wood', 'wood_planks_grey',
            'bark_brown_02', 'bark_willow', 'brown_leather', 'fabric_leather_02', 'snow_02', 'aerial_grass_rock']
# Scanned / modelled props and ground cover (glTF, 2k textures)
MODELS = ['grass_medium_01', 'grass_medium_02', 'grass_bermuda_01', 'dry_branches_medium_01', 'dead_tree_trunk_02',
          'boulder_01', 'rock_moss_set_01', 'shrub_01', 'wine_barrel_01', 'wooden_crate_01', 'modular_wooden_pier',
          'tree_small_02']
# ambientCG materials (2K-JPG zips)
AMBIENTCG = ['Leather030', 'Leather037', 'Rope001', 'Bark012']


def get(url, dst):
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return 'have'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    for attempt in (1, 2, 3):
        r = subprocess.run(['curl', '-sS', '-L', '-m', '600', '-o', dst + '.part', '-w', '%{http_code}', url],
                           capture_output=True, text=True)
        if r.stdout.strip() == '200':
            os.replace(dst + '.part', dst)
            return 'ok'
        time.sleep(4 * attempt)
    if os.path.exists(dst + '.part'):
        os.remove(dst + '.part')
    return 'FAILED ' + r.stdout.strip()


def ph_files(aid):
    r = subprocess.run(['curl', '-sS', '-m', '60', f'https://api.polyhaven.com/files/{aid}'], capture_output=True, text=True)
    return json.loads(r.stdout)


def main():
    rec = {'polyhaven_hdri': {}, 'polyhaven_texture': {}, 'polyhaven_model': {}, 'ambientcg': {}}
    for aid in HDRIS:
        u = ph_files(aid)['hdri']['4k']['hdr']['url']
        st = get(u, os.path.join(LIB, 'hdri', f'{aid}_4k.hdr'))
        rec['polyhaven_hdri'][aid] = dict(url=u, page=f'https://polyhaven.com/a/{aid}', licence='CC0')
        print('hdri', aid, st)
    for aid in TEXTURES:
        f = ph_files(aid)
        maps = {}
        for key in ('Diffuse', 'nor_gl', 'Rough', 'AO', 'Displacement', 'arm'):
            if key in f and '2k' in f[key]:
                fmt = 'jpg' if 'jpg' in f[key]['2k'] else next(iter(f[key]['2k']))
                u = f[key]['2k'][fmt]['url']
                maps[key] = u
                get(u, os.path.join(LIB, 'textures', aid, os.path.basename(u)))
        rec['polyhaven_texture'][aid] = dict(maps=maps, page=f'https://polyhaven.com/a/{aid}', licence='CC0')
        print('texture', aid, len(maps), 'maps')
    for aid in MODELS:
        g = ph_files(aid)['gltf']['2k']['gltf']
        get(g['url'], os.path.join(LIB, 'models', aid, os.path.basename(g['url'])))
        for rel, inc in g.get('include', {}).items():
            get(inc['url'], os.path.join(LIB, 'models', aid, rel))
        rec['polyhaven_model'][aid] = dict(url=g['url'], page=f'https://polyhaven.com/a/{aid}', licence='CC0')
        print('model', aid, 1 + len(g.get('include', {})), 'files')
    for aid in AMBIENTCG:
        u = f'https://ambientcg.com/get?file={aid}_2K-JPG.zip'
        z = os.path.join(LIB, 'ambientcg', f'{aid}_2K-JPG.zip')
        st = get(u, z)
        d = os.path.join(LIB, 'ambientcg', aid)
        if st != 'FAILED' and not os.path.isdir(d):
            zipfile.ZipFile(z).extractall(d)
            os.remove(z)
            open(z, 'w').close()                     # marker so the next run skips the download
        rec['ambientcg'][aid] = dict(url=u, page=f'https://ambientcg.com/view?id={aid}', licence='CC0')
        print('ambientcg', aid, st)
    json.dump(rec, open(os.path.join(ROOT, 'LIBRARY.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
