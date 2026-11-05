#!/usr/bin/env python3
"""Fixed, versioned review boards for human visual acceptance (A/B/C lines).

Why this exists
---------------
Ad-hoc "make me a comparison image" requests produce evidence that cannot be
compared across versions and is thrown away with ``work/preview``.  This script
emits the *same* boards for every build, stamps them with the font SHA-256, and
keeps the human verdict next to them in an append-only log.

Boards
------
B1 random       fixed-seed sample over the full cmap, one glyph per cell
B2 clean        the singleton characters that were never trained on
B3 strata       provenance rows (real / gan_ep90 / gan_ep80 / ribbon / punct)
B4 text-large   three fixed passages at 24 px and 48 px, WenKai vs shipped
B5 text-small   the same passages at 12 px and 16 px, 2x nearest (pixel truth)
B6 diff         per-glyph ink/bbox delta against --prev (optional)

Usage
-----
    python3 scripts/100_review.py --line A
    python3 scripts/100_review.py --line A --prev build/GuanGeKai-v1.6.2.ttf
    python3 scripts/100_review.py --line A --record pass --notes "整体可，园字开口接受"
    python3 scripts/100_review.py --line A --check      # 0 = current font has a pass

Outputs
-------
    work/review/<sha8>/00_cover.png ... B6_diff.png
    work/review/<sha8>/manifest.json
    work/review/verdicts.jsonl                          (append-only)

The checklist is deliberately finite: content / stroke / weight / small / punct /
seam.  "Looks fine" is not a verdict; tick the six items or name the failing one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"

PRESETS = {
    "A": dict(font="build/GuanGeKai-Regular.ttf", prov="release/provenance.json",
              family="GuanGe Kai"),
    "B": dict(font="build/GuanGeKai-B-Regular.ttf", prov="release-b/provenance.json",
              family="GuanGe Kai B"),
    "C": dict(font="build/GuanGeKai-C-Regular.ttf", prov="release-c/provenance.json",
              family="GuanGe Kai C"),
}

BG, FG, LABEL, DIM, RULE = 252, 20, 105, 150, 210
COLS, CELL = 24, 96

CHECKLIST = [
    ("content", "错字 / 字形结构不对（含简繁码位）"),
    ("stroke", "断笔、粘连、毛刺"),
    ("weight", "字重突变（同一行忽粗忽细）"),
    ("small", "小字号糊 / 塌 / 缺笔画"),
    ("punct", "标点、空格位置"),
    ("seam", "真迹与合成接缝"),
]

PASSAGES = [
    ("《大學》首章（繁體）",
     "大學之道，在明明德，在親民，在止於至善。知止而后有定，定而后能靜，"
     "靜而后能安，安而后能慮，慮而后能得。"),
    ("《論語》學而（簡體碼位）",
     "学而时习之，不亦说乎？有朋自远方来，不亦乐乎？人不知而不愠，不亦君子乎？"),
    ("蘭亭集序（混排標點）",
     "永和九年，歲在癸丑，暮春之初，會于會稽山陰之蘭亭。群賢畢至，少長咸集。"),
]

STRATUM_ORDER = ["real", "gan_ep90", "gan_ep80", "gan", "gan_ht", "ribbon_fb", "punct"]
STRATUM_LABEL = {
    "real": "真跡 real",
    "gan": "GAN",
    "gan_ep90": "GAN（主 ep90）",
    "gan_ep80": "GAN（補位 ep80）",
    "gan_ht": "GAN（補位）",
    "ribbon_fb": "帶狀回退 ribbon",
    "punct": "標點 / 數字 / 空格",
}


# ---------------------------------------------------------------- helpers

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def load_cmap(font_path: Path) -> list[int]:
    f = TTFont(font_path, lazy=True)
    try:
        return sorted(f.getBestCmap())
    finally:
        f.close()


def family_of(font_path: Path) -> str:
    f = TTFont(font_path, lazy=True)
    try:
        return f["name"].getDebugName(1) or "?"
    finally:
        f.close()


def wrap(text: str, font: ImageFont.FreeTypeFont, max_w: float) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        if font.getlength(cur + ch) <= max_w:
            cur += ch
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def save_board(img: Image.Image, out: Path, board_id: str, boards: list) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    boards.append({
        "id": board_id,
        "file": out.name,
        "w": img.width,
        "h": img.height,
        "bytes": out.stat().st_size,
        "sha256": sha256_file(out),
    })
    print(f"   {out.name:22s} {img.width}x{img.height}  {out.stat().st_size/1e6:.2f} MB")


def footer(d: ImageDraw.ImageDraw, width: int, height: int, small) -> None:
    d.text((26, height - 34),
           "判定不是“看着行”：逐项过 content / stroke / weight / small / punct / seam；"
           "记录命令见 00_cover.png。",
           font=small, fill=DIM)


# ---------------------------------------------------------------- boards

def board_contact(out: Path, board_id: str, title: str, sub: str, chars: list[str],
                  font_path: Path, boards: list) -> None:
    label_font = ImageFont.truetype(str(BASE), 15)
    small = ImageFont.truetype(str(BASE), 11)
    glyph_font = ImageFont.truetype(str(font_path), CELL)

    pad, head = 26, 92
    rows = (len(chars) + COLS - 1) // COLS
    step = CELL + 22
    width = pad * 2 + COLS * CELL
    height = head + rows * step + 58

    img = Image.new("L", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.text((pad, 20), title, font=label_font, fill=FG)
    d.text((pad, 46), sub, font=small, fill=DIM)
    d.line((pad, 76, width - pad, 76), fill=RULE, width=1)

    for i, cp in enumerate(chars):
        ch = chr(cp)
        r, c = divmod(i, COLS)
        x = pad + c * CELL
        y = head + r * step
        d.text((x + CELL / 2, y + CELL * 0.82), ch, font=glyph_font, fill=FG, anchor="ms")
        d.text((x + CELL / 2, y + CELL + 2), f"U+{cp:04X}", font=small, fill=DIM, anchor="ma")

    footer(d, width, height, small)
    save_board(img, out, board_id, boards)


def board_strata(out: Path, board_id: str, prov: dict, font_path: Path,
                 seed: int, n: int, boards: list) -> None:
    buckets: dict[str, list[str]] = {}
    for ch, src in prov.items():
        buckets.setdefault(src, []).append(ch)
    keys = [k for k in STRATUM_ORDER if k in buckets]
    keys += [k for k in sorted(buckets) if k not in keys]

    label_font = ImageFont.truetype(str(BASE), 15)
    small = ImageFont.truetype(str(BASE), 11)
    glyph_font = ImageFont.truetype(str(font_path), CELL)
    ref_font = ImageFont.truetype(str(BASE), CELL)

    cols = min(n, max(len(buckets[k]) for k in keys))
    tag_w, pad, head = 150, 26, 92
    width = pad * 2 + tag_w + cols * CELL
    row_h = 24 + CELL
    height = head + len(keys) * (row_h * 2 + 18) + 58

    img = Image.new("L", (width, height), BG)
    d = ImageDraw.Draw(img)
    total = len(prov)
    d.text((pad, 20), "B3  按來源分層（每段上排 = 發布字體，下排 = 文楷參照）",
           font=label_font, fill=FG)
    d.text((pad, 46), f"共 {total:,} 字；同一行是同一批字，不同行不是同一批字。",
           font=small, fill=DIM)
    d.line((pad, 76, width - pad, 76), fill=RULE, width=1)

    y = head
    for key in keys:
        chars = sorted(buckets[key])
        picked = sorted(random.Random(seed).sample(chars, min(cols, len(chars))))
        d.text((pad, y), STRATUM_LABEL.get(key, key), font=label_font, fill=LABEL)
        d.text((pad, y + 20), f"{len(chars):,} 字  {100.0*len(chars)/total:.1f}%",
               font=small, fill=DIM)
        x = pad + tag_w
        for ch in picked:
            d.text((x + CELL / 2, y + CELL * 0.82), ch, font=glyph_font, fill=FG, anchor="ms")
            x += CELL
        y += row_h + 4

        d.text((pad, y + 4), "文楷（訓練源，僅參照）", font=small, fill=DIM)
        x = pad + tag_w
        for ch in picked:
            d.text((x + CELL / 2, y + CELL * 0.82), ch, font=ref_font, fill=DIM, anchor="ms")
            x += CELL
        y += row_h + 14
        d.line((pad, y - 6, width - pad, y - 6), fill=RULE, width=1)

    footer(d, width, height, small)
    save_board(img, out, board_id, boards)


def board_text(out: Path, board_id: str, font_path: Path, sizes: tuple[int, ...],
               boards: list) -> None:
    """Side-by-side WenKai / shipped, fixed passages, fixed sizes."""
    pad, col_w, gap = 26, 720, 34
    width = pad * 2 + col_w * 2 + gap
    label_font = ImageFont.truetype(str(BASE), 15)
    small = ImageFont.truetype(str(BASE), 11)
    line_h = {s: int(s * 1.6) for s in sizes}

    blocks = []
    for title, text in PASSAGES:
        for size in sizes:
            wk = ImageFont.truetype(str(BASE), size)
            gk = ImageFont.truetype(str(font_path), size)
            l1 = wrap(text, wk, col_w)
            l2 = wrap(text, gk, col_w)
            h = 30 + max(len(l1), len(l2)) * line_h[size] + 16
            blocks.append(dict(title=title, size=size, wk=wk, gk=gk, l1=l1, l2=l2, h=h))

    height = 92 + sum(b["h"] for b in blocks) + 58
    img = Image.new("L", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.text((pad, 20), f"{board_id}  實排對照：左 = 文楷（參照），右 = 發布字體", font=label_font, fill=FG)
    d.text((pad, 46), "固定三段文本；看錯字、斷筆、字重、標點位置，不是看“像不像”。",
           font=small, fill=DIM)
    d.line((pad, 76, width - pad, 76), fill=RULE, width=1)

    y = 92
    for b in blocks:
        size = b["size"]
        d.text((pad, y), b["title"], font=small, fill=LABEL)
        d.text((width - pad, y), f"{size}px", font=small, fill=LABEL, anchor="ra")
        y += 24
        d.line((pad + col_w + gap // 2, y - 4, pad + col_w + gap // 2, y + b["h"] - 30),
               fill=RULE, width=1)
        for lines, font, fill, x0 in ((b["l1"], b["wk"], DIM, pad),
                                      (b["l2"], b["gk"], FG, pad + col_w + gap)):
            yy = y + 2
            for line in lines:
                d.text((x0, yy), line, font=font, fill=fill)
                yy += line_h[size]
        y += b["h"]
        d.line((pad, y - 8, width - pad, y - 8), fill=RULE, width=1)

    footer(d, width, height, small)
    save_board(img, out, board_id, boards)


def board_small(out: Path, board_id: str, font_path: Path, boards: list) -> None:
    """12/16 px at 2x nearest: the raster the user actually sees at body size."""
    sizes, take = (12, 16), 28
    pad, tag_w = 26, 96
    label_font = ImageFont.truetype(str(BASE), 15)
    small = ImageFont.truetype(str(BASE), 11)

    rows = [(size, p) for size in sizes for p in range(2)]
    row_h = max(sizes) * 2 + 26
    col_w = take * max(sizes) + 30
    width = pad * 2 + tag_w + 2 * col_w
    height = 92 + len(rows) * row_h + 66
    img = Image.new("L", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.text((pad, 20), f"{board_id}  小字號像素真值（12/16px 渲染後 2× nearest 放大）",
           font=label_font, fill=FG)
    d.text((pad, 46), "放大只為看清筆畫是否糊/斷；不代表屏幕觀感。左 = 文楷，右 = 發布字體。",
           font=small, fill=DIM)
    d.line((pad, 76, width - pad, 76), fill=RULE, width=1)

    y = 92
    for size, p in rows:
        title, text = PASSAGES[p]
        s = text[:take]
        wk = ImageFont.truetype(str(BASE), size)
        gk = ImageFont.truetype(str(font_path), size)
        d.text((pad, y + 4), f"{size}px", font=small, fill=LABEL)
        d.text((pad, y + 22), f"段{p+1}", font=small, fill=DIM)
        x = pad + tag_w
        for font, fill in ((wk, DIM), (gk, FG)):
            strip = Image.new("L", (col_w - 10, size * 2), BG)
            ImageDraw.Draw(strip).text((8, int(size * 1.35)), s, font=font, fill=fill)
            img.paste(strip, (x, y))
            x += col_w
        y += row_h
        d.line((pad, y - 8, width - pad, y - 8), fill=RULE, width=1)

    footer(d, width, height, small)
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    save_board(img, out, board_id, boards)


def board_diff(out: Path, board_id: str, font_path: Path, prev_path: Path,
               chars: list[int], prev_cmap: set[int], boards: list, top: int = 60) -> None:
    """Per-glyph ink/bbox delta vs the previous release; only the movers."""
    cur = ImageFont.truetype(str(font_path), 64)
    old = ImageFont.truetype(str(prev_path), 64)

    def stat(font, ch):
        im = Image.new("L", (72, 72), 0)
        ImageDraw.Draw(im).text((36, 58), ch, font=font, fill=255, anchor="ms")
        ink = float(np.asarray(im, dtype=np.float32).sum() / 255.0)
        bb = im.point(lambda v: 255 if v > 64 else 0).getbbox()
        w, h = (bb[2] - bb[0], bb[3] - bb[1]) if bb else (0, 0)
        return ink, w, h

    rows = []
    for cp in chars:
        if cp not in prev_cmap:
            continue
        ch = chr(cp)
        i1, w1, _ = stat(old, ch)
        if i1 <= 0:
            continue
        i2, w2, _ = stat(cur, ch)
        rows.append((abs((i2 - i1) / i1), (i2 - i1) / i1, w2 - w1, ch, i1, i2))
    rows.sort(reverse=True)
    movers = rows[:top]
    changed = sum(1 for r in rows if abs(r[1]) > 0.05)

    pad, head = 26, 92
    width = 1180
    row_h = 76
    height = head + len(movers) * row_h + 58
    img = Image.new("L", (width, height), BG)
    d = ImageDraw.Draw(img)
    label_font = ImageFont.truetype(str(BASE), 15)
    small = ImageFont.truetype(str(BASE), 11)
    glyph = ImageFont.truetype(str(prev_path), 54)
    glyph2 = ImageFont.truetype(str(font_path), 54)

    d.text((pad, 20), f"{board_id}  回歸 diff：{prev_path.name} → {font_path.name}",
           font=label_font, fill=FG)
    d.text((pad, 46), f"墨量變化 >5% 的字共 {changed:,} 個（全量 {len(chars):,} 字）；"
                      f"下表按 |Δ墨量| 取前 {len(movers)}。", font=small, fill=DIM)
    d.line((pad, 76, width - pad, 76), fill=RULE, width=1)

    y = head
    for _, dink, dw, ch, i1, i2 in movers:
        d.text((pad + 30, y + 52), ch, font=glyph, fill=DIM, anchor="ms")
        d.text((pad + 120, y + 52), ch, font=glyph2, fill=FG, anchor="ms")
        d.text((pad + 210, y + 24), f"{ch}  U+{ord(ch):04X}", font=label_font, fill=FG)
        d.text((pad + 210, y + 46),
               f"墨量 {i1:6.1f} → {i2:6.1f}   Δ {dink*100:+6.1f}%   寬 {dw:+d}px",
               font=small, fill=LABEL)
        y += row_h

    footer(d, width, height, small)
    save_board(img, out, board_id, boards)


def board_cover(out: Path, meta: dict, boards: list) -> None:
    label_font = ImageFont.truetype(str(BASE), 18)
    small = ImageFont.truetype(str(BASE), 13)
    width, height = 1180, 780
    img = Image.new("L", (width, height), BG)
    d = ImageDraw.Draw(img)

    y = 30
    d.text((26, y), f"{meta['line']} 線視覺驗收板  ·  {meta['family']}", font=label_font, fill=FG)
    y += 34
    d.text((26, y), f"字體 {meta['font_path']}", font=small, fill=DIM); y += 20
    d.text((26, y), f"sha256 {meta['sha256']}", font=small, fill=DIM); y += 20
    d.text((26, y), f"字數 {meta['cmap']:,}   生成 {meta['generated_at']}   seed {meta['seed']}",
           font=small, fill=DIM); y += 30

    d.text((26, y), "看什麼（每項只能勾 pass / fail）", font=label_font, fill=FG); y += 30
    for _, text in CHECKLIST:
        d.text((39, y), f"□ {text}", font=small, fill=LABEL); y += 24

    y += 14
    d.text((26, y), "怎麼判", font=label_font, fill=FG); y += 30
    for line in [
        "1. 先看 B1/B2 掃錯字與斷筆；再看 B3 確認最弱的 ribbon 行沒有惡化；",
        "2. B4 看正常閱讀大小，B5 只看 12/16px 是否糊、塌、缺筆；",
        "3. 有上一版就必須看 B6，只審 |Δ墨量| 前 60 字，不回看全量；",
        "4. 結論寫回：python3 scripts/100_review.py --line A --record pass --notes \"...\"",
        "   fail 時用 --fail small,stroke 指明哪項不過；--check 只有 pass 返回 0。",
    ]:
        d.text((39, y), line, font=small, fill=DIM); y += 24

    y += 14
    d.text((26, y), "本目錄的板", font=label_font, fill=FG); y += 30
    for b in boards:
        d.text((39, y), f"{b['id']:14s} {b['file']}", font=small, fill=LABEL); y += 22

    d.text((26, height - 34),
           "本文件由 scripts/100_review.py 生成，請勿手改；版本與判定見 manifest.json / verdicts.jsonl。",
           font=small, fill=DIM)
    save_board(img, out, "00", boards)


# ---------------------------------------------------------------- verdicts

def verdicts_path(out_root: Path) -> Path:
    return out_root / "verdicts.jsonl"


def latest_verdict(out_root: Path, sha8: str) -> dict | None:
    p = verdicts_path(out_root)
    if not p.exists():
        return None
    found = None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("sha8") == sha8:
            found = rec
    return found


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="fixed review boards + human verdict log")
    ap.add_argument("--line", default="A", choices=sorted(PRESETS))
    ap.add_argument("--font")
    ap.add_argument("--provenance")
    ap.add_argument("--clean", help="npz with a 'chars' array (default work/pairs_single.npz)")
    ap.add_argument("--out", default=str(ROOT / "work" / "review"))
    ap.add_argument("--seed", type=int, default=20992)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--prev", help="previous release TTF, for B6 regression diff")
    ap.add_argument("--record", choices=["pass", "fail", "known"],
                    help="append a verdict for the current font instead of drawing")
    ap.add_argument("--fail", default="", help="comma-separated checklist ids that failed")
    ap.add_argument("--notes", default="")
    ap.add_argument("--reviewer", default="owner")
    ap.add_argument("--check", action="store_true",
                    help="exit 0 only if the current font has a pass verdict")
    ap.add_argument("--no-text", action="store_true")
    ap.add_argument("--no-diff", action="store_true")
    args = ap.parse_args()

    preset = PRESETS[args.line]
    font_path = Path(args.font) if args.font else ROOT / preset["font"]
    prov_path = Path(args.provenance) if args.provenance else ROOT / preset["prov"]
    out_root = Path(args.out)

    if not font_path.exists():
        raise SystemExit(f"ABORT: 缺字體 {rel(font_path)}（先跑 11_build_full.py）")
    if not prov_path.exists():
        raise SystemExit(f"ABORT: 缺 provenance {rel(prov_path)}（先跑 14_package.py）")

    sha = sha256_file(font_path)
    sha8 = sha[:8]
    outdir = out_root / sha8

    if args.check:
        rec = latest_verdict(out_root, sha8)
        if rec and rec["verdict"] == "pass":
            print(f"REVIEW OK  {rel(font_path)}  {sha8}  by {rec['reviewer']} @ {rec['ts']}")
            return 0
        if rec:
            print(f"REVIEW {rec['verdict'].upper()}  {rel(font_path)}  {sha8}  "
                  f"fails={rec.get('failed')}  notes={rec.get('notes')!r}")
        else:
            print(f"REVIEW MISSING  {rel(font_path)}  {sha8}  "
                  f"先跑：python3 scripts/100_review.py --line {args.line}")
        return 1

    if args.record:
        if not outdir.exists():
            raise SystemExit(f"ABORT: 還沒有 {rel(outdir)} 的板；先出板再記判定")
        fails = [x.strip() for x in args.fail.split(",") if x.strip()]
        unknown = [x for x in fails if x not in {c for c, _ in CHECKLIST}]
        if unknown:
            raise SystemExit(f"ABORT: 未知檢查項 {unknown}；可選 {[c for c, _ in CHECKLIST]}")
        rec = {
            "ts": now(),
            "sha8": sha8,
            "sha256": sha,
            "font": rel(font_path),
            "line": args.line,
            "verdict": args.record,
            "failed": fails,
            "checklist": {c: (c not in fails) for c, _ in CHECKLIST},
            "notes": args.notes,
            "reviewer": args.reviewer,
            "boards": rel(outdir),
        }
        out_root.mkdir(parents=True, exist_ok=True)
        with open(verdicts_path(out_root), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"RECORDED {args.record}  {sha8}  {rel(verdicts_path(out_root))}")
        if args.record != "pass":
            print(f"   failed: {fails or '（未指明，建議用 --fail 標出哪一項）'}")
        return 0

    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    cmap = load_cmap(font_path)
    family = family_of(font_path)
    counts: dict[str, int] = {}
    for src in prov.values():
        counts[src] = counts.get(src, 0) + 1

    outdir.mkdir(parents=True, exist_ok=True)
    boards: list[dict] = []

    print(f"review {args.line}  {rel(font_path)}  sha8={sha8}  -> {rel(outdir)}")

    sample = sorted(random.Random(args.seed).sample(cmap, min(args.n, len(cmap))))
    board_contact(outdir / f"B1_random{len(sample)}.png", "B1",
                  f"B1  全量隨機 {len(sample)} 字（固定 seed）",
                  f"{rel(font_path)}  {family}  ·  seed {args.seed}  ·  {len(cmap):,} 字中抽樣",
                  sample, font_path, boards)

    clean_path = Path(args.clean) if args.clean else ROOT / "work" / "pairs_single.npz"
    if clean_path.exists():
        d = np.load(clean_path, allow_pickle=True)
        clean = sorted(int(ord(c)) for c in d["chars"].tolist())
        board_contact(outdir / f"B2_clean{len(clean)}.png", "B2",
                      f"B2  泛化集 {len(clean)} 字（只出現一次，從未訓練）",
                      "直接看模型沒見過的字；這一板差 = 模型差，不是抽樣倒楣。",
                      clean, font_path, boards)
    else:
        print("   B2 skipped: work/pairs_single.npz missing")

    board_strata(outdir / "B3_strata.png", "B3", prov, font_path, args.seed, 20, boards)

    if not args.no_text:
        board_text(outdir / "B4_text-large.png", "B4", font_path, (24, 48), boards)
        board_small(outdir / "B5_text-small.png", "B5", font_path, boards)

    prev_path = Path(args.prev) if args.prev else None
    if prev_path and prev_path.exists() and not args.no_diff:
        board_diff(outdir / "B6_diff.png", "B6", font_path, prev_path, cmap,
                   set(load_cmap(prev_path)), boards)
    elif args.prev:
        print(f"   B6 skipped: {args.prev} 不存在")

    meta = {
        "line": args.line,
        "family": family,
        "font_path": rel(font_path),
        "sha256": sha,
        "sha8": sha8,
        "cmap": len(cmap),
        "seed": args.seed,
        "generated_at": now(),
    }
    board_cover(outdir / "00_cover.png", meta, boards)

    manifest = {
        "schema": 1,
        "script": "scripts/100_review.py",
        "script_sha256": sha256_file(Path(__file__)),
        "generated_at": meta["generated_at"],
        "line": args.line,
        "font": {"path": rel(font_path), "family": family, "sha256": sha,
                 "bytes": font_path.stat().st_size},
        "provenance": {"path": rel(prov_path), "counts": counts},
        "cmap": len(cmap),
        "seed": args.seed,
        "boards": boards,
        "checklist": [{"id": c, "label": t} for c, t in CHECKLIST],
        "passages": [t for t, _ in PASSAGES],
        "prev": rel(prev_path) if prev_path else None,
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n{len(boards)} boards -> {rel(outdir)}")
    print(f"判定：python3 scripts/100_review.py --line {args.line} --record pass --notes \"...\"")
    print(f"閘門：python3 scripts/100_review.py --line {args.line} --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
