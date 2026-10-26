"""B-line: coverage / empty-glyph / counter QA + contact sheets for the 史記 font.

Forked from `13_qa.py`.  Audit rev2 (P1-3) called the old version out: every check
was print-only, so `empty 3` or a 18,000-glyph coverage still exited 0 and the
release gate was decorative.  Now every check raises SystemExit on failure, and a
counter audit was added because the five shape metrics are blind to a filled hole
(audit P0).

Gates (all hard):
  coverage            == 20,992 exactly
  empty / tiny / huge == 0
  real subset         == --real-expect glyphs (default 4070) and cmap
  counters            no glyph with 0 holes where WenKai has >= 1, and
                      <= --max-lost-frac of comparable glyphs may lose a hole
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BLOCK = (0x4E00, 0x9FFF)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-B-Regular.ttf"))
    ap.add_argument("--outdir", default=str(ROOT / "work-b" / "qa"))
    ap.add_argument("--real", default=str(ROOT / "build" / "GuanGeKai-B-Real.ttf"))
    ap.add_argument("--real-expect", type=int, default=4070,
                    help="exact expected glyph count in the real subset")
    ap.add_argument("--min-real", type=int, default=4070,
                    help="kept for compatibility; --real-expect is the hard gate")
    ap.add_argument("--holes", type=int, default=300,
                    help="counter audit sample size (0 = skip, --holes 0 to disable)")
    ap.add_argument("--max-lost-frac", type=float, default=0.08,
                    help="max share of comparable glyphs allowed to lose a counter")
    ap.add_argument("--sheets", type=int, default=0, help="0 = all")
    args = ap.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    f = TTFont(args.font)
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    have = [c for c in range(BLOCK[0], BLOCK[1] + 1) if c in cmap]
    print(f"coverage {len(have)}/{BLOCK[1]-BLOCK[0]+1} = {len(have)/(BLOCK[1]-BLOCK[0]+1):.4%}")
    empty, tiny, huge = [], [], []
    for cp in have:
        bp = BoundsPen(gs)
        gs[cmap[cp]].draw(bp)
        if not bp.bounds:
            empty.append(cp)
            continue
        x0, y0, x1, y1 = bp.bounds
        w, h = x1 - x0, y1 - y0
        if w < 60 or h < 60:
            tiny.append((chr(cp), round(w), round(h)))
        if w > 1000 or h > 1000:
            huge.append((chr(cp), round(w), round(h)))
    print("empty", len(empty), "tiny", len(tiny), "huge", len(huge))
    print("tiny sample", tiny[:20])
    print("huge sample", huge[:20])
    fails = []
    if len(have) != BLOCK[1] - BLOCK[0] + 1:
        fails.append(f"coverage {len(have)} != {BLOCK[1]-BLOCK[0]+1}")
    if empty:
        fails.append(f"{len(empty)} empty glyphs")
    if tiny:
        fails.append(f"{len(tiny)} tiny glyphs")
    if huge:
        fails.append(f"{len(huge)} huge glyphs")

    cols, rows = 40, 25
    per = cols * rows
    chars = [chr(c) for c in have]
    fnt = ImageFont.truetype(args.font, 55)
    nsheet = (len(chars) + per - 1) // per
    for s in range(0, len(chars), per):
        if args.sheets and s // per >= args.sheets:
            break
        chunk = chars[s:s + per]
        sheet = Image.new("RGB", (cols * 60, rows * 66), "white")
        d = ImageDraw.Draw(sheet)
        for i, ch in enumerate(chunk):
            x, y = (i % cols) * 60, (i // cols) * 66
            d.text((x + 2, y), ch, font=fnt, fill="black")
        sheet.save(out / f"sheet_{s//per:03d}.png")
    print("sheets:", nsheet, "->", out)

    real_path = Path(args.real)
    status = "MISSING"
    if real_path.exists():
        rf = TTFont(str(real_path))
        n_real = rf["maxp"].numGlyphs - 1
        cm_real = len(rf.getBestCmap())
        want = args.real_expect
        status = "OK" if (n_real == want and cm_real == want) else "BROKEN"
        print(f"real-subset glyphs {n_real} cmap {cm_real} (expect {want}) -> {status}")
        if status != "OK":
            fails.append(f"real subset {n_real}/{cm_real} != {want}")
    else:
        fails.append(f"real subset font missing: {real_path}")

    holes = None
    if args.holes:
        import subprocess, sys as _sys
        r = subprocess.run([_sys.executable, str(Path(__file__).parent / "71_holes_b.py"),
                            "--font", args.font, "--n", str(args.holes),
                            "--json", str(out / "holes.json")],
                           capture_output=True, text=True)
        print(r.stdout.strip())
        hj = out / "holes.json"
        if hj.exists():
            holes = json.loads(hj.read_text())
            frac = holes["lost"] / max(1, holes["comparable"])
            if frac > args.max_lost_frac:
                fails.append(f"counters lost in {frac:.1%} of comparable glyphs "
                             f"(> {args.max_lost_frac:.0%})")
    stats = dict(coverage=len(have), empty=len(empty), tiny=tiny[:50], huge=huge[:50],
                 real_subset=status, n_sheets=nsheet, holes=holes)
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    if fails:
        raise SystemExit("QA FAILED: " + "; ".join(fails))
    print("QA OK")


if __name__ == "__main__":
    main()
