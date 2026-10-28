"""English subtitles from the narration timing (sentence-accurate), split into readable cues.

Rules: at most 2 lines x 42 characters per cue, at most ~7 s per cue, split long sentences at
punctuation (time shared in proportion to characters), minimum 0.9 s per cue.
  python3 make_srt.py <out.srt>
"""
import os, sys, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAXC = 42


def wrap(text):
    words = text.split()
    lines, cur = [], ''
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= MAXC:
            cur = (cur + ' ' + w).strip()
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def balanced(text):
    """Two-line wrap with roughly equal lines."""
    if len(text) <= MAXC:
        return [text]
    words = text.split()
    best = None
    for i in range(1, len(words)):
        a, b = ' '.join(words[:i]), ' '.join(words[i:])
        if len(a) <= MAXC and len(b) <= MAXC:
            score = abs(len(a) - len(b))
            if best is None or score < best[0]:
                best = (score, [a, b])
    return best[1] if best else wrap(text)


def chunks(text):
    """Split a sentence into pieces that each fit 2 x 42."""
    if len(text) <= 2 * MAXC - 4:
        return [text]
    parts = re.split(r'(?<=[,;:—])\s+', text)
    out, cur = [], ''
    for p in parts:
        if cur and len(cur) + 1 + len(p) > 2 * MAXC - 4:
            out.append(cur)
            cur = p
        else:
            cur = (cur + ' ' + p).strip()
    if cur:
        out.append(cur)
    final = []
    for c in out:
        while len(c) > 2 * MAXC - 4:
            words = c.split()
            half = len(words) // 2
            final.append(' '.join(words[:half]))
            c = ' '.join(words[half:])
        final.append(c)
    return final


def ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def main():
    tim = json.load(open(os.path.join(ROOT, 'audio/narration/timing.json')))
    cues = []
    for s in tim['sentences']:
        pieces = chunks(s['text'])
        total = sum(len(p) for p in pieces)
        t = s['start']
        dur = s['end'] - s['start']
        for p in pieces:
            d = dur * len(p) / total
            cues.append([t, t + d, p])
            t += d
    # small lead-out and minimum duration, never overlapping the next cue
    for i, c in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else c[1] + 2
        c[1] = min(max(c[1] + 0.25, c[0] + 0.9), nxt - 0.04)
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f'{i}\n{ts(a)} --> {ts(b)}\n' + '\n'.join(balanced(txt)) + '\n\n')
    print(len(cues), 'cues written')


if __name__ == '__main__':
    main()
