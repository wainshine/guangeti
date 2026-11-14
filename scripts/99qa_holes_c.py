#!/usr/bin/env python3
"""C-Q8: source-mask counter audit on the fixed C review table.

Only source-backed rows (real dual/single + page holdout) are evaluated.  Synthetic
GAN/ribbon rows have no source mask and are intentionally excluded; their quality
must be reviewed via the blind sheet, not via this source-fidelity gate.
"""
import json, sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
S = 256


def holes(mask):
    out = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    hier = out[-1]
    return 0 if hier is None else int(sum(1 for h in hier[0] if h[3] != -1))


def render(font, ch):
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((S // 2, int(880 * S / 1000)), ch, fill=255,
                            font=font, anchor="ms")
    return np.array(im) > 127


def main():
    ledger = Path(ROOT / "work-c/qa/review-c/ledger.tsv")
    chosen = [json.loads(l) for l in open(ROOT / "work-c/chosen.jsonl", encoding="utf-8")]
    hold = np.load(ROOT / "work-c/pairs_clean.npz", allow_pickle=True)
    hold_files = {str(k): str(f) for k, f in zip(hold["keys"], hold["files"])}
    fonts = {"real": str(ROOT / "build/GuanGeKai-C-Real.ttf"),
             "holdout": str(ROOT / "build/GuanGeKai-C-Regular.ttf")}
    fcache = {}
    rows = []
    lines = ledger.read_text(encoding="utf-8").splitlines()[1:]
    for line in lines:
        no, _line, ch, _cp, page, _meta, tag = line.split("\t")
        if tag not in ("dual", "single", "holdout"):
            continue
        if tag == "holdout":
            file = hold_files.get(page)
            fkey = "holdout"
        else:
            cand = [r for r in chosen if r["label"] == ch and str(r["page"]) == page]
            file = cand[0]["file"] if cand else None
            fkey = "real"
        if not file or not (ROOT / "work-c/masks" / file).exists():
            rows.append({"no": no, "char": ch, "tag": tag, "status": "missing_mask"})
            continue
        src = np.array(Image.open(ROOT / "work-c/masks" / file).convert("L")) > 127
        fpath = fonts[fkey]
        if fpath not in fcache:
            fcache[fpath] = ImageFont.truetype(fpath, S)
        sh, ph = holes(src), holes(render(fcache[fpath], ch))
        status = "source_open" if sh == 0 else ("potential_loss" if ph < sh else "ok")
        rows.append({"no": no, "char": ch, "tag": tag, "file": file,
                     "source_holes": sh, "product_holes": ph, "status": status})
    out = {
        "font_sha256": __import__("hashlib").sha256(
            (ROOT / "build/GuanGeKai-C-Real.ttf").read_bytes()).hexdigest(),
        "ledger": str(ledger), "n": len(rows), "seed": 0,
        "counts": {s: sum(1 for r in rows if r["status"] == s)
                   for s in ("ok", "potential_loss", "source_open", "missing_mask")},
        "potential_loss": [r for r in rows if r["status"] == "potential_loss"],
    }
    Path(ROOT / "work-c/qa/holes_c_source_mask.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out["counts"], ensure_ascii=False))
    print("potential_loss:", "".join(r["char"] for r in out["potential_loss"]) or "-")


if __name__ == "__main__":
    main()
