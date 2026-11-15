#!/usr/bin/env python3
"""Before/after sheet for the B-Q12 re-sample (89 glyphs).

Layout per cell: [old glyph | new glyph | book crop] + char + squeeze/delta.
This is a two-glyph comparison, which the shared review sheet (one product glyph) does
not cover, so it is drawn here; sizes/typography follow the shared sheet's proportions.
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "work-b" / "v125_preresample" / "GuanGeKai-B-Regular.ttf"
NEW = ROOT / "build" / "GuanGeKai-B-Regular.ttf"
REF = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"
COLS, CELL_W, CELL_H, PER_PAGE = 6, 360, 300, 60


def glyph(path, ch, size=110):
    f = ImageFont.truetype(str(path), int(size * 0.86))
    im = Image.new("L", (size, size), 255)
    ImageDraw.Draw(im).text((size // 2, int(size * 0.92)), ch, font=f, fill=0, anchor="ms")
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", default=str(ROOT / "work-b" / "diff_resample.json"))
    ap.add_argument("--squeeze", default=str(ROOT / "work-b" / "squeeze_b.json"))
    ap.add_argument("--out", default=str(ROOT / "work-b" / "qa" / "review-b-resample"))
    a = ap.parse_args()
    ch = json.loads(Path(a.diff).read_text())["changed"]
    sq = {r["char"]: r for r in json.loads(Path(a.squeeze).read_text())["rows"]}
    plan = {p["char"]: p for p in json.loads((ROOT / "work-b" / "resample_plan2.json").read_text())}
    chosen = {json.loads(l)["label"]: json.loads(l) for l in open(ROOT / "work-b" / "chosen.jsonl")}
    ink = json.loads(Path(a.diff).read_text())["ink_delta"]
    lab = ImageFont.truetype(str(REF), 13)
    cells = {c["file"]: c for c in (json.loads(l) for l in open(ROOT / "work-b" / "cells.jsonl"))}
    rows = [{"char": c, "old": glyph(OLD, c), "new": glyph(NEW, c),
             "crop": Image.open(ROOT / "work-b" / "cells" / chosen[c]["file"]).convert("L"),
             "sq": sq.get(c, {}).get("squeeze"),
             "sq_new": plan.get(c, {}).get("new_sq"), "delta": ink.get(c, 0)} for c in ch]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pages = [rows[i:i + PER_PAGE] for i in range(0, len(rows), PER_PAGE)] or [[]]
    paths = []
    for pi, page in enumerate(pages):
        nrows = max(1, (len(page) + COLS - 1) // COLS)
        S = Image.new("RGB", (COLS * CELL_W, nrows * CELL_H), (255, 255, 255))
        d = ImageDraw.Draw(S)
        for i, r in enumerate(page):
            x, y = (i % COLS) * CELL_W, (i // COLS) * CELL_H
            d.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], outline=(215, 215, 215))
            S.paste(r["old"], (x + 8, y + 12))
            S.paste(r["new"], (x + 126, y + 12))
            c = r["crop"].copy(); c.thumbnail((110, 110))
            S.paste(c, (x + 244, y + 12))
            d.text((x + 8, y + 4), "旧", font=lab, fill=(150, 150, 150))
            d.text((x + 126, y + 4), "新", font=lab, fill=(190, 30, 30))
            d.text((x + 244, y + 4), "裁片", font=lab, fill=(150, 150, 150))
            d.text((x + 8, y + 140), r["char"], font=lab, fill=(0, 0, 0))
            s = (f"squeeze {r['sq']:.2f} -> {r['sq_new']:.2f}"
                 if r["sq"] is not None and r.get("sq_new") is not None else "")
            d.text((x + 8, y + 160), s, font=lab, fill=(0, 110, 200))
            d.text((x + 8, y + 180), f"ink {r['delta']:+.1%}", font=lab, fill=(0, 140, 0))
        p = out / f"sheet-{pi + 1}.png"
        S.save(p); paths.append(str(p))
    print(f"{len(rows)} rows -> {len(paths)} sheet(s): {', '.join(paths)}")


if __name__ == "__main__":
    main()
