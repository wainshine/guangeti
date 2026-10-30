"""C-line stage 3: cut character cells from the OCR line structure.

Why not cut on a grid:  the 大典 mixes 大字 (a 字头 filling the whole 朱丝栏 column)
and 小字双行 (two half-width rows of notes) *within the same column*, so a single
column pitch is wrong by a factor of two somewhere on almost every page.  The two
OCR passes already find the line boxes, and their widths tell the two sizes apart
cleanly (big line ~= full column, small line ~= half column).  So the line comes from
OCR and only the *character boundaries along y* are cut here, with the OCR character
count as a hard constraint (dynamic programming over low-ink rows).

Each cell is scored for cut quality; anything suspicious is marked, and `94_label_c.py`
decides whether to keep it.  Cells are never silently repaired: a bad cut stays bad
and is dropped later, because a half character with a confident label is worse than
no character.

Outputs under work-c/:
  cells/   gray crop, everything except this cell's ink painted white
  masks/   binary mask of exactly this cell's components
  cells.jsonl   one row per cell (geometry, OCR label, quality flags)

  python3 scripts/93_segment_c.py --workers 6
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yongle_page import (_white_corridor, assign_components, detect_rules,  # noqa: E402
                         ink_mask, red_masks)

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
OUT = WORK  # set by --out-dir; cell/mask/cells.jsonl go here
FRAG_FILTER = False
CENTER_GATE = False
GAP_MID = False
CENTER_FRAC = 0.18
MERGE_TRIM = False  # opt-in: the "far component" rule damaged multi-component glyphs (see v3 audit)
CORPUS = ROOT / "永乐大典美国藏本"
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
PAD = 8


def rotate_by(rgb: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.03:
        return rgb
    h, w = rgb.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(rgb, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def cut_line(ink: np.ndarray, L: int, R: int, y0: int, y1: int, N: int) -> list[int]:
    """Cut [y0,y1) into N character cells on low-ink rows (DP)."""
    if N < 1:
        return [y0, y1]
    p = ink[y0:y1, L:R].sum(1).astype(np.float32)
    p = np.convolve(p, np.ones(3) / 3, mode="same")
    h = len(p)
    if h < 5:
        return [int(round(y0 + k * h / N)) for k in range(N + 1)]
    step = h / N
    pmax = max(1.0, float(p.max()))
    low = p < max(2.0, 0.12 * pmax)
    cands, s = [], None
    for y, v in enumerate(low):
        if v and s is None:
            s = y
        if not v and s is not None:
            seg = np.arange(s, y)
            cands.append(int((s + y - 1) // 2) if GAP_MID else int(seg[np.argmin(p[seg])]))
            s = None
    if s is not None:
        seg = np.arange(s, len(p))
        cands.append(int((s + len(p) - 1) // 2) if GAP_MID else int(seg[np.argmin(p[seg])]))
    cands = sorted(set([0] + cands + [h]))
    if len(cands) < N + 1:
        return [int(round(y0 + k * h / N)) for k in range(N + 1)]
    C = len(cands)
    INF = 1e18
    dp = np.full((N + 1, C), INF)
    prev = np.full((N + 1, C), -1, int)
    dp[0, 0] = 0.0
    lo, hi = 0.45 * step, 1.75 * step
    for k in range(1, N + 1):
        for j in range(1, C):
            y = cands[j]
            best = None
            for i in range(j - 1, -1, -1):
                Ln = y - cands[i]
                if Ln < lo:
                    continue
                if Ln > hi:
                    break
                if dp[k - 1, i] >= INF:
                    continue
                c = dp[k - 1, i] + (p[y] if y < h else 0.0) / pmax \
                    + 0.35 * ((Ln - step) / step) ** 2
                if best is None or c < best[0]:
                    best = (c, i)
            if best:
                dp[k, j] = best[0]
                prev[k, j] = best[1]
    if dp[N, C - 1] >= INF:
        return [int(round(y0 + k * h / N)) for k in range(N + 1)]
    cs = [C - 1]
    for k in range(N, 0, -1):
        cs.append(int(prev[k, cs[-1]]))
    cs = sorted(set(cs))
    if len(cs) != N + 1:
        return [int(round(y0 + k * h / N)) for k in range(N + 1)]
    return [y0 + cands[c] for c in cs]


def extend_y(ink: np.ndarray, x0: int, x1: int, by0: int, by1: int, lim: int):
    p = ink[:, x0:x1].sum(1).astype(np.float32)
    h = len(p)
    y0, y1 = int(by0), int(by1)
    k = 0
    while y0 > 1 and p[y0 - 1] > 0 and k < lim:
        y0 -= 1
        k += 1
    k = 0
    while y1 < h - 1 and p[y1] > 0 and k < lim:
        y1 += 1
        k += 1
    return max(0, y0), min(h, y1)


def dedupe_boxes(lines):
    """Drop duplicated / contained OCR boxes from one page."""
    out = []
    for ln in sorted(lines, key=lambda l: -((l["box"][2][0] - l["box"][0][0])
                                            * (l["box"][2][1] - l["box"][1][1]))):
        xs = [p[0] for p in ln["box"]]
        ys = [p[1] for p in ln["box"]]
        bx = (min(xs), min(ys), max(xs), max(ys))
        keep = True
        for o in out:
            ox, oy, ox1, oy1 = o["xyxy"]
            ix = max(0, min(bx[2], ox1) - max(bx[0], ox))
            iy = max(0, min(bx[3], oy1) - max(bx[1], oy))
            if ix * iy > 0.6 * max(1.0, (bx[2] - bx[0]) * (bx[3] - bx[1])):
                keep = False
                break
        if keep:
            ln["xyxy"] = bx
            out.append(ln)
    return out


def segment_one(task):
    key, pdf_name, idx, page, dpi, scale, angle, stats = task
    cv2.setNumThreads(1)
    err = None
    rows = []
    stat = dict(key=key, pages=1, cells=0, skip="", pitch=0.0, wmed=0.0, lines=0)
    try:
        doc = pymupdf.open(CORPUS / pdf_name)
        pix = doc[page].get_pixmap(dpi=dpi)
        rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n)[:, :, :3].copy()
        doc.close()
        rgb = rotate_by(rgb, angle)
        ink = ink_mask(rgb, dpi=dpi)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        rules = detect_rules(rgb, dpi=dpi)
        lines = dedupe_boxes(load_lines(key))
        if len(rules["lines"]) < 2 or not lines:
            stat["skip"] = "no_rules"
            return key, rows, err, stat
        Ls = rules["lines"]
        P = float(rules["pitch"])
        x0f, y0f, x1f, y1f = rules["frame"]
        # per-column sub-row split
        splits = {}
        for ci in range(len(Ls) - 1):
            L, R = Ls[ci], Ls[ci + 1]
            if R - L < P * 0.45:
                continue
            col = ink[max(0, y0f):max(1, y1f), L + 2:R - 2]
            r = np.flatnonzero(col.sum(1) > 0)
            if len(r) < 10:
                splits[ci] = None
                continue
            t0 = max(0, y0f) + int(r[0])
            t1 = max(0, y0f) + int(r[-1]) + 1
            # two-column split: the gutter must be a *white corridor* across the
            # whole y-band, not merely the x with the least ink.  Using the ink
            # minimum alone put the split inside a wide glyph (渤 lost its 氵) and
            # cut the character in half.
            corr = _white_corridor(ink, t0, t1, ink.shape[1])
            a = int(L + 0.26 * (R - L)); b = int(L + 0.74 * (R - L)) + 1
            if b <= a:
                splits[ci] = None
                continue
            k = int(np.argmax(corr[a:b]))
            splits[ci] = (a + k, float(corr[a + k]))
        # ---- gate: the red-rule grid must agree with the OCR line geometry.
        # Maps and tables (e.g. 卷10949 的 江西地圖) have a few stray rules and lots of
        # scattered text; without this check they would be cut with a column pitch
        # that has nothing to do with the characters.
        widths = [(ln["xyxy"][2] - ln["xyxy"][0]) for ln in lines]
        wmed = float(np.median(widths)) if widths else 0.0
        if wmed < 0.20 * P or wmed > 1.35 * P:
            return key, [], None, dict(key=key, pages=1, cells=0, skip="geometry",
                                       pitch=round(P, 1), wmed=round(wmed, 1),
                                       lines=len(lines))
        cells = []
        for li, ln in enumerate(lines):
            bx0, by0, bx1, by1 = [v * scale for v in ln["xyxy"]]
            ch = [c for c in ln["text"] if CJK.match(c)]
            N = len(ch)
            if N == 0:
                continue
            if (bx1 - bx0) > 1.8 * P or (bx1 - bx0) > 1.4 * (by1 - by0):
                continue                       # horizontal title / page number
            cx = (bx0 + bx1) / 2
            ci = int(np.argmin([abs(cx - (Ls[i] + Ls[i + 1]) / 2)
                                for i in range(len(Ls) - 1)]))
            L, R = Ls[ci], Ls[ci + 1]
            full = (bx1 - bx0) > 0.62 * (R - L)
            sp = splits.get(ci)
            yy0 = max(0, int(by0)); yy1 = min(ink.shape[0], int(by1))
            if full and sp is not None:
                # a real 大字 must carry ink on both sides of the gutter; a
                # half-width small line whose OCR box is too wide is not full.
                mid = sp[0]
                l = int(ink[yy0:yy1, L:mid].sum()); r = int(ink[yy0:yy1, mid:R].sum())
                if min(l, r) < 0.15 * max(1, max(l, r)):
                    full = False
            if (not full) and sp is not None and sp[1] > 0.45:
                mid = sp[0]
                # validation: the cut must be a clean vertical corridor for *this
                # line*, not just for the column as a whole; otherwise the split
                # runs through a glyph (鮓 lost 乍, 渤 lost 氵).
                leak = float(ink[yy0:yy1, max(0, mid - 2):mid + 3].mean())
                if leak > 0.02:
                    sp = None
            if full:
                x0, x1 = L, R
            elif sp is not None and sp[1] > 0.45:
                mid = sp[0]
                if cx < mid:
                    x0, x1 = L, mid
                else:
                    x0, x1 = mid, R
                # one-sided small text: if the chosen half is empty and the other
                # carries the ink, use the other half (the empty half stays empty).
                a0 = int(ink[yy0:yy1, x0:x1].sum())
                o0, o1 = (mid, R) if x0 == L else (L, mid)
                b0 = int(ink[yy0:yy1, o0:o1].sum())
                if a0 < 0.20 * max(1, b0):
                    x0, x1 = o0, o1
            else:
                x0 = max(L, int(bx0 - 0.10 * P))
                x1 = min(R, int(bx1 + 0.10 * P))
            if x1 - x0 < 0.22 * P:
                continue
            step = (by1 - by0) / N
            yy0, yy1 = extend_y(ink, x0, x1, by0, by1, int((0.15 if CENTER_GATE else 0.55) * step))
            if yy1 - yy0 < 8:
                continue
            cuts = cut_line(ink, x0, x1, yy0, yy1, N)
            for k in range(N):
                a, b = cuts[k], cuts[k + 1]
                if b - a < 6:
                    continue
                cells.append(dict(
                    key=key, book_idx=idx, page=page, col=ci, li=li, sub=k, merged=False,
                    slot=(int(a), int(b)), slot_x=(int(x0), int(x1)),
                    x0=int(x0), y0=int(a), x1=int(x1), y1=int(b),
                    pitch=round(P, 1), cpitch=round(float(step), 1),
                    big=bool(full), n_line=N, line_score=round(float(ln["score"]), 3),
                    label=ch[k], lin_xyxy=[int(v * scale) for v in ln["xyxy"]]))

        # ---- assign whole connected components, then build the mask from exactly
        # those components.  Cropping the slot rectangle instead would let the
        # neighbour's stroke (or a 句读 mark) into the glyph.
        if CENTER_GATE:
            y_core = [(c["y0"] + CENTER_FRAC * max(1.0, float(c["cpitch"])),
                       c["y1"] - CENTER_FRAC * max(1.0, float(c["cpitch"]))) for c in cells]
        else:
            y_core = None
        lab = assign_components(ink, cells, P, min_area=max(24.0, 0.00012 * P * P),
                                y_core=y_core)
        keep = []
        for c in cells:
            ids = c.get("comp_ids") or []
            if not ids:
                continue
            ix0, iy0, ix1, iy1 = c["bbox"]
            w, h = ix1 - ix0, iy1 - iy0
            cp = max(1.0, float(c["cpitch"]))
            if w < 12 or h < 12:
                continue
            if w < 0.30 * cp or h < 0.30 * cp:
                continue                       # too small to vectorise; drop, don't upscale
            m = np.isin(lab[iy0:iy1, ix0:ix1], ids)
            if FRAG_FILTER:
                # drop stray components that sit entirely outside the main glyph and far
                # from it: a neighbour line's top, a 句读 mark, a page-edge speck.  A dot
                # or a separate 撇/捺 overlaps the main bbox, or sits within 0.12·size, so
                # it is kept.
                ncc, lm, stc, _cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
                if ncc > 2:
                    areas = stc[1:, cv2.CC_STAT_AREA]
                    main = 1 + int(np.argmax(areas))
                    mb = stc[main]
                    tot = float(m.sum())
                    H0, W0 = m.shape
                    drop = []
                    for j in range(1, ncc):
                        if j == main or stc[j, cv2.CC_STAT_AREA] >= 0.20 * tot:
                            continue
                        bx, by, bw, bh = stc[j, :4]
                        dx = max(mb[0] - (bx + bw), bx - (mb[0] + mb[2]), 0)
                        dy = max(mb[1] - (by + bh), by - (mb[1] + mb[3]), 0)
                        if (dx * dx + dy * dy) ** 0.5 > 0.12 * max(H0, W0):
                            drop.append(j)
                    if drop:
                        m = m & ~np.isin(lm, drop)
            bh = iy1 - iy0
            if MERGE_TRIM and (c.get("merged") or bh > 1.30 * cp):
                # one cell holding two characters: keep only the main y-cluster
                cc, lm, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
                if cc > 2:
                    runs = []
                    on = False
                    for yy, vv in enumerate(m.any(1)):
                        if vv and not on: st0 = yy; on = True
                        if not vv and on: runs.append((st0, yy)); on = False
                    if on: runs.append((st0, m.shape[0]))
                    if len(runs) >= 2:
                        # main run = largest ink area
                        areas = [(int(m[a:b].sum()), a, b) for a, b in runs]
                        _, a0, b0 = max(areas)
                        keep_comps = [j for j in range(1, cc)
                                      if a0 - 2 <= cen[j][1] <= b0 + 2]
                        if keep_comps:
                            m = np.isin(lm, keep_comps)
                            ys, xs = np.nonzero(m)
                            if len(ys):
                                m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                                ix0, iy0 = ix0 + int(xs.min()), iy0 + int(ys.min())
                                ix1, iy1 = ix0 + m.shape[1], iy0 + m.shape[0]
                                c["merged"] = False
            # ink touching the cut line = the DP cut went through a character
            a, b = c["slot"]
            sl = c["slot_x"]
            top = np.isin(lab[max(0, a):min(lab.shape[0], a + 3), sl[0]:sl[1]], ids).sum()
            bot = np.isin(lab[max(0, b - 3):min(lab.shape[0], b), sl[0]:sl[1]], ids).sum()
            edge = float((top + bot) / max(1, int(m.sum())))
            cropx0, cropy0 = max(0, ix0 - PAD), max(0, iy0 - PAD)
            cropx1, cropy1 = min(gray.shape[1], ix1 + PAD), min(gray.shape[0], iy1 + PAD)
            mask_full = np.zeros((cropy1 - cropy0, cropx1 - cropx0), np.uint8)
            mask_full[(iy0 - cropy0):(iy1 - cropy0), (ix0 - cropx0):(ix1 - cropx0)] = \
                m.astype(np.uint8) * 255
            cell_gray = np.full_like(mask_full, 255)
            src = gray[cropy0:cropy1, cropx0:cropx1]
            cell_gray[mask_full > 0] = src[mask_full > 0]
            name = f"{key}_c{c['col']:02d}_l{c['li']:02d}_s{c['sub']:03d}.png"
            Image.fromarray(cell_gray).save(OUT / "cells" / name, compress_level=6)
            Image.fromarray(mask_full).save(OUT / "masks" / name, compress_level=6)
            c.update(file=name, x0=int(ix0), y0=int(iy0), x1=int(ix1), y1=int(iy1),
                     w=w, h=h, cx0=int(cropx0), cy0=int(cropy0),
                     edge=round(edge, 4), fill=round(float(m.mean()), 4))
            keep.append(c)
        cells = keep
        for c in cells:
            cp = max(1.0, c["cpitch"])
            c["bad"] = bool(c["edge"] > 0.10 or c["w"] > 1.25 * cp
                            or c["h"] > 1.45 * cp or c["h"] < 0.32 * cp
                            or c.get("merged", False) or c["fill"] < 0.02)
        rows = cells
        stat = dict(key=key, pages=1, cells=len(cells), skip="", pitch=round(P, 1),
                    wmed=round(wmed, 1), lines=len(lines))
    except Exception:
        import traceback
        err = traceback.format_exc()
    return key, rows, err, stat


_LINES = {}


def load_lines(key: str):
    if key not in _LINES:
        _LINES[key] = None
    return _LINES[key]


def build_line_index(path: Path):
    idx = {}
    for line in open(path):
        r = json.loads(line)
        idx[r["key"]] = r["lines"]
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keys", default="")
    ap.add_argument("--out-dir", default="", help="write cells/masks/cells.jsonl here (default work-c)")
    ap.add_argument("--merge-trim", action="store_true",
                    help="for a cell holding two characters, keep only the main y-cluster")
    ap.add_argument("--center-frac", type=float, default=0.18,
                    help="fraction of cpitch trimmed at each cell end before component assignment")
    ap.add_argument("--gap-mid", action="store_true",
                    help="put cuts at the middle of the low-ink run, not its minimum")
    ap.add_argument("--center-gate", action="store_true",
                    help="assign components by centroid inside the slot's central 64%%; "
                         "reduces previous/next glyph leakage (the 一 bug)")
    ap.add_argument("--fragment-filter", action="store_true",
                    help="drop small components far from the main one (OFF by default: it "
                         "removed 氵/乍-like parts of legitimate multi-component glyphs)")
    args = ap.parse_args()
    global OUT, FRAG_FILTER, CENTER_GATE, GAP_MID, CENTER_FRAC, MERGE_TRIM
    FRAG_FILTER = args.fragment_filter
    CENTER_GATE = args.center_gate
    GAP_MID = args.gap_mid
    CENTER_FRAC = args.center_frac
    MERGE_TRIM = args.merge_trim
    OUT = Path(args.out_dir) if args.out_dir else WORK
    (OUT / "cells").mkdir(parents=True, exist_ok=True)
    (OUT / "masks").mkdir(parents=True, exist_ok=True)
    stats = [json.loads(l) for l in open(WORK / "page_stats.jsonl")]
    ocr = build_line_index(WORK / "ocr_v6.jsonl")
    todo = [s for s in stats if s["content"] == "text" and s["key"] in ocr]
    if args.keys:
        keep = set(args.keys.split(","))
        todo = [s for s in todo if s["key"] in keep]
    if args.limit:
        todo = todo[:args.limit]
    print(f"pages {len(todo)}", flush=True)
    ocr_scale = args.dpi / 150.0
    tasks = [(s["key"], s["book"], s["book_idx"], s["page"], args.dpi, ocr_scale,
              s["angle"], s) for s in todo]
    t0 = time.time()
    all_rows = []
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    # the OCR index is rebuilt once per worker through the initializer
    seg_stats = []
    with ctx.Pool(args.workers, initializer=_init, initargs=(str(WORK / "ocr_v6.jsonl"),)) as pool:
        for i, (key, rows, err, st) in enumerate(pool.imap_unordered(segment_one, tasks)):
            if err:
                print(f"[ERR] {key}: {err}", flush=True)
            if st:
                seg_stats.append(st)
            all_rows.extend(rows)
            if i % 25 == 0:
                print(f"{i}/{len(tasks)} pages, {len(all_rows)} cells, "
                      f"{time.time()-t0:.0f}s", flush=True)
    all_rows.sort(key=lambda r: (r["book_idx"], r["page"], r["col"], r["sub"]))
    with open(OUT / "cells.jsonl", "w") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(OUT / "seg_stats.jsonl", "w") as f:
        for st in sorted(seg_stats, key=lambda x: x["key"]):
            f.write(json.dumps(st, ensure_ascii=False) + "\n")
    from collections import Counter
    sk = Counter(st.get("skip") for st in seg_stats)
    print(f"done {len(all_rows)} cells from {len(todo)} pages in {time.time()-t0:.0f}s; "
          f"skipped {dict(sk)}")


def _init(path):
    global _LINES
    _LINES = build_line_index(Path(path))


if __name__ == "__main__":
    main()
