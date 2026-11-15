#!/usr/bin/env python3
"""B-Q11: version diff between two B-line fonts (exact outlines, not thresholds).

For a release we must be able to answer three questions with one command:
  * did any codepoint get added or removed?
  * exactly which glyphs changed (bit-identical outline comparison, not a metric)?
  * for those glyphs, how much ink moved (256 px render), and does the changed set
    match the set we intended to change?

  python3 scripts/82_version_diff_b.py \
      --old work-b/v124_backup/GuanGeKai-B-Regular.ttf \
      --new build/GuanGeKai-B-Regular.ttf \
      --expect-chars-from work-b/changed_348.txt   # optional: gate the change set

Exit codes: 0 = matches expectation / report-only, 3 = unexpected change set,
            2 = inputs unreadable (fail-closed, never a silent PASS).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = 256


def outline(font: TTFont, name: str) -> np.ndarray:
    g = font["glyf"][name]
    if g.numberOfContours <= 0:
        return np.zeros((0, 2), dtype=np.int16)
    return np.asarray(g.getCoordinates(font["glyf"])[0], dtype=np.int16)


def render(font_path: str, ch: str) -> np.ndarray:
    f = ImageFont.truetype(font_path, S)
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((S // 2, int(0.88 * S)), ch, font=f, fill=255, anchor="ms")
    return np.asarray(im) > 127


def version_of(font: TTFont) -> str:
    return (font["name"].getDebugName(5) or "").replace("Version ", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--expect-chars", default="", help="string of chars that may change")
    ap.add_argument("--expect-chars-from", default="", help="file with one char per line")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    for p in (a.old, a.new):
        if not Path(p).exists():
            print(f"FAIL: missing {p}")
            return 2
    old, new = TTFont(a.old), TTFont(a.new)
    cm_o, cm_n = old.getBestCmap(), new.getBestCmap()
    added = sorted(set(cm_n) - set(cm_o))
    removed = sorted(set(cm_o) - set(cm_n))

    changed = []
    for cp in sorted(set(cm_o) & set(cm_n)):
        if not np.array_equal(outline(old, cm_o[cp]), outline(new, cm_n[cp])):
            changed.append(chr(cp))

    ink = {}
    for ch in changed:
        o, n = render(a.old, ch), render(a.new, ch)
        ink[ch] = round(float((n.sum() - o.sum()) / max(1, o.sum())), 4)

    res = {"old": a.old, "new": a.new, "old_version": version_of(old),
           "new_version": version_of(new), "cmap_old": len(cm_o), "cmap_new": len(cm_n),
           "added": [f"U+{c:04X}" for c in added], "removed": [f"U+{c:04X}" for c in removed],
           "changed_n": len(changed), "changed": "".join(changed), "ink_delta": ink}
    print(f"version {res['old_version']} -> {res['new_version']}; cmap {len(cm_o)} -> {len(cm_n)}")
    print(f"added {len(added)}, removed {len(removed)}, glyphs changed {len(changed)}")
    if ink:
        v = np.array(list(ink.values()))
        print(f"ink delta on changed glyphs: median {np.median(v):+.1%}, "
              f"min {v.min():+.1%}, max {v.max():+.1%}")

    expect = a.expect_chars
    if a.expect_chars_from:
        expect += "".join(l.strip() for l in open(a.expect_chars_from) if l.strip())
    if a.out:
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
        print(f"-> {a.out}")
    if expect:
        extra = sorted(set(changed) - set(expect))
        missing = sorted(set(expect) - set(changed))
        if extra or missing:
            print(f"FAIL: unexpected change set; extra={''.join(extra[:20])} "
                  f"missing={''.join(missing[:20])}")
            return 3
        print(f"OK: changed set == declared set ({len(changed)})")
    elif changed:
        print("NOTE: report-only (no --expect-chars given)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
