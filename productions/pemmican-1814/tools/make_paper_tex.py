"""Generate a period-style paper texture with illegible pen strokes (not a facsimile of any document)."""
import sys, math
import numpy as np
import cv2

rng = np.random.default_rng(14)
W, H = 1800, 2300
img = np.zeros((H, W, 3), np.float32)
img[:] = (0.80, 0.86, 0.90)[::-1]  # BGR of a warm cream
base = np.array([0.72, 0.84, 0.90], np.float32)   # BGR
img[:] = base
# fibres + mottling
for s, a in ((400, 0.05), (90, 0.035), (12, 0.025)):
    n = rng.normal(0, 1, (H // s + 2, W // s + 2)).astype(np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)
    img += n[:, :, None] * a * np.array([1.0, 0.8, 0.5], np.float32)
# foxing spots and an edge darkening
for _ in range(40):
    x, y, r = rng.integers(0, W), rng.integers(0, H), rng.integers(4, 30)
    cv2.circle(img, (int(x), int(y)), int(r), (0.55, 0.68, 0.78), -1, cv2.LINE_AA)
img = cv2.GaussianBlur(img, (0, 0), 1.2)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
edge = np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)) / 120.0
img *= (0.82 + 0.18 * np.clip(edge, 0, 1))[:, :, None]

ink = np.zeros((H, W), np.float32)


def word(x0, y0, w, h, thick):
    """A pseudo-cursive word: a looping baseline stroke with random ascenders."""
    n = int(w / 3)
    t = np.linspace(0, 1, n)
    freq = rng.uniform(5, 8) * w / 120
    ph = rng.uniform(0, 6)
    x = x0 + t * w + np.sin(t * freq * 2 * math.pi + ph) * h * 0.18
    y = y0 - np.abs(np.sin(t * freq * math.pi + ph)) * h * rng.uniform(0.35, 0.6)
    for k in range(rng.integers(0, 3)):   # ascenders / descenders
        c = rng.uniform(0.1, 0.9)
        m = np.exp(-((t - c) / 0.03) ** 2)
        y = y - m * h * rng.choice([1.2, -0.8])
    pts = np.stack([x, y], 1).astype(np.int32)
    cv2.polylines(ink, [pts], False, 1.0, int(thick), cv2.LINE_AA)


y = 260
x = 230
# heading
for k in range(4):
    w = rng.uniform(110, 240)
    word(x, y, w, 60, 5)
    x += w + 40
y += 150
while y < H - 220:
    x = 170 + (60 if rng.random() < 0.12 else 0)
    end = W - rng.uniform(150, 260)
    while x < end:
        w = rng.uniform(50, 190)
        if x + w > end:
            break
        word(x, y, w, 34, 3)
        x += w + rng.uniform(18, 34)
    y += rng.uniform(64, 74)
ink = cv2.GaussianBlur(ink, (0, 0), 0.8)
ink_col = np.array([0.16, 0.18, 0.22], np.float32)   # iron-gall brown-black (BGR)
a = np.clip(ink * rng.uniform(0.75, 0.9), 0, 1)[:, :, None]
img = img * (1 - a) + ink_col * a
cv2.imwrite(sys.argv[1], np.clip(img * 255, 0, 255).astype(np.uint8))
print('ok', sys.argv[1])
