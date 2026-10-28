"""C-line: render the specimen sheet for GuanGeKai-C.

Forked from `66_specimen_b.py`: 《永乐大典》 text (卷10934 楚字), C-line caption,
C font default.  The body is transcribed from the leaf, not from a modern edition.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-C-Regular.ttf"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "images" / "specimen-c.png"))
    args = ap.parse_args()

    W, H = 1800, 1500
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(args.font, 72)
    f_text = ImageFont.truetype(args.font, 40)
    f_caption = ImageFont.truetype(str(BASE), 18)

    # the font has no Latin glyphs, so the Latin part must NOT go through it
    d.text((60, 40), "館閣楷", font=f_title, fill="black")
    w = d.textbbox((60, 40), "館閣楷", font=f_title)[2]
    d.text((w + 14, 62), "GuanGe Kai C", font=ImageFont.truetype(str(BASE), 34), fill="#555")
    d.text((60, 130),
           "明嘉靖隆慶間內府重寫本《永樂大典》　美國國會圖書館藏本　"
           "CJK 基本區 U+4E00–U+9FFF　20,992 字",
           font=f_caption, fill="#444")

    body = [
        "楚自微而浸盛楚方盛而已衰蓋蠻夷之強未有久而不替者也",
        "常也霍於近楚之小國然終桓之世不得與中國之盟會宋襄繼伯",
        "謀之不臧齊之盟楚始得與又明年鹿上之事宋實要之然齊之盟",
        "猶書人而列於陳蔡之下鹿上之會猶不先齊宋也至孟之會儼然",
        "位楚子於陳蔡之上執宋公以伐宋獻宋捷以威魯執宋公敗宋師",
        "圍陳納頓偃然諸侯之上執義以正諸夏二十七年會陳蔡以圍宋",
        "故特書人以貶之幸而晉文城濮戰敗氣歐始消三十二年而鬪章",
        "如晉處父報之晉楚始通文公為之執義以正諸夏可謂盛矣",
    ]
    y = 200
    for line in body:
        d.text((60, y), line, font=f_text, fill="black")
        y += 66
    d.text((60, y + 14), "明內府重寫本 · 起收分明 · 行筆自然 · 真跡字",
           font=f_caption, fill="#444")
    y += 66
    for s, lab in [(16, "小字"), (20, "小字"), (24, "正文"), (32, "正文"), (48, "標題")]:
        f = ImageFont.truetype(args.font, s)
        d.text((60, y), lab, font=ImageFont.truetype(str(BASE), 14), fill="#888")
        d.text((112, y - s * 0.15), "楚自微而浸盛楚方盛而已衰蓋蠻夷之強", font=f, fill="black")
        y += s + 18
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.crop((0, 0, W, min(H, y + 30))).save(args.out)
    print("specimen ->", args.out)


if __name__ == "__main__":
    main()
