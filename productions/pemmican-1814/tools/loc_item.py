"""Fetch Library of Congress item records (public JSON, no key) and print what matters before using an image.

  python3 -I tools/loc_item.py OUTDIR <item id> [<item id> ...]        e.g. 2022651022 90710851

Saves OUTDIR/item_<id>.json (provenance) and prints title, date, creator, rights advisory, the reproduction number and
the available image files with sizes. One plain request per item, 2 s apart. Download is a separate, explicit step
(loc_get.py) so that rights are read first.
"""
import sys, os, json, time, subprocess


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for iid in sys.argv[2:]:
        dst = os.path.join(out, f'item_{iid}.json')
        d = None
        for attempt in (1, 2):
            r = subprocess.run(['curl', '-sS', '-m', '60', '-o', dst, '-w', '%{http_code}',
                                f'https://www.loc.gov/item/{iid}/?fo=json'], capture_output=True, text=True)
            try:
                d = json.load(open(dst)) if r.stdout.strip() == '200' else None
            except ValueError:
                d = None
            if d is not None:
                break
            time.sleep(6)
        print(f'\n## {iid}')
        if d is None:
            print('   no usable answer')
            continue
        it = d['item']
        print('title      :', it.get('title', '')[:100])
        print('date       :', it.get('date'), '|', it.get('created_published'))
        print('creator    :', it.get('contributor_names'))
        print('rights     :', it.get('rights_advisory') or it.get('rights_information'))
        print('repro no.  :', str(it.get('reproduction_number', ''))[:140].replace('\n', ' | '))
        print('call no.   :', it.get('call_number'))
        print('notes      :', str(it.get('notes', ''))[:240])
        files = []
        for res in d.get('resources', []):
            for group in res.get('files', []):
                for f in group:
                    if f.get('mimetype', '').startswith('image'):
                        files.append(f)
        for f in files[:8]:
            print('  ', f.get('mimetype'), f.get('size'), f.get('width'), 'x', f.get('height'), f.get('url'))
        time.sleep(2)


if __name__ == '__main__':
    main()
