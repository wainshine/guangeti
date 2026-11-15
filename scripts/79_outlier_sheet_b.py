#!/usr/bin/env python3
"""Sheet for the 74 chosen glyphs that disagree with their own label's other samples.

Row: [chosen sample | up to 3 other samples of the same label | reference glyph of the label]
"""
import json, collections, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"
W, H, PER = 520, 150, 30


def main():
    rows = json.load(open(ROOT / "work-b" / "chosen_outliers.json"))
    by = collections.defaultdict(list)
    for l in open(ROOT / "work-b" / "labeled.jsonl"):
        r = json.loads(l)
        if r.get("label"): by[r["label"]].append(r["file"])
    rnd = random.Random(0)
    lab = ImageFont.truetype(str(REF), 14)
    out = ROOT / "work-b" / "qa" / "review-b-outliers"; out.mkdir(parents=True, exist_ok=True)
    pages = [rows[i:i + PER] for i in range(0, len(rows), PER)]
    for pi, page in enumerate(pages):
        S = Image.new("RGB", (W, H * len(page)), (255, 255, 255)); d = ImageDraw.Draw(S)
        for i, r in enumerate(page):
            y = i * H
            d.rectangle([0, y, W - 1, y + H - 1], outline=(220, 220, 220))
            cur = Image.open(ROOT / "work-b" / "masks" / r["file"]).convert("L")
            cur.thumbnail((110, 110)); S.paste(cur, (8, y + 20))
            d.text((8, y + 2), "chosen", font=lab, fill=(190, 30, 30))
            others = [f for f in by[r["char"]] if f != r["file"]]
            if len(others) > 3: others = rnd.sample(others, 3)
            for k, f in enumerate(others[:3]):
                im = Image.open(ROOT / "work-b" / "masks" / f).convert("L")
                im.thumbnail((110, 110)); S.paste(im, (136 + k * 118, y + 20))
            d.text((136, y + 2), "others", font=lab, fill=(0, 110, 200))
            f2 = ImageFont.truetype(str(ROOT / "build" / "GuanGeKai-B-Real.ttf"), 60)
            g = Image.new("L", (70, 70), 255)
            ImageDraw.Draw(g).text((35, 64), r["char"], font=f2, fill=0, anchor="ms")
            S.paste(g, (W - 90, y + 40))
            d.text((W - 90, y + 2), "label", font=lab, fill=(0, 0, 0))
            d.text((8, y + 132), f"{r['char']}  IoU {r['iou_median']:.2f}  n={r['n_others']+1}", font=lab, fill=(90, 90, 90))
        p = out / f"sheet-{pi + 1}.png"; S.save(p); print(p)


if __name__ == "__main__":
    main()
