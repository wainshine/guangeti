"""IDS-driven component assembly for characters without a real glyph."""
from __future__ import annotations

import json
from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
OPS = set("⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻⿼⿽")
BRACKETS = set("（）()")


def load_ids(path=ROOT / "data" / "ids" / "ids.txt"):
    ids = {}
    for line in open(path):
        if line.startswith("#"):
            continue
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3 and p[0].startswith("U+"):
            ids[chr(int(p[0][2:], 16))] = p[2]
    return ids


def parse(ids, ch, depth=0, seen=None):
    """Return a nested tree: ('leaf', ch) | (op, [children])."""
    if seen is None:
        seen = set()
    s = ids.get(ch)
    if not s or depth > 8 or ch in seen:
        return ("leaf", ch)
    seen = seen | {ch}
    parts = [c for c in s if c not in BRACKETS]
    if len(parts) < 2:
        return ("leaf", ch)
    # handle nested prefixes: e.g. "⿰氵⿱宀谷"  or "⿰⿱a b c"
    def build(tokens):
        if not tokens:
            return None
        t = tokens[0]
        if t in OPS:
            n = 3 if t in "⿲⿳" else 2
            kids = []
            rest = tokens[1:]
            for _ in range(n):
                node, rest = take(rest)
                if node is None:
                    break
                kids.append(node)
            return (t, kids), rest
        return ("leaf", t), tokens[1:]

    def take(tokens):
        if not tokens:
            return None, tokens
        t = tokens[0]
        if t in OPS:
            n = 3 if t in "⿲⿳" else 2
            kids = []
            rest = tokens[1:]
            for _ in range(n):
                node, rest = take(rest)
                if node is None:
                    break
                kids.append(node)
            return (t, kids), rest
        return ("leaf", t), tokens[1:]

    node, rest = take(parts)
    if node is None:
        return ("leaf", ch)
    # resolve leaves that themselves decompose
    def resolve(n):
        if n[0] == "leaf":
            c = n[1]
            if c != ch and c in ids and c not in seen:
                sub = parse(ids, c, depth + 1, seen)
                if sub[0] != "leaf":
                    return sub
                return ("leaf", c)
            return ("leaf", c)
        return (n[0], [resolve(k) for k in n[1]])
    return resolve(node)


class OutlineSource:
    """Provides component outlines in font units, from real glyphs or the base font."""

    def __init__(self, real_jsonl, base_ttf):
        self.real = {}
        for line in open(real_jsonl):
            r = json.loads(line)
            self.real[r["char"]] = r["contours"]
        self.font = TTFont(str(base_ttf))
        self.gs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.cache = {}

    def base_contours(self, ch):
        cp = ord(ch)
        if cp not in self.cmap:
            return None
        gname = self.cmap[cp]
        rec = RecordingPen()
        self.gs[gname].draw(rec)
        contours = []
        cur_start = None
        segs = []
        stack = []
        for op, args in rec.value:
            if op == "moveTo":
                if cur_start is not None and segs:
                    contours.append(dict(start=cur_start, segs=segs))
                cur_start = args[0]; segs = []
            elif op == "lineTo":
                segs.append(("L", args[0][0], args[0][1]))
            elif op == "qCurveTo":
                pts = list(args)
                if pts[-1] is None:  # TrueType special case
                    pts = pts[:-1] + [pts[0]]
                prev = cur_start if not segs else (segs[-1][-2], segs[-1][-1])
                for i in range(len(pts) - 1):
                    c = pts[i]
                    nxt = pts[i + 1]
                    c1 = (prev[0] + 2 / 3 * (c[0] - prev[0]), prev[1] + 2 / 3 * (c[1] - prev[1]))
                    c2 = (nxt[0] + 2 / 3 * (c[0] - nxt[0]), nxt[1] + 2 / 3 * (c[1] - nxt[1]))
                    segs.append(("C", c1[0], c1[1], c2[0], c2[1], nxt[0], nxt[1]))
                    prev = nxt
            elif op == "curveTo":
                pts = list(args)
                for i in range(0, len(pts), 3):
                    c1, c2, e = pts[i], pts[i + 1], pts[i + 2]
                    segs.append(("C", c1[0], c1[1], c2[0], c2[1], e[0], e[1]))
            elif op == "closePath":
                if cur_start is not None and segs:
                    contours.append(dict(start=cur_start, segs=segs))
                cur_start, segs = None, []
        if cur_start is not None and segs:
            contours.append(dict(start=cur_start, segs=segs))
        return contours

    def get(self, ch):
        if ch in self.cache:
            return self.cache[ch]
        c = self.real.get(ch)
        if c is None:
            c = self.base_contours(ch)
        self.cache[ch] = c
        return c


