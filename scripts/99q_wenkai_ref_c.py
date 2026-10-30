"""Build the per-character WenKai reference table used by the cluster pilot.

For each C label, render WenKai at 512 px, take the ink bbox, and record
  ink_density = mask_pixels / bbox_area
  aspect      = bbox_w / bbox_h
Missing labels are recorded as null (ref_missing), never used as a hard gate.
"""
from __future__ import annotations
import json, collections
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = 512
FONT = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S)


def main():
    labels = set()
    for l in open(ROOT / "work-c/exp/v3d2/cells.jsonl"):
        r = json.loads(l)
        if r.get("label"): labels.add(r["label"])
    out = {}
    for ch in sorted(labels):
        im = Image.new("L", (S, S), 0)
        ImageDraw.Draw(im).text((0, 450), ch, fill=255, font=FONT, anchor="ls")
        m = np.array(im) > 127
        ys, xs = np.nonzero(m)
        if not len(ys):
            out[ch] = None; continue
        w = int(xs.max() - xs.min() + 1); h = int(ys.max() - ys.min() + 1)
        out[ch] = {"density": round(float(m.sum()) / max(1, w * h), 4),
                   "aspect": round(w / max(1, h), 3), "w": w, "h": h}
    p = ROOT / "work-c/wenkai_ref.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    miss = sum(1 for v in out.values() if v is None)
    print(f"labels {len(out)} missing {miss} -> {p}")


if __name__ == "__main__":
    main()
