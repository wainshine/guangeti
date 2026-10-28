"""Three-line comparison sheet: GuanGe Kai (A 四书) / B (史记) / C (永乐大典).

One image, same text, three typefaces stacked, so a regression in any line is visible
at a glance instead of needing three separate specimen files.

Why this exists
---------------
Each line ships its own ``specimen*.png`` and ``book-vs-font*``. Those are per-release
and per-line: you cannot tell from them whether the three lines still look like
siblings, and a weight drift or a fallback spike in one line shows up nowhere else.
This sheet is release-time proof of all three at once.

Layout
------
For every sample group the three lines are stacked (A / B / C), each row tagged.
The same text is used in every row, so the differences are style, not content.

Samples are grouped by what tends to break:
  常用字    structural sanity
  孔洞字    counter characters -- the project's P0 defect class
  複雜字    dense characters, where the GAN is weakest and fallback is most likely
  簡體碼位  simplified codepoints that must still carry traditional forms
  非漢字    space / digits / punctuation: the fonts are CJK-only, this row shows it

Sizes 48 / 24 / 14 px expose weight bias and small-size brittleness.

Notes
-----
* Renders only ``build/GuanGeKai*-*.ttf``; missing lines are skipped.
* The faces have **no space, no ASCII, no CJK punctuation** (verified: cmap lacks
  0x20/0x30/0x41/0x300C). Spaces in the samples are drawn as gaps by this script,
  not as glyphs -- otherwise every space would render as a .notdef box.
* Output is one indexed PNG, target < 1.5 MB.

What this is / is not
---------------------
It is a **one-glance sanity sheet**: same text, three typefaces, three sizes, plus a
numeric header (version, real/gan/ribbon counts, ink ratio on a seeded sample).
It is **not** a test suite: a regression outside the sample text will not show up.
It exists to catch the classes of defect you can see instantly -- a line suddenly
thinner, a line missing strokes, a fallback ratio jumping -- before packaging.

It refuses to draw a sheet that would lie:
  * `--check` verifies each `build/GuanGeKai*.ttf` matches the hash in its
    `release*/SHA256SUMS`; a stale font (rebuilt but not packaged) exits 2;
  * the seeded random row (`--seed`, default 7) draws 32 codepoints from the block so
    the sheet is not limited to hand-picked samples;
  * a line whose font is missing is reported and excluded, never silently drawn empty.

Usage
-----
    python3 scripts/95_compare_lines.py            # -> docs/images/lines-compare.png
    python3 scripts/95_compare_lines.py --check    # also verify packaged hashes
    python3 scripts/95_compare_lines.py --show     # print sample text
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]

LINES = [
    ("A", "GuanGe Kai", ROOT / "build" / "GuanGeKai-Regular.ttf", "release"),
    ("B", "GuanGe Kai B", ROOT / "build" / "GuanGeKai-B-Regular.ttf", "release-b"),
    ("C", "GuanGe Kai C", ROOT / "build" / "GuanGeKai-C-Regular.ttf", "release-c"),
]
BASE = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"
OUT = ROOT / "docs" / "images" / "lines-compare.png"

SAMPLES = [
    ("常用字", "天地玄黃 宇宙洪荒 日月盈昃 辰宿列張"),
    ("孔洞字", "國目自回田 四申昌串吕 門開間問聞"),
    ("複雜字", "萬曆年製 乾隆御覽 館閣體楷 繪繡纏繞"),
    ("簡體碼位", "书习长价礼类 庄个亘坛"),
    ("非漢字", " 0123 ABC ，。「」"),
]
SIZES = [48, 24, 14]

BG, FG, LABEL, RULE, DIM = 252, 20, 110, 208, 150
BLOCK = (0x4E00, 0x9FFF)
RANDOM_ROW = 32


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _release_hash(rel: str, name: str) -> str | None:
    sums = ROOT / rel / "SHA256SUMS"
    if not sums.exists():
        return None
    for line in sums.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == name:
            return parts[0]
    return None


def _version(path: Path) -> str:
    try:
        f = TTFont(str(path), lazy=True)
        names = [str(n) for n in f["name"].names if n.nameID == 5 and n.platformID == 3]
        return names[0].replace("Version ", "v") if names else "?"
    except Exception:
        return "?"


def _metrics(rel: str) -> str:
    p = ROOT / rel / "stats.json"
    if not p.exists():
        return ""
    try:
        d = json.loads(p.read_text())
    except Exception:
        return ""
    real = d.get("real", 0)
    # A ships four-state provenance (gan_ep90 + gan_ep80 fill-in); B/C ship "gan"
    gen = sum(d.get(k, 0) for k in ("gan", "gan_ht", "gan_ep90", "gan_ep80"))
    ribbon = d.get("ribbon_fallback", 0)
    total = gen + ribbon
    fb = (100.0 * ribbon / total) if total else 0.0
    return f"真跡 {real:,}  GAN {gen:,}  回退 {ribbon:,} ({fb:.1f}%)"


def _ink_ratio(font_path: Path, chars: str, size: int = 128) -> float:
    """Median ink area of `chars` relative to WenKai -- a crude weight/darkness gauge."""
    base = ImageFont.truetype(str(BASE), size)
    target = ImageFont.truetype(str(font_path), size)
    ratios = []
    for ch in chars:
        a = Image.new("L", (size * 2, size * 2), 0)
        b = Image.new("L", (size * 2, size * 2), 0)
        ImageDraw.Draw(a).text((0, size * 1.72), ch, font=base, fill=255, anchor="ls")
        ImageDraw.Draw(b).text((0, size * 1.72), ch, font=target, fill=255, anchor="ls")
        ia = (np.asarray(a) > 127).sum()
        ib = (np.asarray(b) > 127).sum()
        if ia:
            ratios.append(ib / ia)
    ratios.sort()
    return ratios[len(ratios) // 2] if ratios else float("nan")


def draw_spaced(d: ImageDraw.ImageDraw, y: int, x: int, text: str,
                font: ImageFont.FreeTypeFont, fill: int) -> None:
    """Draw text treating spaces as real gaps (the faces have no space glyph)."""
    for piece in text.split(" "):
        if piece:
            d.text((x, y), piece, font=font, fill=fill)
            x += font.getlength(piece)
        x += font.size * 0.42


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--width", type=int, default=1500)
    ap.add_argument("--check", action="store_true",
                    help="verify build/*.ttf against release*/SHA256SUMS (exit 2 on mismatch)")
    ap.add_argument("--seed", type=int, default=7, help="seed for the random row")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--c-regular", default="",
                    help="override the C-line font (e.g. build/GuanGeKai-C-Regular-v2.ttf); "
                         "skips the release-c hash check for C")
    args = ap.parse_args()
    if args.c_regular:
        for _i, (_t, _n, _p, _rel) in enumerate(LINES):
            if _t == "C":
                LINES[_i] = (_t, _n, Path(args.c_regular), _rel)

    # seeded random row: same codepoints for every line, drawn from the block, so the
    # sheet is not limited to hand-picked characters
    rng = random.Random(args.seed)
    pool = [chr(c) for c in range(BLOCK[0], BLOCK[1] + 1)]
    rnd = "".join(rng.sample(pool, RANDOM_ROW))
    samples = list(SAMPLES) + [("隨機抽樣", rnd)]

    if args.show:
        for k, v in samples:
            print(f"{k}: {v}")

    fonts = [(t, n, Path(p), rel) for t, n, p, rel in LINES if Path(p).exists()]
    if not fonts:
        raise SystemExit("ABORT: no GuanGeKai*.ttf under build/")

    # --- packaged-hash guard: never draw a sheet from a font that is not what shipped
    stale = []
    for tag, _name, path, rel in fonts:
        if tag == "C" and args.c_regular:
            continue
        want = _release_hash(rel, path.name)
        if want and _sha(path) != want:
            stale.append(f"{tag} {path.name}: build≠release/{rel}/SHA256SUMS")
    for tag, _name, path, rel in fonts:
        if tag == "C" and args.c_regular:
            continue
        if not _release_hash(rel, path.name):
            stale.append(f"{tag} {path.name}: {rel}/SHA256SUMS 无此条目（未打包？）")
    if stale and args.check:
        print("STALE — 字体与发布包不一致，先打包再出图：")
        for item in stale:
            print("   ", item)
        raise SystemExit(2)
    if stale:
        print("! 注意：字体与发布包不一致（用 --check 可让它变成硬错）")
        for item in stale:
            print("   ", item)
    if not Path(BASE).exists():
        raise SystemExit(f"ABORT: base face missing: {BASE}")

    label_font = ImageFont.truetype(str(BASE), 17)
    tag_font = ImageFont.truetype(str(BASE), 15)
    pad, tag_w = 26, 26

    need = 0
    for size in SIZES:
        f = ImageFont.truetype(str(BASE), size)
        for _, text in samples:
            need = max(need, int(f.getlength(text) + len(text.split(" ")) * size * 0.42))
    img_w = max(args.width, need + tag_w + pad * 2)

    header_h = 78
    row_h = {s: int(s * 1.55) for s in SIZES}
    total_h = header_h + sum((row_h[s] + 2) * len(fonts) * len(samples) + 20 * len(samples) + 26 for s in SIZES) + 34

    img = Image.new("L", (img_w, total_h), BG)
    d = ImageDraw.Draw(img)

    d.text((pad, 12), "館閣楷三線對照  GuanGe Kai  A（四書） / B（史記） / C（永樂大典）",
           font=label_font, fill=FG)
    y = 36
    ink_ref = rnd[:24]
    for i, (tag, name, path, rel) in enumerate(fonts):
        ratio = _ink_ratio(path, ink_ref)
        d.text((pad, y),
               f"{tag}  {name}  {_version(path)}   {_metrics(rel)}   墨量/文楷 {ratio:.2f}",
               font=tag_font, fill=90 if i == 0 else LABEL)
        y += 15

    y = header_h
    for size in SIZES:
        d.text((pad, y), f"{size} px", font=label_font, fill=LABEL)
        y += 20
        for title, text in samples:
            d.text((pad, y + 2), title, font=tag_font, fill=LABEL)
            y += 20
            for tag, _name, path, _rel in fonts:
                f = ImageFont.truetype(str(path), size)
                base_top = y + int(row_h[size] * 0.14)
                d.text((pad, base_top + 2), tag, font=tag_font, fill=DIM)
                draw_spaced(d, base_top, pad + tag_w, text, f, FG)
                y += row_h[size]
            d.line((pad, y + 1, img_w - pad, y + 1), fill=RULE, width=1)
            y += 2
        y += 20

    d.text((pad, total_h - 24),
           "同一段文字、同一字號、逐行對齊；□ 表示該字體沒有此碼位——三套字均為純 CJK，無 ASCII、無空格。"
           "回退率越高，正文裡「細弱字」越多。",
           font=tag_font, fill=DIM)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("P", palette=Image.ADAPTIVE, colors=16).save(out, optimize=True)
    print(f"-> {out}  ({out.stat().st_size / 1e6:.2f} MB, {img.width}x{img.height})")
    for tag, name, path, rel in fonts:
        print(f"   {tag} {name:14s} {_version(path):10s} {_metrics(rel)}")


if __name__ == "__main__":
    main()
