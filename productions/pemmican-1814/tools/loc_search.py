"""Search the Library of Congress Prints & Photographs catalogue (public JSON API, no key) and list candidates.

  python3 -I tools/loc_search.py OUTDIR "red river cart" "buffalo skulls" ...

One plain request per query, 2 s apart (the API asks scripts to stay under its rate limits). Each result's JSON is
saved under OUTDIR; a compact list (title, date, id, image links) is printed. Rights are NOT decided here: each item
page's "Rights Advisory" has to be read (see loc_item.py) before an image goes into the film.
"""
import sys, os, json, time, subprocess, urllib.parse, re


def get(url, dst):
    r = subprocess.run(['curl', '-sS', '-m', '60', '-o', dst, '-w', '%{http_code}', url], capture_output=True, text=True)
    return r.stdout.strip()


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for q in sys.argv[2:]:
        slug = re.sub(r'\W+', '_', q)[:40]
        dst = os.path.join(out, f'search_{slug}.json')
        url = 'https://www.loc.gov/photos/?' + urllib.parse.urlencode({'q': q, 'fo': 'json', 'c': 25, 'fa': 'online-format:image'})
        d = None
        for attempt in (1, 2):                      # one retry: a transfer can be cut off midway
            code = get(url, dst)
            try:
                d = json.load(open(dst)) if code == '200' else None
            except ValueError:
                d = None
            if d is not None:
                break
            time.sleep(6)
        print(f'\n## {q}  (HTTP {code})')
        if d is None:
            print('   no usable answer')
            continue
        print('total', d.get('pagination', {}).get('total'))
        for r in d.get('results', []):
            imgs = [u.split('#')[0] for u in (r.get('image_url') or [])]
            big = next((u for u in imgs if re.search(r'[uv]\.jpg$|r\.jpg$', u)), imgs[-1] if imgs else '')
            print(f"- {r.get('title', '')[:84]} | {r.get('date')} | {r.get('id', '').replace('http://www.loc.gov/item/', '')} | {big.rsplit('/', 1)[-1]}")
        time.sleep(2)


if __name__ == '__main__':
    main()
