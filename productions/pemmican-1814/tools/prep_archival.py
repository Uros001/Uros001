"""Make the working copies of the archival images used in the film, with their credits.

  python3 tools/prep_archival.py            (needs assets/archival/si*/ from tools/fetch_archival.sh)

Sources: Smithsonian Institution Open Access, all items marked CC0 (public domain dedication). Originals are
fetched from the public S3 bucket `smithsonian-open-access` (media/<unit>/<id>.jpg|.tif) and are not kept in git;
the working copies (long side <= 4500 px) and assets/archival/ARCHIVAL_SOURCES.json are.
"""
import os, json
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'assets/archival')
MAX = 4500

# key: (source file under assets/archival, title for the on-screen credit, maker, year, collection)
SAAM = 'Smithsonian American Art Museum'
SIA = 'Smithsonian Institution Archives'
SELECT = {
    'catlin_yellowstone_chase': ('si_tif/SAAM-1985.66.415_1.tif', 'Buffalo Chase, Mouth of the Yellowstone', 'George Catlin', '1832–33', SAAM),
    'catlin_sioux_camp': ('si_tif/SAAM-1985.66.377_1.tif', 'Sioux Encamped on the Upper Missouri, Dressing Buffalo Meat and Robes', 'George Catlin', '1832', SAAM),
    'catlin_comanche_village': ('si_tif/SAAM-1985.66.346_1.tif', 'Comanche Village, Women Dressing Robes and Drying Meat', 'George Catlin', '1834–35', SAAM),
    'catlin_cree_woman': ('si/SAAM-1985.66.178_1.jpg', 'Tow-ée-ka-wet, a Cree Woman', 'George Catlin', '1832', SAAM),
    'catlin_assiniboine_woman': ('si/SAAM-1985.66.181_1.jpg', 'Assiniboine Woman and Child', 'George Catlin', '1832', SAAM),
    'catlin_canoe_race': ('si_tif/SAAM-1985.66.434_1.tif', 'Canoe Race near Sault Ste. Marie', 'George Catlin', '1836–37', SAAM),
    'catlin_fort_union': ('si_tif/SAAM-1985.66.388_1.tif', 'Fort Union, Mouth of the Yellowstone River', 'George Catlin', '1832', SAAM),
    'catlin_herds_crossing': ('si/SAAM-1985.66.400_1.jpg', 'Buffalo Herds Crossing the Upper Missouri', 'George Catlin', '1832', SAAM),
    'catlin_winter_chase': ('si/SAAM-1985.66.416_1.jpg', 'Buffalo Chase in Winter, Indians on Snowshoes', 'George Catlin', '1832–33', SAAM),
    'catlin_bulls_running_season': ('si/SAAM-1985.66.424_1.jpg', 'Buffalo Bulls Fighting in Running Season, Upper Missouri', 'George Catlin', '1837–39', SAAM),
    'muybridge_gallop_sheet': ('si_tif/SIA-2004-44793.tif', 'Buffalo gallop (Animal Locomotion)', 'Eadweard Muybridge', '1884–86', 'National Museum of American History'),
    'hornaday_shop': ('si/SIA-MNH-3687-000004.jpg', 'William T. Hornaday in the model and taxidermy shop', 'Photographer unknown', '1884–87', SIA),
    'hornaday_bison_group': ('si/SIA-SIA_000095_B43_F01_005.jpg', 'Group of bison collected and mounted by Hornaday, U.S. National Museum', 'Photographer unknown', '1887', SIA),
    'zoo_cow_and_calf': ('si/SIA-SIA_000095_B46_F13_014.jpg', 'Bison cow "May" and calf, National Zoological Park', 'Photographer unknown', 'c. 1898', SIA),
    'zoo_bison_2014': ('si/NZP-20141105-008CPM.jpg', 'American bison, Smithsonian\'s National Zoo', 'Smithsonian\'s National Zoo', '2014', 'Smithsonian'),
}


# Library of Congress items (rights advisory in each item record: "No known restrictions on publication").
# crop = (x0, y0, x1, y1) as fractions of the master scan, to the picture only (no masthead, text columns or caption card);
# 'stereo-left' takes the left photograph of a stereograph.
LOC = {
    'upton_red_river_carts': dict(src='loc/LC-DIG-stereo-1s43921u.tif', crop='stereo-left', item='2022651022',
                                  title='Red River carts, Minnesota', maker='B. F. Upton', date='between 1867 and 1875',
                                  collection='Library of Congress', repro='LC-DIG-stereo-1s43921'),
    'tavernier_slaughtered_for_the_hide': dict(src='loc/12612u.tif', crop=(0.095, 0.268, 0.935, 0.944), item='2019630603',
                                               title='Slaughtered for the hide',
                                               maker='Frenzeny & Tavernier', date='Harper\'s Weekly, 12 December 1874', collection='Library of Congress',
                                               repro='LC-DIG-ds-12612'),
    'tavernier_curing_hides_and_bones': dict(src='loc/3c00250u.tif', crop=(0.066, 0.097, 0.968, 0.820), item='90710851',
                                             title='Curing hides and bones',
                                             maker='Frenzeny & Tavernier', date='Harper\'s Weekly, 4 April 1874', collection='Library of Congress',
                                             repro='LC-USZ62-100250'),
    'nyzp_nucleus_of_the_buffalo_herd': dict(src='loc/16139u.tif', crop=(0.046, 0.036, 0.968, 0.805), item='2023632555',
                                             title='Nucleus of the buffalo herd', maker='Photographer unknown',
                                             date='between 1900 and 1920', collection='Library of Congress',
                                             repro='LC-DIG-ds-16139'),
}


