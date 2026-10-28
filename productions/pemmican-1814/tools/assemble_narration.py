"""Assemble per-sentence narration WAVs into one timed track and write the film timing map.

Outputs (in audio/narration/):
  narration_dry.wav      48 kHz mono, sentences placed at their film times (no processing)
  timing.json            film-time map: sentences, paragraphs, inserts (title, chapters, credits)

The pause design lives in BEATS below; PARA_GAP is solved so the film runs TARGET seconds.
"""
import json, os, re, sys
import numpy as np
import soundfile as sf
import librosa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'audio/narration/raw')
OUT = os.path.join(ROOT, 'audio/narration')
SR = 48000
TARGET = 900.0          # ~15:00

PRE_ROLL = 1.6          # ambience / first image before the first word
SENT_GAP = 0.30
SHORT_SENT_EXTRA = 0.18  # after very short sentences ("Frog Plain.")
QUESTION_EXTRA = 0.25
# extra silence after a paragraph (seconds, on top of PARA_GAP)
AFTER = {'P01': 0.5, 'P02': 0.4, 'P03': 1.6, 'P04': 0.6, 'P07': 0.9, 'P08': 0.7, 'P09': 0.6,
         'P11': 0.5, 'P12': 0.6, 'P14': 0.4, 'P16': 0.8, 'P17': 0.8, 'P18': 0.6, 'P21': 0.6,
         'P22': 1.0, 'P23': 0.8, 'P24': 0.5, 'P26': 0.6, 'P27': 0.7, 'P28': 0.6, 'P29': 1.2,
         'P30': 3.2, 'P31': 0.8, 'P32': 1.0, 'P33': 0.6, 'P34': 0.6, 'P35': 0.6, 'P36': 0.6,
         'P37': 0.6, 'P38': 0.9, 'P39': 2.8, 'P40': 1.6, 'P41': 1.4}
# inserted non-narrated segments (after paragraph): id -> (kind, seconds)
INSERT_AFTER = {'P05': ('TITLE', 6.5), 'P12': ('CH2', 3.6), 'P19': ('CH3', 3.6),
                'P24': ('CH4', 3.6), 'P33': ('CH5', 3.6)}
CREDITS = 15.0
CHAPTERS = {'CH1': ('I', 'Meat That Keeps', 'P06'), 'CH2': ('II', 'The Canoe Road', 'P13'),
            'CH3': ('III', 'The Order', 'P20'), 'CH4': ('IV', 'Frog Plain', 'P25'),
            'CH5': ('V', 'The Last Hunts', 'P34')}


def trim(y, sr, thr_db=-42, pad=0.03):
    """Trim leading/trailing silence, keep a short pad so consonants are not clipped."""
    rms = librosa.feature.rms(y=y, frame_length=512, hop_length=128)[0]
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    on = np.where(db > thr_db)[0]
    if len(on) == 0:
        return y
    s = max(0, on[0] * 128 - int(pad * sr))
    e = min(len(y), (on[-1] + 1) * 128 + int(pad * sr))
    return y[s:e]


def load_sentences():
    meta = json.load(open(os.path.join(RAW, 'sentences.json')))
    paras = {}
    for fn, m in meta.items():
        paras.setdefault(m['pid'], []).append((m['idx'], fn, m))
    out = []
    for pid in sorted(paras, key=lambda p: int(p[1:])):
        sents = []
        for idx, fn, m in sorted(paras[pid]):
            y, sr = sf.read(os.path.join(RAW, 'sentences', fn), dtype='float32')
            y = trim(y, sr)
            y = librosa.resample(y, orig_sr=sr, target_sr=SR)
            # 6 ms fades to avoid clicks
            f = int(0.006 * SR)
            y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
            sents.append(dict(file=fn, text=m['text'], audio=y))
        out.append((pid, sents))
    return out


def layout(paras, para_gap):
    t = PRE_ROLL
    timeline, inserts = [], []
    for pi, (pid, sents) in enumerate(paras):
        pstart = t
        for si, s in enumerate(sents):
            d = len(s['audio']) / SR
            timeline.append(dict(pid=pid, idx=si, file=s['file'], text=s['text'], start=round(t, 3), end=round(t + d, 3)))
            t += d
            if si < len(sents) - 1:
                gap = SENT_GAP
                if len(s['text'].split()) <= 3:
                    gap += SHORT_SENT_EXTRA
                if s['text'].endswith('?'):
                    gap += QUESTION_EXTRA
                t += gap
        pend = t
        timeline_p = dict(pid=pid, start=round(pstart, 3), end=round(pend, 3))
        inserts.append(('PARA', timeline_p))
        t += para_gap + AFTER.get(pid, 0.0)
        if pid in INSERT_AFTER:
            kind, dur = INSERT_AFTER[pid]
            inserts.append((kind, dict(start=round(t, 3), end=round(t + dur, 3))))
            t += dur
    credits = dict(start=round(t, 3), end=round(t + CREDITS, 3))
    return timeline, inserts, credits, t + CREDITS


def main():
    paras = load_sentences()
    lo, hi = 0.3, 2.5
    for _ in range(40):
        mid = (lo + hi) / 2
        total = layout(paras, mid)[3]
        lo, hi = (mid, hi) if total < TARGET else (lo, mid)
    para_gap = round((lo + hi) / 2, 3)
    para_gap = min(max(para_gap, 0.7), 1.6)
    timeline, inserts, credits, total = layout(paras, para_gap)
    track = np.zeros(int((total + 0.5) * SR), np.float32)
    flat = {s['file']: s['audio'] for _, ss in paras for s in ss}
    for s in timeline:
        a = flat[s['file']]
        i = int(round(s['start'] * SR))
        track[i:i + len(a)] += a
    sf.write(os.path.join(OUT, 'narration_dry.wav'), track, SR, subtype='PCM_24')
    paragraphs = [d for k, d in inserts if k == 'PARA']
    ins = [dict(kind=k, **d) for k, d in inserts if k != 'PARA']
    chapters = []
    for cid, (num, name, pstart) in CHAPTERS.items():
        p = next(x for x in paragraphs if x['pid'] == pstart)
        card = next((x for x in ins if x['kind'] == cid), None)
        chapters.append(dict(id=cid, num=num, title=name, start=card['start'] if card else p['start'], first_para=pstart))
    timing = dict(fps=30, total=round(total, 3), para_gap=para_gap, pre_roll=PRE_ROLL, sentences=timeline,
                  paragraphs=paragraphs, inserts=ins, credits=credits, chapters=chapters)
    json.dump(timing, open(os.path.join(OUT, 'timing.json'), 'w'), indent=1, ensure_ascii=False)
    speech = sum(s['end'] - s['start'] for s in timeline)
    words = sum(len(re.findall(r"[\w'’-]+", s['text'])) for s in timeline)
    print(f'para_gap={para_gap}s total={total:.1f}s ({total/60:.2f} min) speech={speech:.1f}s words={words} '
          f'rate={words/(speech/60):.0f} wpm (speech) / {words/(total/60):.0f} wpm (overall)')
    for c in chapters:
        print(c['num'], c['title'], f"{int(c['start']//60)}:{c['start']%60:05.2f}")


if __name__ == '__main__':
    main()
