"""B-line: render the specimen sheet for GuanGeKai-B.

Forked from `12_specimen.py`: 史記 text, B-line caption, B font default.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-B-Regular.ttf"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "images" / "specimen-b.png"))
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
    d.text((w + 14, 62), "GuanGe Kai B", font=ImageFont.truetype(str(BASE), 34), fill="#555")
    d.text((60, 130),
           "明抄本《史記》（舊傳姜立綱）　新加坡國立大學圖書館藏本　"
           "CJK 基本區 U+4E00–U+9FFF　20,992 字",
           font=f_caption, fill="#444")

    body = [
        "項羽乃悉引兵渡河皆沈船破釜甑燒廬舍持三日糧",
        "以示士卒必死無還心於是至則圍王離與秦軍遇九戰",
        "絕其甬道大破之殺蘇角虜王離涉閒不降楚自燒殺",
        "太史公曰詩有之高山仰止景行行止雖不能至然心鄉往之",
        "余讀孔氏書想見其為人適魯觀仲尼廟堂車服禮器",
        "諸生以時習禮其家余祗回留之不能去云天下君王",
        "至于賢人眾矣當時則榮沒則已焉孔子布衣傳十餘世",
        "學者宗之自天子王侯中國言六藝者折中於夫子可謂至聖矣",
    ]
    y = 200
    for line in body:
        d.text((60, y), line, font=f_text, fill="black")
        y += 66
    d.text((60, y + 14), "墨筆抄本 · 起收分明 · 血肉停勻 · 真跡與生成字混排",
           font=f_caption, fill="#444")
    y += 66
    for s, lab in [(16, "小字"), (20, "小字"), (24, "正文"), (32, "正文"), (48, "標題")]:
        f = ImageFont.truetype(args.font, s)
        d.text((60, y), lab, font=ImageFont.truetype(str(BASE), 14), fill="#888")
        d.text((112, y - s * 0.15), "項羽乃悉引兵渡河皆沈船破釜甑燒廬舍持三日糧", font=f, fill="black")
        y += s + 18
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.crop((0, 0, W, min(H, y + 30))).save(args.out)
    print("specimen ->", args.out)


if __name__ == "__main__":
    main()