def _stereo_left(im):
    """Left photograph of a stereograph: the print is low-saturation sepia on a saturated yellow mount."""
    import numpy as np
    hsv = cv2.cvtColor(cv2.resize(im, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2HSV)
    photo = (hsv[:, :, 1] < 90).astype(np.uint8)
    photo[:, photo.shape[1] // 2:] = 0                              # left half only
    photo = cv2.morphologyEx(photo, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(photo)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = st[i, :4] * 4
    m = int(0.022 * w)                                               # inset: the print's soft edge and mount
    return im[y + m:y + h - m, x + m:x + w - m]


def muybridge(src, dst):
    """Cut Muybridge's "Buffalo gallop" sheet (6 rows x 4 lateral views) into frames and steady them on the
    animal. Rows 3-4 (cells 8-15) share one camera bank and background and make one stride; the other rows are
    from other set-ups or faded, so they are not used."""
    import numpy as np
    im = cv2.imread(src)
    rows = [(424, 600), (618, 800), (812, 994), (1008, 1190), (1206, 1386), (1402, 1586)]   # measured on the sheet
    x0, x1 = 761, 2380
    w = (x1 - x0) / 4
    cells = [im[a:b, int(x0 + k * w) + 2:int(x0 + (k + 1) * w) - 2] for a, b in rows for k in range(4)][8:16]

    def hp(c):
        L = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(np.float32)
        return L - cv2.GaussianBlur(L, (0, 0), 12)
    guess = [230, 254, 280, 297, 195, 215, 257, 277]       # rough torso centres, refined by template matching
    tpl = hp(cells[1])[50:125, 254 - 55:254 + 55]
    os.makedirs(dst, exist_ok=True)
    for i, (c, g) in enumerate(zip(cells, guess)):
        H = hp(c)
        lo, hi = max(0, g - 95), min(H.shape[1], g + 95)
        _, _, _, loc = cv2.minMaxLoc(cv2.matchTemplate(H[30:150, lo:hi], tpl, cv2.TM_CCOEFF_NORMED))
        cx = lo + loc[0] + 55
        xa = max(0, min(c.shape[1] - 300, int(round(cx - 140))))
        ya = c.shape[0] - 158
        cv2.imwrite(os.path.join(dst, f'frame_{i:02d}.png'), c[ya:ya + 150, xa:xa + 300])


def main():
    mf = os.path.join(A, 'si/manifest.json')                  # catalogue records saved when the files were found
    man = json.load(open(mf)) if os.path.exists(mf) else {}
    prev_f = os.path.join(A, 'ARCHIVAL_SOURCES.json')
    prev = json.load(open(prev_f)) if os.path.exists(prev_f) else {}
    os.makedirs(os.path.join(A, 'work'), exist_ok=True)
    out = {}
    for key, (src, title, who, year, coll) in SELECT.items():
        im = cv2.imread(os.path.join(A, src), cv2.IMREAD_COLOR)
        h, w = im.shape[:2]
        s = min(1.0, MAX / max(h, w))
        if s < 1.0:
            im = cv2.resize(im, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        dst = os.path.join(A, 'work', key + '.jpg')
        cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        ids = os.path.basename(src).rsplit('.', 1)[0]
        m = man.get(ids) or {k[8:] if k.startswith('catalog_') else k: v for k, v in prev.get(key, {}).items()}
        out[key] = dict(file=f'assets/archival/work/{key}.jpg', size=[im.shape[1], im.shape[0]], title=title, maker=who,
                        date=year, collection=coll, smithsonian_id=ids, record_id=m.get('record_id', ''),
                        record_link=m.get('record_link', ''), guid=m.get('guid', ''), rights=m.get('usage', 'CC0'),
                        catalog_title=m.get('title', ''), catalog_date=m.get('date', ''), catalog_artist=m.get('artist', ''))
        print(key, im.shape[1], 'x', im.shape[0], m.get('usage'))
    for key, m in LOC.items():
        im = cv2.imread(os.path.join(A, m['src']), cv2.IMREAD_COLOR)
        if m['crop'] == 'stereo-left':
            im = _stereo_left(im)
        else:
            h, w = im.shape[:2]
            x0, y0, x1, y1 = m['crop']
            im = im[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
        h, w = im.shape[:2]
        s = min(1.0, MAX / max(h, w))
        if s < 1.0:
            im = cv2.resize(im, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(A, 'work', key + '.jpg'), im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        rec = json.load(open(os.path.join(A, 'loc', f"item_{m['item']}.json")))['item']
        out[key] = dict(file=f'assets/archival/work/{key}.jpg', size=[im.shape[1], im.shape[0]], title=m['title'],
                        maker=m['maker'], date=m['date'], collection=m['collection'], smithsonian_id=m['repro'],
                        record_id=m['item'], record_link=f"https://www.loc.gov/item/{m['item']}/", guid='',
                        rights='LOC rights advisory: ' + str(rec.get('rights_advisory') or rec.get('rights_information')),
                        catalog_title=rec.get('title', ''), catalog_date=str(rec.get('created_published', [''])[0]),
                        catalog_artist='; '.join(rec.get('contributor_names') or []))
        print(key, im.shape[1], 'x', im.shape[0], rec.get('rights_advisory'))
    out.update({k: v for k, v in prev.items() if k.startswith('doc_')})        # document pages: written by tools/doc_marks.py
    json.dump(out, open(os.path.join(A, 'ARCHIVAL_SOURCES.json'), 'w'), indent=1, ensure_ascii=False)
    muybridge(os.path.join(A, 'si_tif/SIA-2004-44793.tif'), os.path.join(A, 'work/muybridge_gallop'))


if __name__ == '__main__':
    main()
