"""Depth maps for archival stills, for 2.5D camera moves (shots.ArchiveDepth).

  python3 -I tools/depth_map.py <key> [<key> ...]        keys of assets/archival/ARCHIVAL_SOURCES.json

Model: Depth Anything V2 Small (Apache-2.0), ONNX export, studio/models/depth_anything_v2_vits_dynamic.onnx
(see studio/setup_tools.sh). Writes assets/archival/work/depth/<key>.png: 16-bit, near = white, far = black,
normalized between the 1st and 99th percentile. The map only tells the renderer how far to move each pixel;
nothing is added to the picture.
"""
import os, sys, json
import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(os.path.dirname(os.path.dirname(ROOT)), 'studio/models/depth_anything_v2_vits_dynamic.onnx')
OUT = os.path.join(ROOT, 'assets/archival/work/depth')
SHORT = 1036                              # inference size of the short side (multiple of 14)


def depth(img_rgb, sess):
    H, W = img_rgb.shape[:2]
    s = SHORT / min(H, W)
    h, w = int(round(H * s / 14)) * 14, int(round(W * s / 14)) * 14
    x = cv2.resize(img_rgb, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    d = sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0].squeeze()
    lo, hi = np.percentile(d, 1), np.percentile(d, 99)
    return np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)


def main():
    import onnxruntime as ort
    reg = json.load(open(os.path.join(ROOT, 'assets/archival/ARCHIVAL_SOURCES.json')))
    sess = ort.InferenceSession(MODEL, providers=['CPUExecutionProvider'])
    os.makedirs(OUT, exist_ok=True)
    for key in sys.argv[1:]:
        img = cv2.imread(os.path.join(ROOT, reg[key]['file']))[:, :, ::-1]
        d = depth(np.ascontiguousarray(img), sess)
        cv2.imwrite(os.path.join(OUT, key + '.png'), (d * 65535).astype(np.uint16))
        print(key, d.shape)


if __name__ == '__main__':
    main()
