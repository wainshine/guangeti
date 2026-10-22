"""Render a specimen sheet and verify the built font."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-Regular.ttf"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "images" / "specimen.png"))
    args = ap.parse_args()

    W, H = 1800, 1400
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(args.font, 72)
    f_text = ImageFont.truetype(args.font, 40)
    f_small = ImageFont.truetype(args.font, 22)
    f_caption = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), 18)

    d.text((60, 40), "館閣楷", font=f_title, fill="black")
    w, _ = d.textbbox((60, 40), "館閣楷", font=f_title)[2:]
    d.text((60 + (w - 60) + 18, 62), "GuanGe Kai", font=ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), 34), fill="#555")
    d.text((60, 130), "明代《四書白文》刻本　館閣體　CJK 基本區 U+4E00–U+9FFF　20,992 字", font=f_caption, fill="#444")

    body = [
        "子曰學而時習之不亦說乎有朋自遠方來不亦樂乎",
        "人不知而不慍不亦君子乎有子曰其為人也孝弟而",
        "好犯上者鮮矣不好犯上而好作亂者未之有也",
        "君子務本本立而道生孝弟也者其為仁之本與",
        "大學之道在明明德在親民在止於至善",
        "天命之謂性率性之謂道修道之謂教",
        "孟子見梁惠王王曰叟不遠千里而來亦將有以利吾國乎",
    ]
    y = 200
    for line in body:
        d.text((60, y), line, font=f_text, fill="black")
        y += 66
    d.text((60, y + 20), "方正結構 · 橫細豎粗 · 起收分明 · 血肉停勻",
           font=f_caption, fill="#444")
    y += 70
    sizes = [(16, "小字"), (20, "小字"), (24, "正文"), (32, "正文"), (48, "標題")]
    for s, lab in sizes:
        f = ImageFont.truetype(args.font, s)
        d.text((60, y), lab, font=ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), 14), fill="#888")
        d.text((112, y - s * 0.15), "學而時習之不亦說乎有朋自遠方來不亦樂乎", font=f, fill="black")
        y += s + 18
    img.crop((0, 0, W, min(H, y + 30))).save(args.out)
    print("specimen ->", args.out)


if __name__ == "__main__":
    main()
