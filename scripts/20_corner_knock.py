"""Add a '顿' blob at sharp skeleton turns — the one computer-grass mechanism we never tried."""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import brush_lib as B  # noqa: E402


def turn_sites(mask, min_angle=60.0, cluster=4.0, min_len=12):
    """Cluster junction endpoints, then measure the bend between the two long edges."""
    ents = []
    for f in B.glyph_frames(mask):
        pts = f["pts"]
        n = len(pts)
        if n < min_len:
            continue
        k = min(6, n - 1)
        if f.get("start_junction"):
            v = pts[0] - pts[k]
            ents.append((float(pts[0][0]), float(pts[0][1]), v / (np.linalg.norm(v) + 1e-6),
                         float(f["r_obs"][0])))
        if f.get("end_junction"):
            v = pts[-1] - pts[-1 - k]
            ents.append((float(pts[-1][0]), float(pts[-1][1]), v / (np.linalg.norm(v) + 1e-6),
                         float(f["r_obs"][-1])))
    # greedy clustering
    groups = []
    for e in ents:
        placed = False
        for g in groups:
            if abs(g["y"] - e[0]) <= cluster and abs(g["x"] - e[1]) <= cluster:
                g["items"].append(e); g["y"] = 0.5 * (g["y"] + e[0]); g["x"] = 0.5 * (g["x"] + e[1])
                placed = True
                break
        if not placed:
            groups.append({"y": e[0], "x": e[1], "items": [e]})
    sites = []
    for g in groups:
        items = g["items"]
        if len(items) != 2:
            continue
        (_, _, u1, r1), (_, _, u2, r2) = items
        cos = float(np.dot(-u1, u2))
        ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
        if ang >= min_angle:
            sites.append((g["y"], g["x"], 0.5 * (r1 + r2)))
    return sites


def knock(mask, gain=1.15, min_angle=60.0, max_sites=40):
    out = mask.astype(np.uint8).copy()
    sites = turn_sites(mask, min_angle)[:max_sites]
    for y, x, r in sites:
        cv2.circle(out, (int(round(x)), int(round(y))), max(1, int(round(r * gain))), 1, -1)
    return out > 0


if __name__ == "__main__":
    d = np.load("work/pairs/pairs.npz", allow_pickle=True)
    chars = [str(c) for c in d["chars"]]; Y = d["Y"]
    i = 3
    m = B.render_char(chars[i], "data/base/LXGWWenKai-Regular.ttf")
    m = cv2.morphologyEx(cv2.erode(m.astype(np.uint8), np.ones((1, 3), np.uint8)),
                         cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
    k = knock(m)
    print("sites", len(turn_sites(m)), "ink", m.sum(), "->", k.sum())
