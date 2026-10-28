"""Loudness helpers: measure integrated loudness (BS.1770 via pyloudnorm) and normalize a file
with a fixed gain followed by a true-peak-safe limiter (ffmpeg alimiter, 4x oversampled check)."""
import subprocess, sys, json
import numpy as np
import soundfile as sf
import pyloudnorm as pyln


def lufs(path):
    y, sr = sf.read(path, dtype='float64')
    return pyln.Meter(sr).integrated_loudness(y)


def true_peak_db(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    tail = r[r.rfind('Summary'):]
    for line in tail.splitlines():
        if 'Peak:' in line:
            return float(line.split('Peak:')[1].split('dBFS')[0])
    return None


def ebur128_summary(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    return r[r.rfind('Summary'):]


def normalize(src, dst, target_lufs, tp_limit_db=-1.5, prechain=''):
    """Optional ffmpeg prechain, then gain to target, then limiter at tp_limit_db."""
    tmp = dst + '.pre.wav'
    if prechain:
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-af', prechain,
                        '-c:a', 'pcm_f32le', tmp], check=True)
    else:
        tmp = src
    cur = lufs(tmp)
    gain = target_lufs - cur
    lim = 10 ** (tp_limit_db / 20)
    af = f'volume={gain:.3f}dB,alimiter=limit={lim:.4f}:attack=3:release=60:level=disabled:asc=true'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', tmp, '-af', af,
                    '-ar', '48000', '-c:a', 'pcm_s24le', dst], check=True)
    out = lufs(dst)
    # small second pass to correct limiter-induced loudness loss
    if abs(out - target_lufs) > 0.2:
        g2 = target_lufs - out
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', dst, '-af',
                        f'volume={g2:.3f}dB,alimiter=limit={lim:.4f}:attack=3:release=60:level=disabled',
                        '-ar', '48000', '-c:a', 'pcm_s24le', dst + '.tmp.wav'], check=True)
        subprocess.run(['mv', dst + '.tmp.wav', dst], check=True)
    return cur, lufs(dst), true_peak_db(dst)


if __name__ == '__main__':
    src, dst, target = sys.argv[1], sys.argv[2], float(sys.argv[3])
    pre = sys.argv[4] if len(sys.argv) > 4 else ''
    print(normalize(src, dst, target, prechain=pre))
