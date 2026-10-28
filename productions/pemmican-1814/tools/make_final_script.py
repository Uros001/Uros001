"""Write script/FINAL_SCRIPT.md: narration with timings, and the picture under each paragraph (from the EDL)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from film import core, edl
from film.shots import Plate


def mmss(t):
    return f'{int(t // 60)}:{t % 60:04.1f}'


def main():
    tim = core.timing()
    clips = edl.resolved()
    ovs = edl.overlays()
    chap = {c['first_para']: c for c in tim['chapters']}
    out = ['# Final Script — The Pemmican War', '',
           f"Runtime {mmss(tim['total'])}. Narration: synthetic voice (Kokoro-82M, `af_heart`). Times are film times.",
           'Each paragraph lists the shots and on-screen text under it. Fact-check row ids are in `research/FACT_CHECK.md`.', '']
    ins = {i['kind']: i for i in tim['inserts']}
    out += ['## Cold open', '']
    for p in tim['paragraphs']:
        pid = p['pid']
        if pid in chap:
            c = chap[pid]
            out += [f"## {c['num']}. {c['title']}  ({mmss(c['start'])})", '']
        sents = [s for s in tim['sentences'] if s['pid'] == pid]
        text = ' '.join(s['text'] for s in sents)
        out += [f"**{pid}** · {mmss(p['start'])}–{mmss(p['end'])}", '', f'> {text}', '']
        vis = []
        for c in clips:
            if c['end'] > p['start'] + 0.2 and c['start'] < p['end'] - 0.2:
                sh = c['shot']
                d = f"`{sh.name}` {sh.desc}" if isinstance(sh, Plate) else sh.desc
                vis.append(f"{mmss(max(c['start'], p['start']))} {d}")
        for t0, t1, fn in ovs:
            if t1 > p['start'] and t0 < p['end']:
                vis.append(f"{mmss(t0)} *on screen:* {getattr(fn, 'desc', '')}")
        out += ['- ' + v for v in vis] + ['']
        if pid == 'P05':
            out += [f"**Title card** · {mmss(ins['TITLE']['start'])}: THE PEMMICAN WAR — Red River · 1812–1821", '']
    out += [f"**Credits** · {mmss(tim['credits']['start'])}–{mmss(tim['credits']['end'])}: disclosures (synthetic narration, "
            "3D reconstructions, generated props), map, music and font credits; sources in the description.", '']
    open(os.path.join(core.ROOT, 'script/FINAL_SCRIPT.md'), 'w').write('\n'.join(out))
    print('ok', len(out), 'lines')


if __name__ == '__main__':
    main()
