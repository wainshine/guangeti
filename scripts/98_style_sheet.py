"""Provenance-stratified style sheet: show what the shipped font is actually made of.

`95_compare_lines.py` renders a font-wide sample, so every glyph is a mix of 真迹 /
GAN / ribbon fallback and you cannot tell which is which.  This sheet splits by
provenance first, then by character, so the eye can judge each source separately.

Layout (one image per line)
---------------------------
    row 0  真迹        real glyphs from the manuscript
    row 1  GAN (main)  the primary generator (A: ep90, B/C: ep)
    row 2  GAN (fill)  only when the line ships a second checkpoint (A ep80, B ht)
    row 3  ribbon      the fallback renderer -- the weakest class, worth watching

Columns are the same characters for every row, drawn from the stratum itself, so a
row is internally comparable but rows are *not* the same characters (they cannot be:
a character belongs to exactly one stratum).

Inputs (per line, fixed paths)
------------------------------
    A: build/GuanGeKai-Regular.ttf    + release/provenance.json
    B: build/GuanGeKai-B-Regular.ttf  + release-b/provenance.json
    C: build/GuanGeKai-C-Regular.ttf  + release-c/provenance.json

Strata are read from the provenance file's values, so A's four-state provenance
(`real/gan_ep90/gan_ep80/ribbon_fb`) and B/C's three-state one both work without
special casing.

Usage
-----
    python3 scripts/98_style_sheet.py --line A
    python3 scripts/98_style_sheet.py --line B --check
    python3 scripts/98_style_sheet.py --all        # every line that has been packaged

Exit codes: 0 ok, 2 inputs missing / stale (never draw a sheet from a half-built line).

This script is shared by all three lines.  B/C sessions run `--line B` / `--line C`
after `14_package`-equivalent; they do not fork it.  The cross-line sheets need all
three lines packaged and are produced by `--all` at project level.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"

LINES = {
    "A": dict(font="build/GuanGeKai-Regular.ttf", rel="release", family="GuanGe Kai"),
    "B": dict(font="build/GuanGeKai-B-Regular.ttf", rel="release-b", family="GuanGe Kai B"),
    "C": dict(font="build/GuanGeKai-C-Regular.ttf", rel="release-c", family="GuanGe Kai C"),
}

STRATUM_LABEL = {
    "real": "真跡",
    "gan": "GAN",
    "gan_ep90": "GAN（主 ep90）",
    "gan_ep80": "GAN（補位 ep80）",
    "gan_ht": "GAN（補位）",
    "ribbon_fb": "帶狀回退 ribbon",
}

BG, FG, LABEL, DIM, RULE = 252, 20, 105, 150, 210
COLS = 22
CELL = 96


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _shipped_hash(rel: str, name: str) -> str | None:
    sums = ROOT / rel / "SHA256SUMS"
    if not sums.exists():
        return None
    for line in sums.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == name:
            return parts[0]
    return None


def load_line(tag: str, check: bool) -> tuple[Path, dict, str]:
    spec = LINES[tag]
    font = ROOT / spec["font"]
    prov_path = ROOT / spec["rel"] / "provenance.json"
    for p in (font, prov_path):
        if not p.exists():
            raise SystemExit(f"ABORT[{tag}]: 缺少 {p.relative_to(ROOT)}（先跑打包）")
    want = _shipped_hash(spec["rel"], font.name)
    if check and want and _sha(font) != want:
        raise SystemExit(f"ABORT[{tag}]: build/{font.name} 与 {spec['rel']}/SHA256SUMS 不一致，先重新打包")
    prov = json.loads(prov_path.read_text())
    return font, prov, spec["family"]


def strata_of(prov: dict) -> list[tuple[str, list[str]]]:
    buckets: dict[str, list[str]] = {}
    for ch, src in prov.items():
        buckets.setdefault(src, []).append(ch)
    order = {"real": 0, "gan": 1, "gan_ep90": 1, "gan_ep80": 2, "gan_ht": 2, "ribbon_fb": 3}
    keys = sorted(buckets, key=lambda k: (order.get(k, 9), -len(buckets[k])))
    return [(k, sorted(buckets[k])) for k in keys]


def pick(chars: list[str], n: int, seed: int) -> list[str]:
    if len(chars) <= n:
        return chars
    return random.Random(seed).sample(chars, n)


def draw_sheet(tag: str, family: str, font_path: Path, prov: dict, n: int, seed: int,
               out: Path) -> None:
    strata = strata_of(prov)
    if not strata:
        raise SystemExit(f"ABORT[{tag}]: provenance 为空")

    label_font = ImageFont.truetype(str(BASE), 17)
    small = ImageFont.truetype(str(BASE), 14)
    glyph_font = ImageFont.truetype(str(font_path), CELL)
    head_font = ImageFont.truetype(str(font_path), 34)

    pad, row_h, tag_w = 26, CELL + 16, 128
    total = len(prov)
    width = pad * 2 + tag_w + COLS * CELL + 8
    height = 96 + (len(strata) + 1) * (row_h + 26) + 60

    img = Image.new("L", (width, height), BG)
    d = ImageDraw.Draw(img)

    d.text((pad, 16), f"{tag} 線  {family}  —  按來源分層（每列一個字，行內同一批字）",
           font=label_font, fill=FG)
    d.text((pad, 40), f"{font_path.name}  共 {total:,} 字", font=small, fill=DIM)

    wk_font = ImageFont.truetype(str(BASE), CELL)
    y = 78
    real_pick = None
    for key, chars in strata:
        picked = pick(chars, n, seed)
        if key == "real":
            real_pick = picked
        label = STRATUM_LABEL.get(key, key)
        share = 100.0 * len(chars) / total
        d.text((pad, y), label, font=label_font, fill=LABEL)
        d.text((pad, y + 20), f"{len(chars):,} 字  {share:.1f}%", font=small, fill=DIM)
        x = pad + tag_w
        for ch in picked:
            d.text((x + CELL * 0.5, y + CELL * 0.84), ch, font=glyph_font, fill=FG, anchor="ms")
            x += CELL
        d.line((pad, y + row_h + 2, width - pad, y + row_h + 2), fill=RULE, width=1)
        y += row_h + 26
        if key == "real":          # 文楷对照：与真迹行同一批字，方便逐字比结构
            y += 18                # 标签单独占一行，避免与字形重叠
            d.text((pad, y - 2), "霞鶩文楷（訓練源，僅參照）", font=label_font, fill=DIM)
            x = pad + tag_w
            for ch in picked:
                d.text((x + CELL * 0.5, y + CELL * 0.84), ch, font=wk_font, fill=DIM, anchor="ms")
                x += CELL
            d.line((pad, y + CELL + 6, width - pad, y + CELL + 6), fill=RULE, width=1)
            y += CELL + 26

    d.text((pad, height - 24),
           "同一行內是一批字，不同行不是同一批字（一個字只屬於一個來源）。"
           "回退行最容易看出筆畫簡化與風格割裂。",
           font=small, fill=DIM)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("P", palette=Image.ADAPTIVE, colors=16).save(out, optimize=True)
    print(f"-> {out.relative_to(ROOT)}  ({out.stat().st_size/1e6:.2f} MB, {img.width}x{img.height})")
    for key, chars in strata:
        print(f"   {key:10s} {len(chars):6,}  {100.0*len(chars)/total:5.1f}%")


def _render(font, ch, cell=CELL):
    import numpy as np
    im = Image.new("L", (cell, cell), 0)
    ImageDraw.Draw(im).text((cell * 0.5, cell * 0.84), ch, font=font, fill=255, anchor="ms")
    return np.asarray(im) > 127


def draw_cross(fonts: dict[str, Path], provs: dict[str, dict], n: int, seed: int, out: Path) -> None:
    """Same-stratum blocks: characters that are real (or GAN, or ribbon) in *every* line."""
    import numpy as np
    label_font = ImageFont.truetype(str(BASE), 17)
    small = ImageFont.truetype(str(BASE), 14)
    tags = [t for t in ("A", "B", "C") if t in fonts]
    if len(tags) < 2:
        print("cross: 不足两条线，跳过")
        return
    def bucket(prov, want):
        return {c for c, s in prov.items() if (s == "real") == (want == "real") and
                ((want == "real") or (s.startswith("gan") if want == "gan" else s == "ribbon_fb"))}
    blocks = []
    for want, title in (("real", "三線皆真跡"), ("gan", "三線皆 GAN"), ("ribbon", "三線皆回退")):
        common = set.intersection(*[bucket(provs[t], want) for t in tags]) if tags else set()
        if common:
            blocks.append((title, sorted(common)))
    if not blocks:
        print("cross: 没有三线共有的同源字，跳过")
        return
    widths = 190
    height = 90 + len(blocks) * ((len(tags) + 1) * (CELL + 6) + 34) + 30
    img = Image.new("L", (26 * 2 + widths + n * CELL, height), BG)
    d = ImageDraw.Draw(img)
    d.text((26, 16), "三線同源對齊 — 每個方塊內的字，三條線來源相同（真跡/GAN/回退）", font=label_font, fill=FG)
    y = 60
    for title, common in blocks:
        d.text((26, y), f"{title}  共 {len(common):,} 字", font=label_font, fill=LABEL)
        y += 22
        picked = pick(common, n, seed)
        for tag in tags:
            f = ImageFont.truetype(str(fonts[tag]), CELL)
            d.text((26, y + CELL * 0.6), f"{tag} 線", font=small, fill=DIM)
            x = 26 + widths
            for ch in picked:
                d.text((x + CELL * 0.5, y + CELL * 0.84), ch, font=f, fill=FG, anchor="ms")
                x += CELL
            y += CELL + 6
        wk = ImageFont.truetype(str(BASE), CELL)
        d.text((26, y + CELL * 0.6), "文楷", font=small, fill=DIM)
        x = 26 + widths
        for ch in picked:
            d.text((x + CELL * 0.5, y + CELL * 0.84), ch, font=wk, fill=DIM, anchor="ms")
            x += CELL
        y += CELL + 6
        d.line((26, y + 4, img.width - 26, y + 4), fill=RULE, width=1)
        y += 30
    img.convert("P", palette=Image.ADAPTIVE, colors=16).save(out, optimize=True)
    print(f"-> {out.relative_to(ROOT)}  ({out.stat().st_size/1e6:.2f} MB)")


def draw_failures(fonts: dict[str, Path], provs: dict[str, dict], n: int, out: Path) -> None:
    """Per line: the n worst glyphs by ink deviation and component-count mismatch vs WenKai."""
    import numpy as np, cv2
    label_font = ImageFont.truetype(str(BASE), 17)
    small = ImageFont.truetype(str(BASE), 14)
    wk = ImageFont.truetype(str(BASE), CELL)
    def comps(m):
        k, _, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
        return sum(1 for i in range(1, k) if st[i, 4] >= 8)
    rows = []
    for tag, fp in fonts.items():
        f = ImageFont.truetype(str(fp), CELL)
        scored = []
        for ch in provs[tag]:
            a, b = _render(f, ch), _render(wk, ch)
            if not b.any():
                continue
            ink = a.sum() / b.sum()
            dc = abs(comps(a) - comps(b))
            scored.append((abs(np.log(max(ink, 1e-3))) + 0.15 * dc, ch, ink, dc))
        scored.sort(reverse=True)
        rows.append((tag, scored[:n]))
    wk_font = ImageFont.truetype(str(BASE), int(CELL * 0.9))
    col = CELL + 26
    width = 26 * 2 + 150 + n * col + 120
    rowh = CELL * 2 + 34
    height = 78 + len(rows) * rowh + 30
    img = Image.new("L", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.text((26, 16), "失敗畫廊 — 每線墨量/連通域最異常的字（上＝本字體，下＝文楷參照）",
           font=label_font, fill=FG)
    d.text((26, 38), "數字：本字墨量/文楷墨量 · 連通域差", font=small, fill=DIM)
    y = 66
    for tag, items in rows:
        f = ImageFont.truetype(str(fonts[tag]), CELL)
        d.text((26, y + CELL * 0.5), f"{tag} 線", font=label_font, fill=LABEL)
        x = 26 + 150
        for score, ch, ink, dc in items:
            d.text((x + CELL * 0.5, y + CELL * 0.84), ch, font=f, fill=FG, anchor="ms")
            d.text((x + CELL * 0.5, y + CELL + 6 + CELL * 0.8), ch, font=wk_font, fill=DIM, anchor="ms")
            d.text((x + CELL * 0.5, y + rowh - 12), f"{ink:.2f}/{dc}", font=small, fill=DIM, anchor="ma")
            x += CELL + 26
        y += rowh
    d.text((26, height - 22), "墨量比 < 0.75 或 > 1.4、連通域差 ≥ 2 的字優先人工確認。",
           font=small, fill=DIM)

    img.convert("P", palette=Image.ADAPTIVE, colors=16).save(out, optimize=True)
    print(f"-> {out.relative_to(ROOT)}  ({out.stat().st_size/1e6:.2f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", choices=list(LINES), help="single line to draw")
    ap.add_argument("--all", action="store_true", help="every line that has been packaged")
    ap.add_argument("--n", type=int, default=COLS, help="characters per row")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--check", action="store_true", help="verify font against release SHA256SUMS")
    args = ap.parse_args()

    if not args.line and not args.all:
        ap.error("需要 --line A|B|C 或 --all")

    tags = [args.line] if args.line else list(LINES)
    drawn = []
    for tag in tags:
        try:
            font, prov, family = load_line(tag, args.check)
        except SystemExit as exc:
            if args.line:
                raise
            print(f"skip {tag}: {exc}")
            continue
        out = ROOT / "docs" / "images" / f"style-{tag}.png"
        draw_sheet(tag, family, font, prov, args.n, args.seed, out)
        drawn.append(tag)

    if args.all:
        missing = [t for t in LINES if t not in drawn]
        if missing:
            print(f"\n跨線對照（style-cross / style-failures）需要三條線都打包：缺 {missing}，本輪跳過。")
        else:
            fonts = {t: ROOT / LINES[t]["font"] for t in LINES}
            provs = {t: json.loads((ROOT / LINES[t]["rel"] / "provenance.json").read_text()) for t in LINES}
            draw_cross(fonts, provs, 16, args.seed, ROOT / "docs/images/style-cross.png")
            draw_failures(fonts, provs, 8, ROOT / "docs/images/style-failures.png")
    if not drawn:
        sys.exit(2)


if __name__ == "__main__":
    main()
