"""Extend a GuanGeKai font with the punctuation / digits / spaces it lacks.

Why: the three families cover CJK basic block only (20,992). Space, digits and CJK
punctuation fall back to `.notdef`, which is a hollow box -- a text set in these fonts
shows □ everywhere. This adds the minimum set so the font can be used for body text.

Source of glyphs: LXGW WenKai (OFL 1.1, no Reserved-Name use here), same upm 1000,
copied 1:1 (visual test in docs/PLAN-PUNCT.md shows 1.00 is the right scale).

Not included on purpose: Latin A-Z / a-z. WenKai's Latin is a modern sans/serif hybrid
and clashes with kai; leaving it to the system fallback looks better.

Usage
-----
    python3 scripts/13_extend_punct.py --line A            # writes build/...-Ext.ttf
    python3 scripts/13_extend_punct.py --line B --drop-outside-basic
    python3 scripts/13_extend_punct.py --line C --inplace  # overwrite build font

Order: run AFTER 11_build_full.py, BEFORE 14_package.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.misc.transform import Transform

ROOT = Path(__file__).resolve().parents[1]
WENKAI = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import punct_set  # noqa: E402  shared CHARS / REMOVED / EXPECTED_CMAP

FONTS = {
    "A": ROOT / "build" / "GuanGeKai-Regular.ttf",
    "B": ROOT / "build" / "GuanGeKai-B-Regular.ttf",
    "C": ROOT / "build" / "GuanGeKai-C-Regular.ttf",
}

# 第一档：必补（约 40 字）。拉丁不进这一档，见模块 docstring。
CHARS = punct_set.CHARS


def extend(font_path: Path, out_path: Path, drop_outside: bool, dry: bool) -> None:
    base = TTFont(str(font_path))
    wk = TTFont(str(WENKAI))
    wk_cmap = wk.getBestCmap()
    wk_gs = wk.getGlyphSet()
    glyf, hmtx = base["glyf"], base["hmtx"]
    cmap = base.getBestCmap()
    order = list(base.getGlyphOrder())

    dropped_legacy = []
    for cp in punct_set.REMOVED:            # delete the half-width curly quotes
        if cp in cmap:
            for table in base["cmap"].tables:
                table.cmap.pop(cp, None)
            dropped_legacy.append(cp)
    added, skipped = [], []
    for cp in CHARS:
        if cp in cmap:
            skipped.append(cp)
            continue
        src = wk_cmap.get(cp)
        if src is None:
            skipped.append(cp)
            continue
        rp = RecordingPen()
        wk_gs[src].draw(rp)
        pen = TTGlyphPen(None)
        rp.replay(TransformPen(pen, Transform(1.0, 0, 0, 1.0, 0, 0)))
        name = f"uni{cp:04X}"
        glyf[name] = pen.glyph()
        try:
            aw, lsb = wk["hmtx"][src]
        except KeyError:
            aw, lsb = base["head"].unitsPerEm, 0
        hmtx[name] = (aw, lsb)
        order.append(name)
        added.append((cp, name))

    dropped = []
    if drop_outside:
        keep_uni = [n for _c, n in added]
        added_cp = set(CHARS)          # 本脚本负责的 44 个码位永不删除
        outside = [c for c in base.getBestCmap()
                   if not (0x4E00 <= c <= 0x9FFF) and c not in added_cp]
        dropped = outside
        for table in base["cmap"].tables:
            for cp in outside:
                table.cmap.pop(cp, None)

    if dry:
        print(f"{font_path.name}: 将新增 {len(added)} 码位, 跳过 {len(skipped)}, 删除区外 {len(dropped)}")
        print("  新增:", "".join(chr(c) for c, _ in added))
        if dropped:
            print("  删除:", "".join(chr(c) for c in dropped))
        return

    base.setGlyphOrder(order)
    glyf.glyphOrder = order
    base["maxp"].numGlyphs = len(order)
    for cp, name in added:
        for table in base["cmap"].tables:
            if table.format in (4, 12):
                table.cmap[cp] = name

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.recalcTimestamp = False        # byte-reproducible: do not stamp head.modified
    base.save(str(out_path))
    try:
        shown = out_path.relative_to(ROOT)
    except ValueError:
        shown = out_path
    if dropped_legacy:
        print(f"   删除遗留弯引号 {len(dropped_legacy)}: " + "".join(chr(c) for c in dropped_legacy))
    print(f"-> {shown}  新增 {len(added)} 码位"
          + (f"，删除区外 {len(dropped)}" if dropped else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", choices=list(FONTS), required=True)
    ap.add_argument("--out", help="输出路径（默认 build/<名字>-Ext.ttf）")
    ap.add_argument("--inplace", action="store_true", help="直接覆盖 build 里的字体")
    ap.add_argument("--drop-outside-basic", action="store_true",
                    help="删除基本区之外的码位（B 线的 5 个扩展 A）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = FONTS[args.line]
    if not src.exists():
        sys.exit(f"ABORT: 缺少 {src.relative_to(ROOT)}")
    out = src if args.inplace else Path(args.out or str(src.with_name(src.stem + "-Ext.ttf")))
    extend(src, out, args.drop_outside_basic, args.dry_run)


if __name__ == "__main__":
    main()
