"""M0a: can a low-level discriminator tell real glyphs from synthesised ones at small sizes?

Real glyphs are passed through a light denoise first, so that manuscript scan noise
does not by itself make the two classes separable.  A high AUC means the *shape*
difference survives downscaling; AUC ~0.5 means it is invisible at that size.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import brush_lib as B  # noqa: E402
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]


def denoise(m: np.ndarray) -> np.ndarray:
    m = cv2.medianBlur(m.astype(np.uint8), 3)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    out = m.copy()
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 25:
            out[lab == i] = 0
    return out


def features(img: np.ndarray) -> np.ndarray:
    g = img.astype(np.float32)
    ink = g > 127
    h, w = g.shape
    q = [ink[:h // 2, :w // 2].mean(), ink[:h // 2, w // 2:].mean(),
         ink[h // 2:, :w // 2].mean(), ink[h // 2:, w // 2:].mean()]
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    dt = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 5)
    sk_vals = dt[ink]
    peri = (cv2.Laplacian(ink.astype(np.uint8), cv2.CV_32F) > 0).sum()
    return np.array([
        ink.mean(), *q, q[0] - q[3], q[1] - q[2],
        mag.mean() / 255, mag.std() / 255,
        n - 1, (n - 1) / max(1, ink.sum() / 1000.0),
        (ink.mean() * h * w) / max(1, peri),
        sk_vals.mean() / w if len(sk_vals) else 0,
        sk_vals.std() / w if len(sk_vals) else 0,
        ink.sum() / max(1, ink.shape[0]) / w,
    ], np.float32)


def resize_bin(m: np.ndarray, s: int) -> np.ndarray:
    g = cv2.resize(m.astype(np.float32), (s, s), interpolation=cv2.INTER_AREA)
    return (g > 127).astype(np.uint8) * 255


def main():
    d = np.load(ROOT / "work/pairs/pairs.npz", allow_pickle=True)
    chars = [str(c) for c in d["chars"]]
    Y = d["Y"]
    rng = np.random.RandomState(11)
    idx = rng.choice(len(chars), 200, replace=False)

    real, synth = [], []
    for i in idx:
        m = Y[i] > 127
        real.append(denoise(m.astype(np.uint8) * 255))
        base = B.render_char(chars[i], str(ROOT / "data/base/LXGWWenKai-Regular.ttf"))
        syn = cv2.morphologyEx(
            cv2.erode(base.astype(np.uint8), np.ones((1, 3), np.uint8)),
            cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) * 255
        synth.append(syn.astype(np.uint8))

    out = {}
    for s in (16, 24, 32, 48):
        X, y = [], []
        for a, b in zip(real, synth):
            X.append(features(resize_bin(a, s))); y.append(1)
            X.append(features(resize_bin(b, s))); y.append(0)
        X = np.array(X); y = np.array(y)
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
        auc = cross_val_score(clf, X, y, cv=5, scoring="roc_auc").mean()
        out[s] = round(float(auc), 3)
        print(f"{s}px  AUC {auc:.3f}")
    (ROOT / "work/m0_result.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
