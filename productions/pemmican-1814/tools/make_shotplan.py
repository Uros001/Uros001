"""Write production/SHOT_PLAN.md from the EDL (single source of truth)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from film import core, edl
from film.shots import Plate, Func, Archive, Diptych, Sequence, DocPage

ROOT = core.ROOT


def mmss(t):
    return f'{int(t // 60)}:{t % 60:05.2f}'


def kind(sh):
    if isinstance(sh, Plate):
        return '3D plate (2.5D move)'
    if isinstance(sh, DocPage):
        return 'Archival document (real page)'
    if isinstance(sh, (Archive, Diptych, Sequence)):
        return 'Archival image (real)'
    d = sh.desc.lower()
    if d.startswith(('map', 'globe')):
        return 'Map'
    return 'Motion graphic'


def main():
    clips = edl.resolved()
    tim = core.timing()
    lines = ['# Shot Plan — The Pemmican War', '',
             'Generated from `tools/film/edl.py`, the edit decision list the renderer actually uses. Times are film times',
             'resolved from the narration timing (`audio/narration/timing.json`). Transitions: `cut`, `dissolve n s`, `dip n s`',
             '(through black).', '',
             '**Visual sources.** Real archival material is used wherever it could be found and licensed: paintings and',
             'photographs from the Smithsonian (CC0) and the Library of Congress (no known restrictions), and pages of an',
             '1819 printed book from the Internet Archive (public domain), each credited on screen. Where no archival',
             'picture exists, the shot is an original Blender reconstruction (procedural geometry, rendered as background and',
             'foreground plates and moved in 2.5D with parallax), labelled as such. Maps use Natural Earth vectors and',
             'NASA/NOAA shaded relief (public domain). Graphics are original. No stock footage or AI image/video generation',
             'is used.', '']
    chap = {c['start']: f"{c['num']}. {c['title']}" for c in tim['chapters']}
    lines += ['| # | In | Out | Dur | Type | Shot | Transition in |', '|---|---|---|---|---|---|---|']
    for i, c in enumerate(clips, 1):
        sh = c['shot']
        x = c['xfade']
        tr = 'cut' if not x else (f'dissolve {x:.1f} s' if x > 0 else f'dip {abs(x):.1f} s')
        name = f"`{sh.name}` — {sh.desc}" if isinstance(sh, Plate) else sh.desc
        lines.append(f"| {i} | {mmss(c['start'])} | {mmss(c['end'])} | {c['end'] - c['start']:.1f} s | {kind(sh)} | {name} | {tr} |")
    lines += ['', '## Overlays (supers, lower thirds, counters)', '', '| In | Out | Overlay |', '|---|---|---|']
    for t0, t1, fn in edl.overlays():
        lines.append(f'| {mmss(t0)} | {mmss(t1)} | {getattr(fn, "desc", "overlay")} |')
    lines += ['', '## Counts', '']
    n3d = sum(isinstance(c['shot'], Plate) for c in clips)
    nm = sum(kind(c['shot']) == 'Map' for c in clips)
    na = sum(kind(c['shot']).startswith('Archival') for c in clips)
    ng = len(clips) - n3d - nm - na
    t3d = sum(c['end'] - c['start'] for c in clips if isinstance(c['shot'], Plate))
    tm = sum(c['end'] - c['start'] for c in clips if kind(c['shot']) == 'Map')
    ta = sum(c['end'] - c['start'] for c in clips if kind(c['shot']).startswith('Archival'))
    tdoc = sum(c['end'] - c['start'] for c in clips if isinstance(c['shot'], DocPage))
    lines += [f'- Clips: {len(clips)} (real archival {na}, 3D plate shots {n3d}, maps {nm}, graphics/cards {ng})',
              f'- Screen time: real archival {ta:.0f} s ({100 * ta / tim["total"]:.1f} %, of which document pages {tdoc:.0f} s), '
              f'3D reconstructions {t3d:.0f} s ({100 * t3d / tim["total"]:.1f} %), maps {tm:.0f} s, '
              f'graphics/cards {tim["total"] - t3d - tm - ta:.0f} s',
              f'- Average shot length: {tim["total"] / len(clips):.1f} s',
              f'- Unique Blender plates: {len({c["shot"].name for c in clips if isinstance(c["shot"], Plate)})}']
    open(os.path.join(ROOT, 'production/SHOT_PLAN.md'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[-5:]))


if __name__ == '__main__':
    main()
