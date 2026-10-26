"""B-line stage 3: label every character cell with a Unicode character.

OCR is the primary source (the manuscript keeps variant forms such as 爲/為, 閒/間);
the public-domain 《史記》 text is the alignment target and fills cells the OCR
dropped.  Because this copy is a *manuscript*, its character sequence and the
printed recensions differ by 脫/衍/異體, so alignment is scored, never enforced:
a page whose best match rate is low is flagged instead of silently relabelled.

  python3 scripts/54_label_b.py            # writes work-b/labeled.jsonl
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
K = 6


def strip_cjk(s: str) -> str:
    return "".join(ch for ch in s if CJK.match(ch))


def load_reference(path: Path):
    names, starts, chunks = [], [], []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("@"):
            name, p = line[1:].split("\t")
            names.append(name)
            starts.append(int(p))
        elif line:
            chunks.append(line)
    return "".join(chunks), names, starts


_INDEX = None


def build_index(ref: str, k: int = K):
    global _INDEX
    if _INDEX is None:
        idx = defaultdict(list)
        for pos in range(len(ref) - k):
            idx[ref[pos:pos + k]].append(pos)
        _INDEX = idx
    return _INDEX


def locate(trans: str, ref: str, lo: int = 0, hi: int | None = None, k: int = K) -> int:
    """Best reference offset for a transcript, by k-mer voting over [lo, hi)."""
    hi = len(ref) if hi is None else hi
    index = build_index(ref, k)
    index = {g: [p for p in ps if lo <= p < hi] for g, ps in index.items()} if lo or hi < len(ref) else index
    votes = Counter()
    step = max(1, len(trans) // 24)
    for i in range(0, max(1, len(trans) - k), step):
        gram = trans[i:i + k]
        for pos in index.get(gram, []):
            votes[pos - i] += 1
    if not votes:
        return lo
    off = votes.most_common(1)[0][0]
    return max(0, min(len(ref) - 50, off))


def align_rate(trans: str, window: str):
    sm = difflib.SequenceMatcher(None, trans, window, autojunk=False)
    blocks = sm.get_matching_blocks()
    return sum(b.size for b in blocks) / max(1, len(trans)), blocks


def page_lines(lines, min_w_ratio=1.1):
    """Vertical OCR lines (one text column each), ordered right to left."""
    vl = []
    for ln in lines:
        xs = [p[0] for p in ln["box"]]
        ys = [p[1] for p in ln["box"]]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if (y1 - y0) > (x1 - x0) * min_w_ratio:
            vl.append(dict(x0=x0, x1=x1, y0=y0, y1=y1, text=ln["text"], score=ln["score"],
                           xc=(x0 + x1) / 2.0))
    vl.sort(key=lambda l: -l["xc"])
    return vl


def attach_cells(vl, cells, max_frac=0.70):
    """Give every cell to the line whose centre is closest in x.

    Grouping by box overlap lets a too-wide detector box swallow the neighbouring
    column and shift every label after it; nearest centre plus a distance cap keeps
    the damage local and leaves genuinely unmatched cells unlabelled.
    """
    if not vl:
        return
    xs = sorted(l["xc"] for l in vl)
    pitch = float(np.median(np.diff(xs))) if len(xs) > 1 else 300.0
    lim = max_frac * pitch
    for l in vl:
        l["cells"] = []
    for c in cells:
        cx = (c["x0"] + c["x1"]) / 2.0
        d = [abs(cx - l["xc"]) for l in vl]
        j = int(np.argmin(d))
        if d[j] <= lim:
            vl[j]["cells"].append(c)
    for l in vl:
        l["cells"].sort(key=lambda c: c["y0"])


def assign_chars(vl):
    """Attach one character (and its transcript offset) to each cell of a line."""
    off = 0
    for l in vl:
        chars = strip_cjk(l["text"])
        l["chars"] = chars
        l["off"] = off
        off += len(chars)
        grp = l["cells"]
        for c in grp:
            c["ocr"], c["ocr_score"], c["pos"] = "", 0.0, None
        if not grp or not chars:
            continue
        if len(chars) == len(grp):
            for j, (c, ch) in enumerate(zip(grp, chars)):
                c["ocr"], c["ocr_score"], c["pos"] = ch, l["score"], l["off"] + j
        else:
            y0, y1 = grp[0]["y0"], grp[-1]["y1"]
            centres = [(c["y0"] + c["y1"]) / 2 for c in grp]
            for j, ch in enumerate(chars):
                ey = y0 + (j + 0.5) * (y1 - y0) / len(chars)
                k = int(np.argmin([abs(cy - ey) for cy in centres]))
                if not grp[k]["ocr"]:
                    grp[k]["ocr"], grp[k]["ocr_score"], grp[k]["pos"] = ch, l["score"] * 0.9, l["off"] + j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--reference", default=str(ROOT / "data" / "reference-b" / "reference.txt"))
    ap.add_argument("--out", default="")
    ap.add_argument("--min-align", type=float, default=0.30,
                    help="pages whose best reference match is below this are flagged")
    ap.add_argument("--variant", default=str(ROOT / "data" / "reference-b" / "variants.json"),
                    help="curated pairs 'ocr|ref' where the manuscript really writes the OCR "
                         "form and the reference is the normalised one (keep the OCR label)")
    ap.add_argument("--fix", default=str(ROOT / "data" / "reference-b" / "ocr_fix.json"),
                    help="curated map ocr_char -> ref_char for OCR modernisations/misreads; "
                         "applied to every cell, independent of page alignment")
    ap.add_argument("--coherent", type=float, default=0.90,
                    help="a page whose per-cell OCR/ref agreement is above this is trusted "
                         "for ref fallback; below it the reference mapping is considered "
                         "drifted and only --fix is applied")
    args = ap.parse_args()
    variants = json.loads(Path(args.variant).read_text()) if Path(args.variant).exists() else {}
    fixes = json.loads(Path(args.fix).read_text()) if Path(args.fix).exists() else {}
    print(f"curated: {len(variants)} variant pairs, {len(fixes)} ocr->ref fixes")

    work = Path(args.work)
    cells = [json.loads(l) for l in open(work / "cells.jsonl")]
    ocr = {r["page"]: r for r in (json.loads(l) for l in open(work / "ocr_pages.jsonl"))}
    ref, ref_names, ref_starts = load_reference(Path(args.reference))
    print(f"reference {len(ref)} chars, {len(ref_names)} sections; cells {len(cells)}")

    by_page = defaultdict(list)
    for c in cells:
        by_page[c["page"]].append(c)

    pages = sorted(by_page)
    order, page_cells = [], {}
    n_stray = 0
    rates = {}
    for page in pages:
        vl = page_lines(ocr.get(page, {}).get("lines", []))
        attach_cells(vl, by_page[page])
        assign_chars(vl)
        pc = [c for l in vl for c in l["cells"]]
        for c in by_page[page]:
            c.setdefault("ocr", "")
            c.setdefault("ocr_score", 0.0)
        # Audit 2-1: cells that fall outside every OCR line were dropped here, so they
        # could never become genuine-glyph candidates (B lost 1,716 of them, 0.36%).
        # Keep them with an empty label and an explicit source instead of vanishing.
        attached = {id(c) for c in pc}
        stray = [c for c in by_page[page] if id(c) not in attached]
        for c in stray:
            c["nolines"] = True
        pc = pc + stray
        n_stray += len(stray)
        page_cells[page] = pc
        order.append(page)

    # ---------- locate the first page, then walk the reference ----------
    head = "".join(c["ocr"] for p in order[:4] for c in page_cells[p])
    pos = locate(head, ref, 0, len(ref))
    print(f"start offset {pos}  context {ref[max(0,pos-20):pos+30]}")

    report = []
    for page in order:
        pc = page_cells[page]
        trans = "".join(c["ocr"] for c in pc)
        if len(trans) < 10:
            for c in pc:
                c["ref"] = ""
            report.append(dict(page=page, n=len(trans), rate=0.0, pos=pos, jumped=False))
            continue
        # Several windows can reach the SAME rate when the text repeats (史記 is full of
        # formulaic passages).  Taking the first best one walks the pointer backwards and
        # silently re-labels a whole page with the wrong characters, so ties are broken by
        # distance to the running position instead.
        cands = [max(0, pos + d) for d in (-3000, -1500, -600, -200, -50, 0, 50, 200, 600, 1500, 3000)]
        cands = [c for c in cands if c < len(ref) - 100]
        res = []
        for w0 in cands:
            window = ref[w0: w0 + len(trans) + 400]
            rate, blocks = align_rate(trans, window)
            res.append((rate, w0, blocks))
        brast = max(r[0] for r in res)
        near = [r for r in res if r[0] >= brast - 0.01]
        near.sort(key=lambda r: abs(r[1] + 40 - pos))
        best = (near[0][0], near[0][1], near[0][2])
        jumped = False
        if best[0] < 0.5:
            g = locate(trans, ref)
            if abs(g - pos) > 200:
                window = ref[g: g + len(trans) + 400]
                rate, blocks = align_rate(trans, window)
                if rate > best[0] + 0.10:
                    best = (rate, g, blocks)
                    jumped = True
        rate, w0, blocks = best
        refidx = [None] * len(trans)
        for blk in blocks:
            for k in range(blk.size):
                refidx[blk.a + k] = w0 + blk.b + k
        # fill positional (replace) runs of equal length
        prev_a = prev_b = 0
        for blk in blocks:
            ga, gb = blk.a - prev_a, blk.b - prev_b
            if ga == gb and ga > 0:
                for k in range(ga):
                    if refidx[prev_a + k] is None:
                        refidx[prev_a + k] = w0 + prev_b + k
            prev_a, prev_b = blk.a + blk.size, blk.b + blk.size
        if rate > 0.4:
            last = blocks[-2] if len(blocks) > 1 else blocks[-1]
            pos = w0 + last.b + last.size
        for c in pc:
            pj = c.get("pos")
            ri = refidx[pj] if (pj is not None and pj < len(refidx)) else None
            c["ref"] = ref[ri] if ri is not None and ri < len(ref) else ""
        report.append(dict(page=page, n=len(trans), rate=round(rate, 3), pos=pos, jumped=jumped))
        rates[page] = rate

    # ---------- per-page coherence of the OCR/ref mapping ----------
    coh = {}
    for page in order:
        cs = page_cells[page]
        n = sum(1 for c in cs if c.get("ocr") and c.get("ref"))
        e = sum(1 for c in cs if c.get("ocr") and c.get("ref") and c["ocr"] == c["ref"])
        coh[page] = (e / n) if n >= 30 else 0.0
    cv = np.array(list(coh.values()))
    print(f"coherence: median {np.median(cv):.3f}  p10 {np.percentile(cv,10):.3f}  "
          f"pages below {args.coherent}: {(cv < args.coherent).mean():.1%}")

    # ---------- final labels ----------
    out, n_eq, n_ne, n_ocr, n_ref, n_none = [], 0, 0, 0, 0, 0
    low = []
    n_fix = 0
    for page in order:
        rate = rates.get(page, 0.0)
        for c in page_cells[page]:
            o, r = c.get("ocr", ""), c.get("ref", "")
            c["ref_agree"] = bool(o and r and o == r)
            c["align_rate"] = rate
            c["low_align"] = bool(rate < args.min_align)
            c["coherent"] = coh.get(page, 0.0) >= args.coherent
            if not o and not r and c.get("nolines"):
                c["label"], c["label_src"] = "", "nolines"
            elif o:
                # OCR is the primary source.  Two curated tables then apply:
                #   fixes    - the recogniser's own modernisations (来/來), always
                #   variants - "ocr|ref" pairs where the manuscript really writes the
                #              OCR form, so a disagreement must NOT overwrite it
                # On a *coherent* page (>=90% of cells already agree with the reference)
                # any remaining disagreement is treated as an OCR misread and the
                # reference wins.  On a drifted page nothing but `fixes` is applied.
                if o in fixes:
                    c["label"], c["label_src"] = fixes[o], "ocr_fixed"
                    n_fix += 1
                elif c["coherent"] and r and o != r and f"{o}|{r}" not in variants:
                    c["label"], c["label_src"] = r, "ref_corrected"
                else:
                    c["label"], c["label_src"] = o, "ocr"
            elif r and c["coherent"]:
                c["label"], c["label_src"] = r, "ref"
            else:
                c["label"], c["label_src"] = "", "none"
            if o and r:
                n_eq += 1 if o == r else 0
                n_ne += 0 if o == r else 1
            elif o:
                n_ocr += 1
            elif r:
                n_ref += 1
            else:
                n_none += 1
            out.append(c)
        if rate < args.min_align:
            low.append((page, round(rate, 3), len(page_cells[page])))

    print(f"cells outside any OCR line kept as nolines: {n_stray}")
    print(f"ocr==ref {n_eq}  ocr!=ref {n_ne}  ocr-only {n_ocr}  ref-only {n_ref}  none {n_none}")
    print(f"agreement on comparable cells: {n_eq/max(1,n_eq+n_ne):.3f}")
    srcc = Counter(c["label_src"] for c in out)
    print(f"ocr fixes applied: {n_fix}")
    print("label sources:", dict(srcc))
    cnt = Counter(c["label"] for c in out if c["label"])
    print(f"unique labels {len(cnt)}; cells with label {sum(cnt.values())}")
    print("most common:", cnt.most_common(15))
    lowc = Counter()
    for c in out:
        lowc[c["low_align"]] += 1
    print("low-align cells", lowc[True], f"({lowc[True]/max(1,len(out)):.1%})")
    if low:
        print(f"low-align pages {len(low)}:", low[:30])
    out.sort(key=lambda c: (c["page"], -c["col"], c["row"]))
    op = Path(args.out) if args.out else work / "labeled.jsonl"
    with open(op, "w") as f:
        for c in out:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (work / "align_report.json").write_text(json.dumps(report, ensure_ascii=False))
    print("->", op)


if __name__ == "__main__":
    main()
