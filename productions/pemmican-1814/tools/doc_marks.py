"""Prepare scanned Internet Archive pages for the film: crop, and find phrases to highlight from the scan's OCR word boxes.

  python3 -I tools/doc_marks.py        (needs assets/archival/ia/: see tools/fetch_documents.sh)

Source: "Report of the proceedings connected with the disputes between the Earl of Selkirk, and the North-West Company, at
the assizes, held at York in Upper Canada, October 1818" (Montreal: Lane and Mower, 1819), University of Toronto copy,
Internet Archive item reportofproceedi00wilc. Printed in 1819, so in the public domain.

Writes assets/archival/work/doc_<name>.jpg (cropped page) and work/doc_marks.json: {name: {phrase: [[x0, y0, x1, y1], ...]}}
with boxes normalized to the cropped image, one box per text line of the phrase.
"""
import os, re, json
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IA = os.path.join(ROOT, 'assets/archival/ia')
WORK = os.path.join(ROOT, 'assets/archival/work')
BOOK = 'reportofproceedi00wilc'
META_TITLE = ('Report of the proceedings connected with the disputes between the Earl of Selkirk, and the North-West Company, '
              'at the assizes, held at York in Upper Canada, October 1818: from minutes taken in court')

# name: leaf (= object index in the djvu.xml = BookReader page n<leaf>), crop as fractions of the scan, phrases.
# A phrase is (start words, end word prefix or None, extra words after the start words[, words to include before]); the OCR damages a few words, so a
# phrase runs "from these words to the first word starting with this, within 30 words".
PAGES = {
    'proclamation': dict(leaf=167, printed='p. 134', title="Macdonell's proclamation, 8 January 1814 (as printed in 1819)", crop=(0.03, 0.0, 0.975, 0.705), phrases={      # printed page 134 (cut after the Secretary's line)
        'date_given': (['given', 'under', 'my', 'hand', 'at', 'fort', 'daer'], '1814', 0),
        'one_year': (['one', 'twelvemonth', 'from', 'the', 'date', 'hereof'], None, 0),
        'foods': (['flesh', 'fish', 'grain', 'or', 'vegetabl'], None, 0),
        'take_out': (['shall', 'take', 'out', 'any', 'pro'], None, 1),
        'except': (['save', 'and', 'except'], 'tinations', 0),
        'licence': (['obtain'], 'same', 0),
        'paid': (['paid', 'for', 'by'], 'rates', 0),
        'forfeited': (['shall', 'be', 'forfeited'], None, 0),
        'signed': (['miles', 'macdonell'], None, 1),
    }),
    'glossary': dict(leaf=19, printed='p. xiv', title='Glossary: "Pemican" and "Taureau", as printed in 1819', crop=(0.04, 0.0, 0.97, 0.52), phrases={            # printed page xiv
        'pemican': (['the', 'meat', 'of', 'buffaloes'], 'fat', 0, 1),
        'universal': (['it', 'is', 'the', 'universal'], 'season', 0),
        'piece': (['piece'], 'portages', 0),
        'taureau': (['itaureau'], 'lbs', 0),
    }),
    'title': dict(leaf=6, printed='title page', title='Report of the proceedings, York assizes, October 1818 (title page, 1819)', crop=(0.04, 0.0, 0.97, 0.93), phrases={}),
}


def words(xml_obj):
    out = []
    for m in re.finditer(r'<WORD coords="([^"]+)"[^>]*>([^<]*)</WORD>', xml_obj):
        x1, yb, x2, yt = (int(v) for v in m.group(1).split(',')[:4])
        out.append((re.sub(r'[^a-z0-9]', '', m.group(2).lower()), x1, yt, x2, yb))
    return out


def find(ws, spec):
    start, end, extra, before = (list(spec) + [0])[:4] if len(spec) == 3 else spec
    for i in range(len(ws) - len(start) + 1):
        if all(ws[i + k][0].startswith(p) for k, p in enumerate(start)):
            j = i + len(start)
            a = max(0, i - before)
            if end:
                for k in range(j, min(len(ws), j + 30)):
                    if ws[k][0].startswith(end):
                        return ws[a:k + 1]
                continue
            return ws[a:j + extra]
    return None


