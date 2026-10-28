"""Procedural leaf atlas (RGBA, 2x2): lobed oak-type leaves with veins and colour variation, for leaf cards."""
import sys, math
import numpy as np
import cv2

rng = np.random.default_rng(5)
S = 512


def leaf(seed, lobes=7, base_col=(52, 92, 64), sat=1.0):
    r = np.random.default_rng(seed)
    img = np.zeros((S, S, 4), np.float32)
    pts = []
    n = 400
    for i in range(n + 1):
        t = i / n                       # 0..1 along the outline (left side up, right side down)
        u = t * 2 if t <= 0.5 else (1 - t) * 2     # 0 at tip/base, 1 at the middle
        y = (t * 2 if t <= 0.5 else (1 - t) * 2)
        yy = 0.06 + 0.88 * (1 - (y if t <= 0.5 else y))
        # half-width profile: obovate (wider near the tip end), lobed
        s = 1 - yy
        w = 0.42 * (math.sin(math.pi * min(1, s * 1.08)) ** 0.8) * (0.55 + 0.45 * s)
        lob = 0.5 + 0.5 * math.cos(s * lobes * math.pi * 2)
        w *= 0.62 + 0.38 * lob ** 1.5 * (0.5 + 0.5 * s)
        x = 0.5 + (-w if t <= 0.5 else w)
        pts.append((x * S, yy * S))
    poly = np.array(pts, np.int32)
    mask = np.zeros((S, S), np.uint8)
    cv2.fillPoly(mask, [poly], 255, cv2.LINE_AA)
    col = np.array(base_col, np.float32) / 255.0
    n1 = cv2.resize(r.random((8, 8)).astype(np.float32), (S, S), interpolation=cv2.INTER_CUBIC)
    n2 = cv2.resize(r.random((64, 64)).astype(np.float32), (S, S), interpolation=cv2.INTER_CUBIC)
    shade = 0.8 + 0.3 * n1 + 0.08 * n2
    rgb = col[None, None, :] * shade[:, :, None]
    veins = np.zeros((S, S), np.float32)
    cv2.line(veins, (S // 2, int(0.94 * S)), (S // 2, int(0.08 * S)), 1.0, 5, cv2.LINE_AA)
    for k in range(lobes):
        yv = int((0.85 - k * 0.7 / lobes) * S)
        for sgn in (-1, 1):
            cv2.line(veins, (S // 2, yv), (int(S / 2 + sgn * 0.33 * S), int(yv - 0.08 * S)), 0.7, 2, cv2.LINE_AA)
    veins = cv2.GaussianBlur(veins, (0, 0), 1.2)
    rgb = rgb * (1 + 0.35 * veins[:, :, None])
    # stem
    cv2.line(mask, (S // 2, int(0.94 * S)), (S // 2, S - 4), 255, 6, cv2.LINE_AA)
    # brown edges / blemishes
    edge = cv2.GaussianBlur((mask > 0).astype(np.float32), (0, 0), 6)
    rgb = rgb * (0.85 + 0.15 * edge[:, :, None]) + np.array([0.06, 0.03, 0.0], np.float32) * (1 - edge[:, :, None]) * 0.6
    a = mask.astype(np.float32) / 255
    img[:, :, :3] = np.clip(rgb, 0, 1)
    img[:, :, 3] = a
    return img


atlas = np.zeros((2 * S, 2 * S, 4), np.float32)
cols = [(58, 96, 66), (52, 88, 70), (64, 104, 72), (70, 98, 62)]   # BGR greens
for i in range(4):
    r, c = divmod(i, 2)
    atlas[r * S:(r + 1) * S, c * S:(c + 1) * S] = leaf(10 + i, lobes=5 + i % 3, base_col=cols[i])
out = (np.clip(atlas, 0, 1) * 255).astype(np.uint8)
cv2.imwrite(sys.argv[1], out)
print('ok', sys.argv[1])
