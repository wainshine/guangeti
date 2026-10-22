"""Terminal-template transfer: copy real 收筆 shapes onto synthesised glyphs.

Real glyphs → skeleton → free stroke ends → rotate patch so the outward
direction is +x → median per direction bin → template.  At generation time the
template is rotated back and max-blended into the rendered mask.
"""
from __future__ import annotations

import numpy as np
import cv2

import brush_lib as B

PATCH = 32
NBINS = 8


def _free_ends(mask):
    """Return [(y, x, dy, dx)] for every free stroke end, direction pointing outward."""
    out = []
    for f in B.glyph_frames(mask):
        pts = f["pts"]
        n = len(pts)
        if n < 4:
            continue
        k = min(6, n - 1)
        if not f.get("start_junction"):
            d = pts[0] - pts[k]
            nrm = np.linalg.norm(d) + 1e-6
            out.append((pts[0][0], pts[0][1], d[0] / nrm, d[1] / nrm))
        if not f.get("end_junction"):
            d = pts[-1] - pts[-1 - k]
            nrm = np.linalg.norm(d) + 1e-6
            out.append((pts[-1][0], pts[-1][1], d[0] / nrm, d[1] / nrm))
    return out


def _rotated_patch(mask, y, x, ang, size=PATCH):
    """Crop a `size` patch centred at (y,x), rotated so direction `ang` maps to +x."""
    half = size // 2
    y0, x0 = int(round(y)) - half, int(round(x)) - half
    pad = np.zeros((2 * half + size, 2 * half + size), np.uint8)
    ys0, xs0 = max(0, y0), max(0, x0)
    ys1, xs1 = min(mask.shape[0], y0 + 2 * half + size), min(mask.shape[1], x0 + 2 * half + size)
    if ys1 <= ys0 or xs1 <= xs0:
        return None
    pad[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0] = mask[ys0:ys1, xs0:xs1].astype(np.uint8)
    M = cv2.getRotationMatrix2D((pad.shape[1] / 2, pad.shape[0] / 2), np.degrees(ang), 1.0)
    rot = cv2.warpAffine(pad * 255, M, (pad.shape[1], pad.shape[0]), flags=cv2.INTER_LINEAR)
    cy, cx = pad.shape[0] // 2, pad.shape[1] // 2
    return rot[cy - half:cy + half, cx - half:cx + half] > 127


def build_templates(masks, size=PATCH, nbins=NBINS):
    """Median binary template per outward-direction bin (angle in [-pi, pi])."""
    acc: dict[int, list[np.ndarray]] = {b: [] for b in range(nbins)}
    for m in masks:
        for (y, x, dy, dx) in _free_ends(B.as_mask(m)):
            ang = np.arctan2(dy, dx)
            b = int(((ang + np.pi) / (2 * np.pi) * nbins)) % nbins
            p = _rotated_patch(B.as_mask(m), y, x, ang, size)
            if p is not None and p.sum() > 20:
                acc[b].append(p)
    tmpl = {}
    for b, ps in acc.items():
        if len(ps) < 20:
            continue
        tmpl[b] = (np.median(np.stack(ps).astype(np.float32), axis=0) > 0.5)
    return tmpl, {b: len(ps) for b, ps in acc.items()}


def apply_templates(mask, tmpl, nbins=NBINS, size=PATCH, strength=1.0):
    """Rotate each bin template back onto every free end of `mask`."""
    mask = B.as_mask(mask).copy()
    out = mask.astype(np.uint8)
    for (y, x, dy, dx) in _free_ends(mask):
        ang = np.arctan2(dy, dx)
        b = int(((ang + np.pi) / (2 * np.pi) * nbins)) % nbins
        if b not in tmpl:
            continue
        t = tmpl[b].astype(np.uint8)
        half = size // 2
        big = np.zeros((size * 2, size * 2), np.uint8)
        big[half:half + size, half:half + size] = t
        M = cv2.getRotationMatrix2D((size, size), -np.degrees(ang), 1.0)
        rot = cv2.warpAffine(big * 255, M, (size * 2, size * 2), flags=cv2.INTER_LINEAR) > 127
        ys, xs = np.nonzero(rot)
        ys = ys - size + int(round(y))
        xs = xs - size + int(round(x))
        ok = (ys >= 0) & (ys < out.shape[0]) & (xs >= 0) & (xs < out.shape[1])
        out[ys[ok], xs[ok]] = 1
    return out > 0
