import cv2
import numpy as np
from PIL import Image
S = 48

def norm_glyph(path):
    img = np.array(Image.open(path).convert("L"))
    thr = max(80, int(np.percentile(img, 50)) - 40)
    m = img < thr
    if m.sum() < 30:
        return None, None
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    h, w = y1 - y0, x1 - x0
    if h < 10 or w < 10:
        return None, None
    side = max(h, w) * 1.08
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    xa, ya = int(cx - side / 2), int(cy - side / 2)
    xb, yb = int(cx + side / 2), int(cy + side / 2)
    pad = max(0, -xa) + max(0, -ya) + max(0, xb - img.shape[1]) + max(0, yb - img.shape[0])
    if pad:
        img = cv2.copyMakeBorder(img, max(0, -ya), max(0, yb - img.shape[0]),
                                 max(0, -xa), max(0, xb - img.shape[1]),
                                 cv2.BORDER_CONSTANT, value=245)
        xa, ya, xb, yb = max(0, xa), max(0, ya), min(img.shape[1], xb), min(img.shape[0], yb)
    crop = img[ya:yb, xa:xb]
    if crop.size == 0:
        return None, None
    small = cv2.resize(crop, (S, S), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    return small, dict(w=int(w), h=int(h))
