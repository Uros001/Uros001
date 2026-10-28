"""Automated QA for the final deliverable. Writes production/QA_REPORT.md data block to stdout (JSON) and a
contact sheet of sampled frames.

  python3 qa.py <video.mp4> <srt> <contact_sheet.jpg>
"""
import os, sys, json, re, subprocess
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path])
    return json.loads(r.stdout)


def detect(path, filt, pattern, kind='video'):
    flag = '-vf' if kind == 'video' else '-af'
    r = run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, flag, filt, '-an' if kind == 'video' else '-vn', '-f', 'null', '-'])
    return re.findall(pattern, r.stderr)


def srt_cues(path):
    txt = open(path, encoding='utf-8').read().strip().split('\n\n')
    out = []
    for b in txt:
        lines = b.split('\n')
        a, z = lines[1].split(' --> ')

        def sec(s):
            h, m, rest = s.split(':')
            s2, ms = rest.split(',')
            return int(h) * 3600 + int(m) * 60 + int(s2) + int(ms) / 1000
        out.append((sec(a), sec(z), ' '.join(lines[2:])))
    return out


def main():
    video, srt, sheet = sys.argv[1:4]
    res = {}
    pr = probe(video)
    v = next(s for s in pr['streams'] if s['codec_type'] == 'video')
    a = next(s for s in pr['streams'] if s['codec_type'] == 'audio')
    fps = eval(v['r_frame_rate'])
    res['container'] = dict(format=pr['format']['format_name'], duration=float(pr['format']['duration']),
                            size_mb=round(int(pr['format']['size']) / 1e6, 1), bitrate_kbps=round(int(pr['format']['bit_rate']) / 1000))
    res['video'] = dict(codec=v['codec_name'], profile=v.get('profile'), w=v['width'], h=v['height'], fps=fps, pix_fmt=v['pix_fmt'],
                        frames=int(v.get('nb_frames', 0)), color=v.get('color_space'), duration=float(v.get('duration', 0)))
    res['audio'] = dict(codec=a['codec_name'], sr=int(a['sample_rate']), ch=a['channels'], bitrate_kbps=round(int(a.get('bit_rate', 0)) / 1000),
                        duration=float(a.get('duration', 0)))
    res['spec_ok'] = dict(h264=v['codec_name'] == 'h264', res=v['width'] >= 1920 and v['height'] >= 1080, fps30=abs(fps - 30) < 0.01,
                          aac=a['codec_name'] == 'aac', sr48k=int(a['sample_rate']) == 48000, stereo=a['channels'] == 2,
                          av_dur_match=abs(float(v.get('duration', 0)) - float(a.get('duration', 0))) < 0.1)
    # black frames (excluding intended fades at head/tail and dips)
    blacks = detect(video, 'blackdetect=d=0.4:pix_th=0.06', r'black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)')
    res['black_segments'] = [tuple(round(float(x), 2) for x in b) for b in blacks]
    freezes = detect(video, 'freezedetect=n=0.0008:d=3', r'freeze_start: ([\d.]+)|freeze_end: ([\d.]+)')
    res['freeze_events'] = len([f for f in freezes if f[0]])
    sil = detect(video, 'silencedetect=noise=-50dB:d=1.5', r'silence_start: ([\d.]+)|silence_end: ([\d.]+) \| silence_duration: ([\d.]+)', 'audio')
    res['silences_over_1_5s'] = [(round(float(s[1]) - float(s[2]), 2), round(float(s[2]), 2)) for s in sil if s[1]]
    # loudness
    r = run(['ffmpeg', '-hide_banner', '-nostats', '-i', video, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'])
    tail = r.stderr[r.stderr.rfind('Summary'):]
    I = re.search(r'I:\s+(-?[\d.]+) LUFS', tail)
    TP = re.search(r'Peak:\s+(-?[\d.]+) dBFS', tail)
    LRA = re.search(r'LRA:\s+([\d.]+) LU', tail)
    res['loudness'] = dict(integrated_lufs=float(I.group(1)), true_peak_dbtp=float(TP.group(1)), lra=float(LRA.group(1)))
    # subtitles vs narration timing
    tim = json.load(open(os.path.join(ROOT, 'audio/narration/timing.json')))
    cues = srt_cues(srt)
    sents = tim['sentences']
    words_srt = sum(len(c[2].split()) for c in cues)
    words_nar = sum(len(s['text'].split()) for s in sents)
    starts = sorted(c[0] for c in cues)
    off = [min(abs(s['start'] - c) for c in starts) for s in sents]
    overl = sum(1 for x, y in zip(cues, cues[1:]) if y[0] < x[1])
    res['subtitles'] = dict(cues=len(cues), words_srt=words_srt, words_narration=words_nar, max_sentence_start_offset_s=round(max(off), 3),
                            overlaps=overl, last_cue_end=round(cues[-1][1], 2), max_line_len=max(len(l) for c in cues for l in c[2].split('\n')))
    # contact sheet: one frame every 15 s
    dur = res['container']['duration']
    tdir = sheet + '.frames'
    os.makedirs(tdir, exist_ok=True)
    tiles = []
    import cv2
    for i, t in enumerate(np.arange(7.5, dur, 15.0)):
        p = os.path.join(tdir, f'{i:03d}.jpg')
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1', '-q:v', '3', p])
        im = cv2.imread(p)
        if im is None:
            continue
        im = cv2.resize(im, (384, 216))
        cv2.putText(im, f'{int(t // 60)}:{int(t % 60):02d}', (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(im)
    while len(tiles) % 6:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(sheet, np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    res['contact_sheet'] = sheet
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
