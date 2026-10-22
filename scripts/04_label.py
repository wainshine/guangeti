"""Assign a Unicode character to every extracted glyph cell.

Page-level PP-OCR gives a near-perfect transcript; the canonical Four Books
text acts as spell-check and disambiguates variant forms.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
NEG = -10 ** 9


def load_reference():
    names, starts, chunks = [], [], []
    for line in open(ROOT / "data" / "reference" / "reference.txt"):
        line = line.rstrip("\n")
        if line.startswith("@"):
            name, p = line[1:].split("\t")
            names.append(name)
            starts.append(int(p))
        elif line:
            chunks.append(line)
    return "".join(chunks), names, starts


def strip_cjk(s: str) -> str:
    return "".join(ch for ch in s if CJK.match(ch))


def nw(a: str, b: str, match=1, mismatch=-1, gap=-1):
    """Global alignment a -> b, returns list of (i, j, op) and score."""
    n, m = len(a), len(b)
    H = np.full((n + 1, m + 1), NEG, dtype=np.int32)
    ptr = np.zeros((n + 1, m + 1), dtype=np.int8)
    H[0, :] = np.arange(m + 1) * gap
    H[:, 0] = np.arange(n + 1) * gap
    ptr[1:, 0] = 1
    ptr[0, 1:] = 2
    b_arr = np.frombuffer(b.encode("utf-32-le"), dtype=np.uint32)
    for i in range(1, n + 1):
        diag = H[i - 1, :-1] + np.where(b_arr == ord(a[i - 1]), match, mismatch)
        up = H[i - 1, 1:] + gap
        left = H[i, :-1] + gap
        best = np.maximum(np.maximum(diag, up), left)
        H[i, 1:] = best
        p = np.where(diag >= up, 0, 1)
        p = np.where(left > np.maximum(diag, up), 2, p)
        ptr[i, 1:] = p
    i, j = n, m
    ops = []
    while i > 0 or j > 0:
        if i == 0:
            ops.append((None, j - 1, "ins")); j -= 1
        elif j == 0:
            ops.append((i - 1, None, "del")); i -= 1
        else:
            p = ptr[i, j]
            if p == 0:
                ops.append((i - 1, j - 1, "diag")); i -= 1; j -= 1
            elif p == 1:
                ops.append((i - 1, None, "del")); i -= 1
            else:
                ops.append((None, j - 1, "ins")); j -= 1
    ops.reverse()
    return ops, int(H[n, m])


def locate(trans: str, ref: str, lo: int, hi: int, k: int = 6) -> int:
    """Best reference offset for a transcript, by k-mer voting."""
    index = defaultdict(list)
    for pos in range(lo, min(hi, len(ref) - k)):
        index[ref[pos:pos + k]].append(pos)
    votes = Counter()
    step = max(1, len(trans) // 24)
    for i in range(0, max(1, len(trans) - k), step):
        gram = trans[i:i + k]
        for pos in index.get(gram, []):
            votes[pos - i] += 1
    if not votes:
        return lo
    off, v = votes.most_common(1)[0]
    return max(lo, min(hi, off))


def main():
    cells = [json.loads(l) for l in open(ROOT / "work" / "cells.jsonl")]
    ocr = {r["page"]: r for r in (json.loads(l) for l in open(ROOT / "work" / "ocr_pages.jsonl"))}
    ref, ref_names, ref_starts = load_reference()
    print("reference", len(ref), "cells", len(cells))

    by_page = defaultdict(list)
    for c in cells:
        by_page[c["page"]].append(c)

    # ---------- map cells to OCR lines, build page transcripts ----------
    transcripts = {}
    for page, cs in by_page.items():
        lines = [dict(box=[[x * 2, y * 2] for x, y in ln["box"]], text=ln["text"], score=ln["score"])
                 for ln in ocr.get(page, {}).get("lines", [])]
        vl = [ln for ln in lines
              if (max(y for x, y in ln["box"]) - min(y for x, y in ln["box"]))
              > (max(x for x, y in ln["box"]) - min(x for x, y in ln["box"])) * 1.1]
        line_cells = defaultdict(list)
        for c in cs:
            cx, cy = (c["x0"] + c["x1"]) / 2, (c["y0"] + c["y1"]) / 2
            best, bd = None, 1e9
            for k, ln in enumerate(vl):
                xs = [q[0] for q in ln["box"]]
                ys = [q[1] for q in ln["box"]]
                x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
                if x0 - 40 <= cx <= x1 + 40 and y0 - 40 <= cy <= y1 + 40:
                    d = abs(cx - (x0 + x1) / 2)
                    if d < bd:
                        best, bd = k, d
            if best is not None:
                line_cells[best].append(c)
        page_cells = []
        for k, ln in enumerate(vl):
            group = sorted(line_cells.get(k, []), key=lambda c: c["y0"])
            if not group:
                continue
            text = strip_cjk(ln["text"])
            if len(text) == len(group):
                for c, ch in zip(group, text):
                    c["ocr"], c["ocr_score"] = ch, ln["score"]
            elif text:
                ys = [p[1] for p in ln["box"]]
                y0, y1 = min(ys), max(ys)
                centers = [(c["y0"] + c["y1"]) / 2 for c in group]
                for i, ch in enumerate(text):
                    ey = y0 + (i + 0.5) * (y1 - y0) / len(text)
                    j = int(np.argmin([abs(cy - ey) for cy in centers]))
                    if "ocr" not in group[j]:
                        group[j]["ocr"], group[j]["ocr_score"] = ch, ln["score"] * 0.9
                for c in group:
                    c.setdefault("ocr", "")
                    c.setdefault("ocr_score", 0.0)
            else:
                for c in group:
                    c["ocr"], c["ocr_score"] = "", 0.0
            page_cells.extend(group)
        for c in cs:
            c.setdefault("ocr", "")
            c.setdefault("ocr_score", 0.0)
        page_cells.sort(key=lambda c: (-c["col"], c["row"]))
        transcripts[page] = page_cells

    order = sorted(transcripts)
    # ---------- locate the beginning ----------
    firsts = "".join(c["ocr"] for p in order[:3] for c in transcripts[p])
    pos = locate(firsts, ref, 0, len(ref))
    print("start offset", pos, "context:", ref[max(0, pos - 30): pos + 40])

    # ---------- sequential alignment ----------
    import difflib
    report = []
    for page in order:
        pc = transcripts[page]
        trans = "".join(c["ocr"] for c in pc)
        if len(trans) < 10:
            for c in pc:
                c["ref"] = ""
            report.append((page, len(trans), 0.0, pos))
            continue
        starts = [max(0, pos - 80)] + [max(0, pos - 80 - b) for b in (300, 1000, 3000, 6000)]
        starts += [pos + d for d in (300, 1000, 3000, 6000)]
        if pos < len(ref) - 100:
            starts.append(max(0, locate(trans, ref, pos, len(ref)) - 80))
        best = None
        for w0 in starts:
            w0 = max(0, min(w0, len(ref) - 50))
            window = ref[w0: w0 + len(trans) + 400]
            sm = difflib.SequenceMatcher(None, trans, window, autojunk=False)
            blocks = sm.get_matching_blocks()
            matched = sum(b.size for b in blocks)
            rate = matched / len(trans)
            if best is None or rate > best[0] + 0.02:
                best = (rate, w0, window, blocks)
        rate, w0, window, blocks = best
        refidx = [None] * len(trans)
        for blk in blocks:
            for k in range(blk.size):
                refidx[blk.a + k] = w0 + blk.b + k
        # fill short replace blocks positionally
        prev_a = prev_b = 0
        for blk in blocks:
            ga, gb = blk.a - prev_a, blk.b - prev_b
            if ga == gb and ga > 0:
                for k in range(ga):
                    if refidx[prev_a + k] is None:
                        refidx[prev_a + k] = w0 + prev_b + k
            prev_a, prev_b = blk.a + blk.size, blk.b + blk.size
        if rate > 0.5:
            last_blk = blocks[-2] if len(blocks) > 1 else blocks[-1]
            pos = w0 + last_blk.b + last_blk.size
        for c, ri in zip(pc, refidx):
            c["ref"] = ref[ri] if ri is not None and ri < len(ref) else ""
        report.append((page, len(trans), round(rate, 3), pos))

    # ---------- final labels ----------
    out = []
    n_eq = n_ne = n_ocr = n_ref = n_none = 0
    for page in order:
        for c in transcripts[page]:
            ocr_ch, ref_ch = c["ocr"], c.get("ref", "")
            c["ref_agree"] = bool(ocr_ch and ref_ch and ocr_ch == ref_ch)
            if ocr_ch:
                c["label"] = ocr_ch        # OCR is the primary source
                c["label_src"] = "ocr"
            elif ref_ch:
                c["label"] = ref_ch
                c["label_src"] = "ref"
            else:
                c["label"] = ""
                c["label_src"] = "none"
            if ocr_ch and ref_ch:
                n_eq += 1 if ocr_ch == ref_ch else 0
                n_ne += 0 if ocr_ch == ref_ch else 1
            elif ocr_ch:
                n_ocr += 1
            elif ref_ch:
                n_ref += 1
            else:
                n_none += 1
            out.append(c)
    print(f"ocr==ref {n_eq}  ocr!=ref {n_ne}  ocr-only {n_ocr}  ref-only {n_ref}  none {n_none}")
    with open(ROOT / "work" / "labeled.jsonl", "w") as f:
        for c in out:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    cnt = Counter(c["label"] for c in out if c["label"])
    print("unique labels", len(cnt), "empty", sum(1 for c in out if not c["label"]))
    print(cnt.most_common(15))
    with open(ROOT / "work" / "align_report.json", "w") as f:
        json.dump(report, f)


if __name__ == "__main__":
    main()
