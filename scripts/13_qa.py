"""Quality checks + contact sheets for a built font."""
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
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-Regular.ttf"))
    ap.add_argument("--outdir", default=str(ROOT / "work" / "qa"))
    ap.add_argument("--real", default=str(ROOT / "build" / "GuanGeKai-Real.ttf"))
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

    # contact sheets: 40x25 chars per sheet
    cols, rows = 40, 25
    per = cols * rows
    chars = [chr(c) for c in have]
    fnt = ImageFont.truetype(args.font, 55)
    for s in range(0, len(chars), per):
        chunk = chars[s:s + per]
        sheet = Image.new("RGB", (cols * 60, rows * 66), "white")
        d = ImageDraw.Draw(sheet)
        for i, ch in enumerate(chunk):
            x, y = (i % cols) * 60, (i // cols) * 66
            d.text((x + 2, y), ch, font=fnt, fill="black")
        sheet.save(out / f"sheet_{s//per:03d}.png")
    print("sheets:", (len(chars) + per - 1) // per, "->", out)
    real_path = Path(args.real)
    if real_path.exists():
        rf = TTFont(str(real_path))
        n_real = rf["maxp"].numGlyphs - 1
        cm_real = len(rf.getBestCmap())
        try:
            _exp = sum(1 for _ in open(ROOT / "work" / "chosen.jsonl"))
        except Exception:
            _exp = 1675
        status = "OK" if n_real == _exp and cm_real == _exp else "BROKEN"
        print(f"real-subset glyphs {n_real} cmap {cm_real} -> {status}")
        if status != "OK":
            raise SystemExit(f"ABORT: GuanGeKai-Real.ttf expected {_exp}/{_exp}, got {n_real}/{cm_real}")
    else:
        raise SystemExit(f"ABORT: {real_path} missing — run 07_build_real.py first")
    # hard gates (audit P1-3): these used to be printed and ignored
    if len(have) != BLOCK[1] - BLOCK[0] + 1:
        raise SystemExit(f"ABORT: coverage {len(have)} != {BLOCK[1]-BLOCK[0]+1}")
    if empty or tiny or huge:
        raise SystemExit(f"ABORT: empty={len(empty)} tiny={len(tiny)} huge={len(huge)}")
    # fontRevision must agree with the name-table version (audit 3-3)
    _f = TTFont(args.font)
    _ver = [str(n) for n in _f["name"].names if n.nameID == 5 and n.platformID == 3]
    if _ver:
        _p = (_ver[0].replace("Version ", "").split(".") + ["0", "0"])[:3]
        _want = int(_p[0]) + int(_p[1]) / 10.0 + int(_p[2]) / 100.0
        if abs(_f["head"].fontRevision - _want) > 1e-3:
            raise SystemExit(f"ABORT: fontRevision {_f['head'].fontRevision:.4f} != {_want:.3f}")
    stats = dict(coverage=len(have), empty=len(empty), tiny=tiny[:50], huge=huge[:50])
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
