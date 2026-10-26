"""Build the B-line reference text (public-domain 《史記》) for OCR alignment.

Input : data/reference-b/shiji_raw.txt   (see docs/DATA-B.md §2 for provenance)
Output: data/reference-b/reference.txt   `@<卷>\t<offset>` headers + CJK-only body

The reference is used *only* as an alignment target for the OCR transcripts.  It is
never embedded in the font and no characters are taken from it: the glyphs always
come from the scan.  Punctuation and editorial notes are dropped, so only the
public-domain character sequence survives.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "reference-b" / "shiji_raw.txt"
OUT = ROOT / "data" / "reference-b" / "reference.txt"

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def main():
    text = SRC.read_text(encoding="utf-8")
    parts = re.split(r"^##\s*(.+)$", text, flags=re.M)
    out, pos, nsec, total = [], 0, 0, 0
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        cjk = "".join(ch for ch in body if CJK.match(ch))
        if not cjk:
            continue                       # the ten 表 are tables, not running text
        out.append(f"@{name}\t{pos}")
        out.append(cjk)
        pos += len(cjk)
        nsec += 1
        total += len(cjk)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"sections {nsec}  cjk chars {total}  -> {OUT}")
    print("unique chars", len(set("".join(out[1::2]))))


if __name__ == "__main__":
    main()