def bbox(contours):
    xs, ys = [], []
    for c in contours:
        xs.append(c["start"][0]); ys.append(c["start"][1])
        for s in c["segs"]:
            for i in range(1, len(s), 2):
                xs.append(s[i]); ys.append(s[i + 1])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def transform(contours, sx, sy, dx, dy):
    out = []
    for c in contours:
        segs = []
        for s in c["segs"]:
            vals = list(s[1:])
            segs.append((s[0],) + tuple(v * (sx if i % 2 == 0 else sy) + (dx if i % 2 == 0 else dy)
                                        for i, v in enumerate(vals)))
        out.append(dict(start=(c["start"][0] * sx + dx, c["start"][1] * sy + dy), segs=segs))
    return out


def fit(contours, box):
    """Uniformly scale into box=(x0,y0,x1,y1), centred."""
    bb = bbox(contours)
    if bb is None:
        return []
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    x0, y0, x1, y1 = box
    tw, th = x1 - x0, y1 - y0
    s = min(tw / max(1e-3, bw), th / max(1e-3, bh)) * 0.94
    sx = sy = s
    # mild stretch so that a component fills its cell better without distortion
    if tw / max(1e-3, bw) < th / max(1e-3, bh):
        sx = min(tw / max(1e-3, bw) * 0.98, s * 1.3)
    else:
        sy = min(th / max(1e-3, bh) * 0.98, s * 1.3)
    dx = x0 + (tw - bw * sx) / 2 - bb[0] * sx
    dy = y0 + (th - bh * sy) / 2 - bb[1] * sy
    return transform(contours, sx, sy, dx, dy)


def natural_size(src, node):
    if node[0] == "leaf":
        c = src.get(node[1])
        bb = bbox(c) if c else None
        return (bb[2] - bb[0], bb[3] - bb[1]) if bb else (500, 500)
    kids = [natural_size(src, k) for k in node[1]]
    if node[0] in ("⿰", "⿲"):
        return (sum(k[0] for k in kids) / len(kids), max(k[1] for k in kids))
    if node[0] in ("⿱", "⿳"):
        return (max(k[0] for k in kids), sum(k[1] for k in kids) / len(kids))
    return (max(k[0] for k in kids), max(k[1] for k in kids))


def layout(src, node, box, depth=0):
    op = node[0]
    if op == "leaf":
        c = src.get(node[1])
        return fit(c, box) if c else []
    x0, y0, x1, y1 = box
    if depth > 8:
        return []
    kids = node[1]
    if op in ("⿰", "⿱", "⿲", "⿳"):
        horiz = op in ("⿰", "⿲")
        ns = [natural_size(src, k) for k in kids]
        w = [n[0] if horiz else n[1] for n in ns]
        tot = sum(w) or 1
        frac = [max(0.18, min(0.64, wi / tot)) for wi in w]
        s = sum(frac)
        frac = [f / s for f in frac]
        out = []
        pos = x0 if horiz else y0
        span = (x1 - x0) if horiz else (y1 - y0)
        for k, f in zip(kids, frac):
            seg = span * f
            b = (pos, y0, pos + seg, y1) if horiz else (x0, pos, x1, pos + seg)
            out += layout(src, k, b, depth + 1)
            pos += seg
        return out
    if op in ("⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺"):
        outer = layout(src, kids[0], box, depth + 1)
        w, h = x1 - x0, y1 - y0
        inset = 0.16
        if op == "⿴":
            b = (x0 + w * inset, y0 + h * inset, x1 - w * inset, y1 - h * inset)
        elif op == "⿵":   # open bottom
            b = (x0 + w * inset, y0 + h * inset, x1 - w * inset, y1 - h * 0.05)
        elif op == "⿶":   # open top
            b = (x0 + w * inset, y0 + h * 0.05, x1 - w * inset, y1 - h * inset)
        elif op == "⿷":   # open right
            b = (x0 + w * inset, y0 + h * inset * 0.6, x1 - w * 0.05, y1 - h * inset * 0.6)
        elif op == "⿸":   # top-left corner
            b = (x0 + w * inset, y0 + h * inset, x1 - w * 0.05, y1 - h * 0.05)
        elif op == "⿹":   # top-right corner
            b = (x0 + w * 0.05, y0 + h * inset, x1 - w * inset, y1 - h * 0.05)
        else:              # ⿺ bottom-left
            b = (x0 + w * inset, y0 + h * 0.05, x1 - w * 0.05, y1 - h * inset)
        return outer + layout(src, kids[1], b, depth + 1)
    if op == "⿻":
        out = []
        for k in kids:
            out += layout(src, k, box, depth + 1)
        return out
    # unknown operator: stack as ⿰
    half = (x0 + x1) / 2
    return layout(src, kids[0], (x0, y0, half, y1), depth + 1) + layout(src, kids[1], (half, y0, x1, y1), depth + 1)
