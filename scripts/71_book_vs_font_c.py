"""C-line: build the static 「原書 vs 字型」 comparison figure for the release.

Left  : a crop of a 永樂大典 leaf (colour scan).
Right : the same passage typeset vertically with GuanGeKai-C.

The two are *not* pixel-aligned: the leaf was written by hand, the right side is
typeset, so column heights and breaks differ.  The point is the pen: 起收筆、轉折、
字距.  This is a curated asset (like `book-vs-font.png` / `book-vs-font-b.jpg`), not
something the release pipeline regenerates silently.

  python3 scripts/71_book_vs_font_c.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
CORPUS = ROOT / "永乐大典美国藏本"

# 卷10934 楚字（p00_0005）右起前六欄，據原頁校讀
LINES = [
    "楚自微而浸盛楚方盛而已衰蓋蠻夷之強未有久而不替者也",
    "常也霍於近楚之小國然終桓之世不得與中國之盟會宋襄繼伯謀之",
    "不臧齊之盟楚始得與又明年鹿上之事宋實要之然齊之盟猶書人而",
    "列於陳蔡之下鹿上之會猶不先齊宋也至孟之會儼然位楚子於陳蔡",
    "之上執宋公以伐宋獻宋捷以威魯執宋公敗宋師圍陳納頓偃然",
    "諸侯之上執義以正諸夏二十七年會陳蔡以圍宋故特書人以貶之",
    "位楚子於陳蔡之上執宋公以伐宋獻宋捷以威魯執宋公敗宋師",
    "圍陳納頓偃然諸侯之上執義以正諸夏二十七年會陳蔡以圍宋",
    "故特書人以貶之幸而晉文城濮戰敗氣歐始消三十二年而鬪章",
    "如晉處父報之晉楚始通文公為之執義以正諸夏可謂盛矣",
    "宋會魯平宋此楚莊之成伯也成二年陽橋之役以區區嬰齊而合十二",
    "義聖人予之豈得已哉明年于邲之敗為中國羞楚於是乎大張滅蕭圍",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-C-Regular.ttf"))
    ap.add_argument("--key", default="p00_0005")
    ap.add_argument("--out", default=str(ROOT / "docs" / "images" / "book-vs-font-c.jpg"))
    args = ap.parse_args()
    stats = {json.loads(l)["key"]: json.loads(l) for l in open(WORK / "page_stats.jsonl")}
    st = stats[args.key]
    doc = pymupdf.open(CORPUS / st["book"])
    pix = doc[st["page"]].get_pixmap(dpi=300)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)[:, :, :3].copy()
    doc.close()
    M = cv2.getRotationMatrix2D((rgb.shape[1] / 2, rgb.shape[0] / 2), st["angle"], 1.0)
    rgb = cv2.warpAffine(rgb, M, (rgb.shape[1], rgb.shape[0]),
                         flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    # crop the six right-most text columns using the OCR boxes where possible
    lines = [json.loads(l) for l in open(WORK / "ocr_v6.jsonl") if args.key in l]
    x0, x1 = int(rgb.shape[1] * 0.42), int(rgb.shape[1] * 0.95)
    y0, y1 = int(rgb.shape[0] * 0.25), int(rgb.shape[0] * 0.78)
    left = rgb[y0:y1, x0:x1]
    # scale the book crop to a common height
    H = 1500
    left = cv2.resize(left, (int(left.shape[1] * H / left.shape[0]), H),
                      interpolation=cv2.INTER_AREA)

    S = 40                       # px per character on the typeset side
    W2 = 820
    right = Image.new("RGB", (W2, H), (247, 244, 236))
    d = ImageDraw.Draw(right)
    font = ImageFont.truetype(args.font, S)
    x = W2 - 40
    for line in LINES:
        y = 80
        for ch in line:
            d.text((x, y), ch, font=font, fill=(25, 22, 20))
            y += int(S * 1.30)
        x -= int(S * 1.55)
    # caption strip
    cap = Image.new("RGB", (left.shape[1] + W2, 60), "white")
    dc = ImageDraw.Draw(cap)
    f = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 22)
    dc.text((20, 18), "原書：明嘉靖隆慶間內府重寫本《永樂大典》卷10934（美國國會圖書館藏）",
            font=f, fill=(40, 40, 40))
    dc.text((left.shape[1] + 30, 18), "右：同一段文字用 GuanGeKai-C 排版", font=f, fill=(40, 40, 40))
    canvas = Image.new("RGB", (left.shape[1] + W2, H + 60), "white")
    canvas.paste(Image.fromarray(left), (0, 60))
    canvas.paste(right, (left.shape[1], 60))
    canvas.paste(cap, (0, 0))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out, quality=92)
    print("wrote", args.out, canvas.size)


if __name__ == "__main__":
    main()
