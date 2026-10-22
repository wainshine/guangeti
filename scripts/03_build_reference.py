"""Build the canonical Four Books reference text (traditional, punctuation stripped)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]
CAN = ROOT / "data" / "canonical"
OUT = ROOT / "data" / "reference"
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def clean(s: str) -> str:
    return "".join(ch for ch in s if CJK.match(ch))


def main():
    cc = OpenCC("s2t")
    OUT.mkdir(parents=True, exist_ok=True)
    blocks = []

    # Book order: 論語 → 大學 → 中庸 → 孟子
    lunyu = json.load(open(CAN / "lunyu.json"))
    for chap in lunyu:
        text = "".join(chap["paragraphs"])
        blocks.append((f"論語·{chap['chapter']}", clean(cc.convert(text))))

    for name, fn in [("大學", "daxue.json"), ("中庸", "zhongyong.json")]:
        d = json.load(open(CAN / fn))
        text = "".join(d["paragraphs"])
        blocks.append((name, clean(cc.convert(text))))

    # 孟子 14 篇
    mengzi = json.load(open(CAN / "mengzi.json"))
    for chap in mengzi:
        text = "".join(chap["paragraphs"])
        blocks.append((f"孟子·{chap['chapter']}", clean(cc.convert(text))))

    with open(OUT / "reference.txt", "w") as f:
        pos = 0
        for name, text in blocks:
            f.write(f"@{name}\t{pos}\n")
            f.write(text + "\n")
            pos += len(text)
    total = sum(len(t) for _, t in blocks)
    print("reference chars:", total, "blocks:", len(blocks), "->", OUT / "reference.txt")


if __name__ == "__main__":
    main()
