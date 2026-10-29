"""Export the base map (Natural Earth relief, rivers, lakes; as in the film's mapseq.souris) at 2880x1620 and the
projected positions of the colony, the route and the North West Company post, for the HyperFrames composition."""
import os, sys, json
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../../productions/pemmican-1814/tools'))
from film import core
core.set_size(2880, 1620)                       # 1.5 x the film frame, so the camera can push in and stay sharp
from film import maps as M, mapseq as MS

cam = M.MapCam(-98.3, 49.8, 520)                # the film's start camera for this map
img = core.grade(M.base(cam, relief=1.0, borders=0.1, graticule=0.0, rivers=1.3), contrast=1.04, sat=0.95)
cv2.imwrite(os.path.join(HERE, 'assets/base.jpg'), (np.clip(img, 0, 1)[:, :, ::-1] * 255).astype(np.uint8),
            [cv2.IMWRITE_JPEG_QUALITY, 94])
pts = np.array([MS.FORT_DOUGLAS, (-97.6, 49.85), (-98.6, 49.85), (-99.2, 49.7), MS.SOURIS_POST], float)
sm = M._catmull(pts, 12)
x, y, _ = cam.project(sm[:, 0], sm[:, 1])
P = lambda lon, lat: [round(v, 1) for v in cam.p(lon, lat)]
json.dump(dict(route=[[round(a, 1), round(b, 1)] for a, b in zip(x, y)], douglas=P(*MS.FORT_DOUGLAS),
               souris=P(*MS.SOURIS_POST), souris_label=P(-100.0, 49.42), start_center=P(-98.3, 49.8),
               end_center=P(-98.4, 49.78), end_zoom=600 / 520), open(os.path.join(HERE, 'assets/geo.json'), 'w'))
