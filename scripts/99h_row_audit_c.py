"""Row audit: cells-per-line vs OCR chars-per-line, with *both* join semantics.

`li` in cells.jsonl indexes 93.dedupe_boxes(ocr_v6[key]) — NOT the raw OCR list
(dedupe_boxes drops overlapping boxes and re-sorts by area).  The RAW number is
kept only as a comparison; the DEDUPE number is the production definition.

  python3 scripts/99h_row_audit_c.py
"""
from __future__ import annotations
import json, re, collections, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def cjk(s):
    return "".join(c for c in s if CJK.match(c))


def load_dedupe():
    spec = importlib.util.spec_from_file_location("segc", ROOT / "scripts" / "93_segment_c.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.dedupe_boxes


def main():
    dedupe_boxes = load_dedupe()
    v6 = {}
    for l in open(ROOT / "work-c" / "ocr_v6.jsonl"):
        r = json.loads(l)
        v6[r["key"]] = r["lines"]
    cells = collections.defaultdict(list)
    for l in open(ROOT / "work-c" / "cells.jsonl"):
        r = json.loads(l)
        cells[(r["key"], r["li"])].append(r)
    total_cells = sum(len(v) for v in cells.values())

    # DEDUPE (production): li indexes the deduped, area-sorted list
    dedupe_rows = 0
    dedupe_mismatch = 0
    dedupe_cells = 0
    dedupe_nocell = 0
    sub_mismatch = 0
    sub_cells = 0
    for key, raw in v6.items():
        for li, ln in enumerate(dedupe_boxes(raw)):
            N = len(cjk(ln["text"]))
            if not N:
                continue
            cs = cells.get((key, li), [])
            if not cs:
                dedupe_nocell += 1
                continue
            dedupe_rows += 1
            if len(cs) != N:
                dedupe_mismatch += 1
                dedupe_cells += len(cs)
            if {c["sub"] for c in cs} != set(range(N)):
                sub_mismatch += 1
                sub_cells += len(cs)

    # RAW (comparison only): same li, but applied to the un-deduped list
    raw_rows = 0
    raw_mismatch = 0
    raw_cells = 0
    for key, raw in v6.items():
        for li, ln in enumerate(raw):
            N = len(cjk(ln["text"]))
            if not N:
                continue
            cs = cells.get((key, li), [])
            if not cs:
                continue
            raw_rows += 1
            if len(cs) != N:
                raw_mismatch += 1
                raw_cells += len(cs)

    # dedupe dropped boxes / pages
    dropped = 0
    dropped_pages = set()
    for key, raw in v6.items():
        keep = {tuple(map(tuple, l["box"])) for l in dedupe_boxes(raw)}
        for l in raw:
            if tuple(map(tuple, l["box"])) not in keep:
                dropped += 1
                dropped_pages.add(key)

    out = {
        "definition": "nc=cells rows per (key,li); nl=CJK chars of dedupe_boxes(ocr_v6)[li]; denom=nc>0",
        "nl_source": "ocr_v6+93.dedupe_boxes+cjk_only",
        "excluded": "punctuation, spaces, non-CJK",
        "dedupe": {
            "rows_with_cells": dedupe_rows,
            "mismatch_rows": dedupe_mismatch,
            "mismatch_pct": round(100 * dedupe_mismatch / max(1, dedupe_rows), 1),
            "mismatch_cells": dedupe_cells,
            "mismatch_cells_pct": round(100 * dedupe_cells / max(1, total_cells), 1),
            "no_cell_rows": dedupe_nocell,
            "sub_coverage_mismatch_rows": sub_mismatch,
            "sub_coverage_mismatch_cells": sub_cells,
        },
        "raw_comparison": {
            "note": "li indexes the RAW list; this is a join artifact, not an error rate",
            "rows_with_cells": raw_rows,
            "mismatch_rows": raw_mismatch,
            "mismatch_pct": round(100 * raw_mismatch / max(1, raw_rows), 1),
            "mismatch_cells": raw_cells,
            "mismatch_cells_pct": round(100 * raw_cells / max(1, total_cells), 1),
        },
        "dedupe_drop": {"boxes": dropped, "pages": len(dropped_pages),
                        "pages_sample": sorted(dropped_pages)[:10]},
        "total_cells": total_cells,
    }
    (ROOT / "work-c" / "row_audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
