"""M0b: is a *terminal-only* change perceptible at small sizes?

Holds everything else constant: v1.2.1 filter output vs the same output with E10
terminal templates pasted on.  This isolates the exact change v1.3 proposes.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import brush_lib as B  # noqa: E402
import terminal_lib as T  # noqa: E402
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]


def features(img):
    g = img.astype(np.float32); ink = g > 127; h, w = g.shape
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    dt = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 5)
    v = dt[ink]
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    return np.array([ink.mean(), mag.mean()/255, mag.std()/255, n-1,
                     v.mean()/w if len(v) else 0, v.std()/w if len(v) else 0,
                     ink[:h//2,:w//2].mean(), ink[h//2:,w//2:].mean()], np.float32)


def resize_bin(m, s):
    g = cv2.resize(m.astype(np.float32), (s, s), interpolation=cv2.INTER_AREA)
    return (g > 127).astype(np.uint8) * 255


def main():
    d = np.load(ROOT/"work/pairs/pairs.npz", allow_pickle=True)
    chars = [str(c) for c in d["chars"]]; Y = d["Y"]
    rng = np.random.RandomState(0)
    tmpl, _ = T.build_templates([Y[i] > 127 for i in rng.choice(len(Y), 200, replace=False)],
                                nbins=4, size=28)
    rng = np.random.RandomState(13)
    idx = rng.choice(len(chars), 150, replace=False)
    base, mock = [], []
    for i in idx:
        m = B.render_char(chars[i], str(ROOT/"data/base/LXGWWenKai-Regular.ttf"))
        v12 = cv2.morphologyEx(cv2.erode(m.astype(np.uint8), np.ones((1,3), np.uint8)),
                               cv2.MORPH_CLOSE, np.ones((3,3), np.uint8))
        v13 = T.apply_templates(v12 > 0, tmpl, nbins=4, size=28).astype(np.uint8)
        base.append(v12*255); mock.append(v13*255)
    out = {}
    for s in (16, 24, 32, 48):
        X, y = [], []
        for a, b in zip(base, mock):
            X.append(features(resize_bin(a, s))); y.append(0)
            X.append(features(resize_bin(b, s))); y.append(1)
        X = np.array(X); y = np.array(y)
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
        auc = cross_val_score(clf, X, y, cv=5, scoring="roc_auc").mean()
        out[s] = round(float(auc), 3)
        print(f"{s}px  v1.2 vs v1.3-mock  AUC {auc:.3f}")
    (ROOT/"work/m0_terminal.json").write_text(json.dumps(out, indent=2))
    # visual sheet at 24px, 3x zoom
    sheet = np.zeros((24*2*3, 24*12*3), np.uint8)
    for j, i in enumerate(idx[:12]):
        for r, arr in enumerate([base[j], mock[j]]):
            t = cv2.resize(arr, (24, 24), interpolation=cv2.INTER_AREA)
            t = cv2.resize(t, (72, 72), interpolation=cv2.INTER_NEAREST)
            sheet[r*72:(r+1)*72, j*72:(j+1)*72] = t
    cv2.imwrite(str(ROOT/"work/preview/m0_terminal_24px.png"), sheet)


if __name__ == "__main__":
    main()
