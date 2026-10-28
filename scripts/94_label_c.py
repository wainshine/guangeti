"""C-line stage 4: turn two OCR witnesses into silver labels.

There is no reference transcription for these volumes (识典古籍 stops at 卷7602, our
corpus is 6831–19792), so a label is only accepted when independent witnesses agree:

  A  PP-OCRv6 on the colour page
  B  PP-OCRv5 on the red-removed, contrast-stretched page

Both are line-level OCR, so the comparison is done on the *line text*: for every A
line, the B lines covering the same box are concatenated and aligned against A's
string.  A cell inherits `agree_ab` when its character lands on an identical
character in B.

Everything that cannot be confirmed is kept with `label=""` and a reason, never
guessed: a clean but small silver set is worth more than a large noisy one, because
every wrong label becomes a wrong glyph in the shipped font.  Visual clustering
(stage 4b) and cell-level re-recognition (stage 4c) then add or remove confidence in
separate columns of the same record, so the final thinning rule lives in one place.

  python3 scripts/94_label_c.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib.util import module_from_spec, spec_from_file_location  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
BLOCK = (0x4E00, 0x9FFF)


def load_lines(path: Path):
    idx = {}
    for line in open(path):
        r = json.loads(line)
        idx[r["key"]] = r["lines"]
    return idx


def load_dedupe():
    spec = spec_from_file_location("segc", ROOT / "scripts" / "93_segment_c.py")
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.dedupe_boxes


def cjk(s: str) -> str:
    return "".join(c for c in s if CJK.match(c))


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / max(1.0, ua)


def box_of(ln):
    xs = [p[0] for p in ln["box"]]
    ys = [p[1] for p in ln["box"]]
    return (min(xs), min(ys), max(xs), max(ys))


def match_text(a_text: str, b_lines: list) -> list:
    """Map each A character to the aligned B character ('' when unmapped)."""
    out = [""] * len(a_text)
    if not b_lines:
        return out
    b_text = "".join(cjk(ln["text"]) for ln in b_lines)
    if not b_text:
        return out
    sm = SequenceMatcher(None, a_text, b_text, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                out[i1 + k] = b_text[j1 + k]
        elif tag == "replace" and (i2 - i1) == (j2 - j1):
            # a one-for-one substitution is a genuine disagreement (not a dropped
            # character), so it must be *recorded* as the B reading, not left empty;
            # otherwise `conflict` can never fire and every label looks confirmed
            for k in range(i2 - i1):
                out[i1 + k] = b_text[j1 + k]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v6", default=str(WORK / "ocr_v6.jsonl"))
    ap.add_argument("--v5", default=str(WORK / "ocr_v5.jsonl"))
    ap.add_argument("--out", default=str(WORK / "labeled.jsonl"))
    ap.add_argument("--min-line-iou", type=float, default=0.25)
    args = ap.parse_args()
    dedupe_boxes = load_dedupe()
    v6 = load_lines(Path(args.v6))
    v5 = load_lines(Path(args.v5))
    cells = [json.loads(l) for l in open(WORK / "cells.jsonl")]
    print(f"cells {len(cells)}; pages v6 {len(v6)} v5 {len(v5)}")

    by_page = defaultdict(list)
    for c in cells:
        by_page[c["key"]].append(c)
    # A-line-by-A-line matching is done once per page
    line_map = {}          # (key, li) -> list of v5 chars per A char
    stats = Counter()
    for key, cs in by_page.items():
        la = dedupe_boxes(v6.get(key, []))
        lb = v5.get(key, [])
        if not la:
            continue
        boxes_b = [(box_of(l), l) for l in lb]
        for li, ln in enumerate(la):
            ax = box_of(ln)
            cand = [l for (bx, l) in boxes_b
                    if iou(ax, bx) >= args.min_line_iou
                    or (bx[0] + bx[2]) / 2 >= ax[0] - 20
                    and (bx[0] + bx[2]) / 2 <= ax[2] + 20
                    and (bx[1] + bx[3]) / 2 >= ax[1] - 20
                    and (bx[1] + bx[3]) / 2 <= ax[3] + 20]
            cand.sort(key=lambda l: (box_of(l)[1], -box_of(l)[0]))
            a_text = cjk(ln["text"])
            line_map[(key, li)] = match_text(a_text, cand)
            if cand:
                stats["lines_with_b"] += 1
            else:
                stats["lines_without_b"] += 1

    # Pages carrying 篆/隸 forms are excluded as pages.  The obvious marker — the
    # running title 永樂大典卷之… — is useless: it is printed in the margin of body
    # leaves too (73 of the first 1,040 pages carried it for that reason alone).
    # The workable marker is the 篆 label itself (and 隸 where paired with 書), because
    # those pages are the character-origin (六書) showcases; a glyph-level seal-script
    # classifier would be a project of its own.
    front = set()
    for key, lines in v6.items():
        txt = "".join(cjk(l["text"]) for l in lines)
        if "篆" in txt or (("隸" in txt or "隷" in txt) and "書" in txt):
            front.add(key)
    print(f"seal/clerical pages excluded: {len(front)}")

    out = []
    n_agree = n_conflict = n_nob = n_oob = 0
    src = Counter()
    for c in cells:
        key, li, k = c["key"], c["li"], c["sub"]
        if key in front:
            c["label"], c["label_src"] = "", "front_matter"
            c["v5_char"] = ""
            src["front_matter"] += 1
            out.append(c)
            continue
        mapped = line_map.get((key, li))
        v5c = ""
        if mapped is not None and k < len(mapped):
            v5c = mapped[k]
        lab = c["label"]
        c["v6_char"] = lab
        c["v5_char"] = v5c
        c["agree_ab"] = bool(v5c and v5c == lab)
        if not lab:
            src["no_a"] += 1
            c["label_src"] = "no_a"
            c["label"] = ""
            out.append(c)
            continue
        cp = ord(lab)
        if not (BLOCK[0] <= cp <= BLOCK[1]):
            n_oob += 1
            c["label_src"] = "out_of_block"
            c["label"] = ""
            out.append(c)
            continue
        if c["agree_ab"]:
            n_agree += 1
            src["ab"] += 1
            c["label_src"] = "ab"
        elif v5c:
            n_conflict += 1
            src["conflict"] += 1
            c["label_src"] = "conflict"
            c["label"] = ""
        else:
            n_nob += 1
            src["a_only"] += 1
            c["label_src"] = "a_only"
        out.append(c)

    with open(args.out, "w") as f:
        for c in out:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    rep = dict(cells=len(out), agree_ab=n_agree, conflict=n_conflict,
               a_only=n_nob, out_of_block=n_oob,
               line_with_b=stats["lines_with_b"], line_without_b=stats["lines_without_b"],
               label_sources=dict(src))
    (WORK / "label_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    cnt = Counter(c["label"] for c in out if c["label"])
    print(f"unique labels {len(cnt)}; cells labelled {sum(cnt.values())}")
    print("most common:", cnt.most_common(12))
    print("->", args.out)


if __name__ == "__main__":
    main()
