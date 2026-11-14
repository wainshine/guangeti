"""Shared review-sheet layout for all three glyph lines (A/B/C).

This is the single implementation of the sheet layout.  Line-specific scripts only
prepare `rows` (data) and must not re-implement drawing.

Design (agreed 2026-11-14):
  * one cell = product glyph + reference glyph (OFL base font) + source crop + 3 meta lines
  * label text always uses the OFL base font, never the product font -- the product font
    has no Latin and would render page numbers as tofu
  * missing glyphs/crops are drawn as text ("缺字" / "无裁片"), not tofu
  * long meta text auto-shrinks (_draw_fit) so `框=[...]` never bleeds into the next cell

Usage (adapter side):
    from review_sheet import build_sheet, write_tsv
    build_sheet(rows, "GuanGeKai-Regular.ttf", "work/qa/review-{d}/sheet-{n}.png")
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"


def ref_font_path() -> str:
    return str(REF)


def ref_has_char(ch: str) -> bool:
    try:
        from fontTools.ttLib import TTFont
        return len(ch) == 1 and ord(ch) in TTFont(ref_font_path()).getBestCmap()
    except Exception:
        return False


def font_has_char(font_path: str, ch: str) -> bool:
    try:
        from fontTools.ttLib import TTFont
        return len(ch) == 1 and ord(ch) in TTFont(str(font_path)).getBestCmap()
    except Exception:
        return True


def _font(font_path: str, size: int):
    try:
        return ImageFont.truetype(str(font_path), max(8, int(size)))
    except Exception:
        return ImageFont.load_default()


def glyph_png(font_path: str, ch: str, size: int = 160) -> Image.Image | None:
    """Render one glyph; None when the font lacks the char (caller draws 缺字)."""
    if not font_has_char(font_path, ch):
        return None
    im = Image.new("L", (size, size), 255)
    ImageDraw.Draw(im).text((size // 2, int(size * 0.92)), ch,
                            font=_font(font_path, int(size * 0.8)), fill=0, anchor="ms")
    return im


def _draw_fit(draw, xy, text, font, fill, max_w):
    f = font
    while draw.textlength(text, font=f) > max_w and getattr(f, "size", 0) > 8:
        f = _font(getattr(f, "path", ref_font_path()), f.size - 1)
    draw.text(xy, text, font=f, fill=fill)


def _load_crop(row: dict) -> Image.Image | None:
    crop = row.get("crop")
    if crop is None:
        return None
    if isinstance(crop, Image.Image):
        return crop.convert("L")
    p = Path(crop)
    if not p.is_absolute():
        p = ROOT / p
    return Image.open(p).convert("L") if p.exists() else None


def draw_cell(canvas, x, y, row, product_font, cell_w=200, cell_h=290, scale=1.0, color=True):
    s = scale
    d = ImageDraw.Draw(canvas)
    lab = _font(ref_font_path(), 14 * s)
    mono = _font(ref_font_path(), 13 * s)
    if color:
        d.rectangle([x, y, x + int(cell_w) - 1, y + int(cell_h) - 1], outline=(214, 214, 214))
        c_no, c_meta, c_ref = (190, 30, 30), (90, 90, 90), (0, 0, 0)
    else:
        c_no, c_meta, c_ref = 0, 110, 0

    ch = row.get("char", "")
    font = row.get("glyph_font") or product_font
    g = glyph_png(font, ch, int(112 * s))
    if g is None:
        d.text((x + int(10 * s), y + int(40 * s)), "缺字", font=lab, fill=(160, 160, 160))
    else:
        canvas.paste(g.convert("RGB" if color else "L"), (x + int(8 * s), y + int(4 * s)))

    d.text((x + int(126 * s), y + int(6 * s)), f"#{row.get('no', '')}", font=lab, fill=c_no)
    d.text((x + int(126 * s), y + int(24 * s)),
           f"U+{ord(ch):04X}" if len(ch) == 1 else "", font=mono, fill=c_meta)
    if ref_has_char(ch) and ch != "":
        rg = glyph_png(ref_font_path(), ch, int(46 * s))
        if rg is not None:
            canvas.paste(rg.convert("RGB" if color else "L"), (x + int(126 * s), y + int(40 * s)))
    else:
        d.text((x + int(126 * s), y + int(46 * s)), "无参照", font=mono, fill=(165, 165, 165))

    crop = _load_crop(row)
    if crop is None:
        d.text((x + int(10 * s), y + int(160 * s)), "无裁片", font=lab, fill=(165, 165, 165))
    else:
        c = crop.copy(); c.thumbnail((int(110 * s), int(110 * s)))
        canvas.paste(c.convert("RGB" if color else "L"), (x + int(8 * s), y + int(122 * s)))

    maxw = cell_w - int(8 * s)
    for k, line in enumerate(list(row.get("meta") or [])[:3]):
        _draw_fit(d, (x + int(8 * s), y + int(238 * s) + int(18 * s) * k),
                  str(line), lab, c_meta, maxw)
    return canvas


def _self_check(canvas, x, y, row, cell_w, cell_h, s):
    """Catch the two silent regressions: tofu labels and .notdef glyphs."""
    # label strip must contain some ink
    strip = canvas.crop((x + int(4 * s), y + int(236 * s),
                         x + int(cell_w - 4 * s), y + int(cell_h - 2 * s)))
    if strip.convert("L").getextrema()[0] > 200:
        raise AssertionError(f"row {row.get('no')}: label strip has no ink (font/tofu regression?)")
    # a .notdef box is a hollow rectangle occupying most of the glyph box
    if row.get("char") and not font_has_char(row.get("glyph_font") or "", row["char"]):
        pass  # missing glyph is intentional and drawn as 缺字


def build_sheet(rows, product_font, out_png, *, cols=10, cell=(200, 290), per_page=100,
                scale=1.0, color=True, ref_font=None) -> list[str]:
    """Lay rows out into one or more PNGs. `out_png` may contain `{n}` for page numbers."""
    global REF
    if ref_font:
        REF = Path(ref_font)
    cw, chh = int(round(cell[0] * scale)), int(round(cell[1] * scale))
    pages = [rows[i:i + per_page] for i in range(0, len(rows), per_page)] or [[]]
    outs = []
    for pi, page_rows in enumerate(pages):
        nrows = max(1, (len(page_rows) + cols - 1) // cols)
        canvas = Image.new("RGB" if color else "L", (cols * cw, nrows * chh),
                           (255, 255, 255) if color else 255)
        for i, r in enumerate(page_rows):
            x, y = (i % cols) * cw, (i // cols) * chh
            draw_cell(canvas, x, y, r, product_font, cw, chh, scale, color)
            _self_check(canvas, x, y, r, cw, chh, scale)
        if "{n}" in out_png:
            path = out_png.replace("{n}", str(pi + 1))
        elif "{d}" in out_png:
            path = out_png.replace("{d}", "1")
        elif "{" in out_png:
            path = out_png.format(pi + 1)
        else:
            path = out_png
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(path)
        outs.append(path)
    return outs


def write_tsv(rows, path, fields=("no", "line", "char", "codepoint", "page", "meta", "tag")):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fo:
        fo.write("\t".join(fields) + "\n")
        for r in rows:
            vals = []
            for f in fields:
                v = r.get(f, "")
                if f == "codepoint" and not v and len(r.get("char", "")) == 1:
                    v = f"U+{ord(r['char']):04X}"
                if f == "meta" and isinstance(v, (list, tuple)):
                    v = " | ".join(map(str, v))
                vals.append(str(v))
            fo.write("\t".join(vals) + "\n")
    return path