def line_boxes(seq):
    """Group matched words into one box per text line."""
    lines = []
    for w in seq:
        cy = (w[2] + w[4]) / 2
        if lines and abs(cy - lines[-1]['cy']) < 30:
            b = lines[-1]
            b['x1'], b['y1'], b['x2'], b['y2'] = min(b['x1'], w[1]), min(b['y1'], w[2]), max(b['x2'], w[3]), max(b['y2'], w[4])
        else:
            lines.append(dict(cy=cy, x1=w[1], y1=w[2], x2=w[3], y2=w[4]))
    return lines


def main():
    xml = open(os.path.join(IA, f'{BOOK}_djvu.xml'), encoding='utf-8', errors='replace').read().split('<OBJECT')[1:]
    os.makedirs(WORK, exist_ok=True)
    allmarks = {}
    for name, cfg in PAGES.items():
        img = cv2.imread(os.path.join(IA, f"report_n{cfg['leaf']}.jpg"))
        H, W = img.shape[:2]
        x0, y0, x1, y1 = cfg['crop'][0] * W, cfg['crop'][1] * H, cfg['crop'][2] * W, cfg['crop'][3] * H
        cw, ch = x1 - x0, y1 - y0
        ws = words(xml[cfg['leaf']])
        marks = {}
        for pname, spec in cfg['phrases'].items():
            seq = find(ws, spec)
            if not seq:
                print('NOT FOUND', name, pname)
                continue
            pad = 8
            marks[pname] = [[round((b['x1'] - pad - x0) / cw, 4), round((b['y1'] - pad - y0) / ch, 4),
                             round((b['x2'] + pad - x0) / cw, 4), round((b['y2'] + pad - y0) / ch, 4)] for b in line_boxes(seq)]
            print(name, pname, len(marks[pname]), 'line box(es):', ' '.join(w[0] for w in seq))
        allmarks[name] = marks
        crop = img[int(y0):int(y1), int(x0):int(x1)]
        cv2.imwrite(os.path.join(WORK, f'doc_{name}.jpg'), crop, [cv2.IMWRITE_JPEG_QUALITY, 93])
        chk = crop.copy()
        for bxs in marks.values():
            for bx in bxs:
                cv2.rectangle(chk, (int(bx[0] * cw), int(bx[1] * ch)), (int(bx[2] * cw), int(bx[3] * ch)), (0, 0, 255), 4)
        s = 1100 / chk.shape[0]
        chk_dir = os.environ.get('DOC_CHECK_DIR')
        if chk_dir:
            cv2.imwrite(os.path.join(chk_dir, f'check_{name}.jpg'), cv2.resize(chk, (int(chk.shape[1] * s), 1100), interpolation=cv2.INTER_AREA))
    json.dump(allmarks, open(os.path.join(WORK, 'doc_marks.json'), 'w'), indent=1)
    register()


def register():
    """Add the three pages to assets/archival/ARCHIVAL_SOURCES.json (same fields as the images; prep_archival.py keeps them)."""
    f = os.path.join(ROOT, 'assets/archival/ARCHIVAL_SOURCES.json')
    reg = json.load(open(f))
    for name, cfg in PAGES.items():
        im = cv2.imread(os.path.join(WORK, f'doc_{name}.jpg'))
        reg[f'doc_{name}'] = dict(
            file=f'assets/archival/work/doc_{name}.jpg', size=[im.shape[1], im.shape[0]], title=cfg['title'],
            maker='Lane and Mower, printers, Montreal', date='1819',
            collection='Internet Archive (University of Toronto, Thomas Fisher Library copy)',
            smithsonian_id=f"{BOOK}, {cfg['printed']}", record_id=BOOK,
            record_link=f"https://archive.org/details/{BOOK}/page/n{cfg['leaf']}", guid='',
            rights='Public domain (printed 1819); scan by the University of Toronto',
            catalog_title=META_TITLE, catalog_date='1819', catalog_artist='Wilcocke, Samuel Hull, 1766?-1833')
    json.dump(reg, open(f, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
