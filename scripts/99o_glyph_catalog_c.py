"""Million-cell glyph catalog with confidence tiers (no copies).

  verified : human-audited, correct (from work-c/verified seed)
  revoked  : human-audited, wrong (the marked audit cells)
  silver   : auto-pass (label + agree_ab + sane geometry), for noisy pretraining
  candidate: everything else with a label

Source crops/masks stay in work-c/exp/v3d2; the catalog stores their paths and hashes.
Identity is the crop sha256, not line/sub.
"""
from __future__ import annotations
import argparse, json, hashlib, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "work-c/exp/v3d2"
OUT = ROOT / "work-c/glyph_store"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    src = Path(args.src); out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    # seed verified
    verified = {json.loads(l)["id"] for l in open(ROOT / "work-c/verified/index.jsonl")}
    # human-marked wrong cells
    revoked = set()
    for wd, keyp, markedp in (
        (ROOT / "work-c", ROOT / "work-c/blind_400_key.json", ROOT / "work-c/blind_400_marked.json"),
        (src, src / "blind_300_key.json", src / "blind_300_audit.json")):
        key = {p["id"]: p for p in json.load(open(keyp))["cells"]}
        md = json.load(open(markedp))
        ids = {r["id"] for r in md} if isinstance(md, list) else set(md.get("ids", []))
        for i in ids:
            p = key.get(i)
            if not p: continue
            cp = wd / "cells" / p["file"]
            if cp.exists(): revoked.add(sha(cp)[:16])
    # agree_ab by file
    ab = {}
    for l in open(src / "labeled.jsonl"):
        r = json.loads(l); ab[r["file"]] = bool(r.get("agree_ab"))
    seen = {}; stats = collections.Counter(); by_char = collections.Counter(); conflicts = 0
    for l in open(src / "cells.jsonl"):
        r = json.loads(l)
        ch = r.get("label") or ""
        if not ch: continue
        cp = src / "cells" / r["file"]; mp = src / "masks" / r["file"]
        if not cp.exists(): continue
        h = sha(cp)[:16]
        if h in seen:
            continue
        cpitch = max(1.0, float(r.get("cpitch", 1)))
        sane = (not r.get("merged")) and r.get("fill", 0) >= 0.04 and r["h"] <= 1.25 * cpitch
        if h in verified: st = "verified"
        elif h in revoked: st = "revoked"
        elif ab.get(r["file"]) and sane: st = "silver"
        else: st = "candidate"
        rec = {"id": h, "label": ch, "status": st, "key": r["key"],
               "bbox": [r["x0"], r["y0"], r["x1"], r["y1"]],
               "src": str(cp.relative_to(ROOT)), "mask": str(mp.relative_to(ROOT)),
               "line": r["li"], "sub": r["sub"], "fill": r.get("fill"),
               "cpitch": round(cpitch, 1), "agree_ab": bool(ab.get(r["file"]))}
        seen[h] = rec; stats[st] += 1; by_char[ch] += 1
    with open(out / "index.jsonl", "w") as f:
        for k in sorted(seen): f.write(json.dumps(seen[k], ensure_ascii=False) + "\n")
    man = {"n": len(seen), "status": dict(stats), "unique_chars": len(by_char),
           "conflicts": conflicts, "source": str(src),
           "note": "id=crop sha256[:16]; line/sub are provenance only; verified/revoked from human audits"}
    (out / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1))
    print(json.dumps(man, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
