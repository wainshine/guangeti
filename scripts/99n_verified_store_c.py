"""Immutable verified-glyph store.

A cell that is confirmed (correct crop + correct label) is stored by content hash,
NOT by its line/sub position.  Future cuts can reuse it by page bbox; JiT/GAN
training can read the whole store regardless of which line it came from.

Layout:
  work-c/verified/index.jsonl       one record per accepted crop
  work-c/verified/cells/<id>.png    gray crop
  work-c/verified/masks/<id>.png    binary mask
  work-c/verified/manifest.json     counts / sources

Record: {id, key, bbox:[x0,y0,x1,y1], label, crop_sha256, source, stratum, date, status}
"""
from __future__ import annotations
import argparse, json, hashlib, collections
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VER = ROOT / "work-c" / "verified"


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(VER))
    args = ap.parse_args()
    out = Path(args.out); (out / "cells").mkdir(parents=True, exist_ok=True); (out / "masks").mkdir(exist_ok=True)
    sources = [
        # label, work dir, key file, marked-ids file
        ("v3c-audit400", ROOT / "work-c", ROOT / "work-c/blind_400_key.json",
         ROOT / "work-c/blind_400_marked.json"),
        ("v3d2-audit300", ROOT / "work-c/exp/v3d2", ROOT / "work-c/exp/v3d2/blind_300_key.json",
         ROOT / "work-c/exp/v3d2/blind_300_audit.json"),
    ]
    index = {}; by_char = collections.Counter(); dup = 0; conflict = 0
    for label, wd, keyp, markedp in sources:
        key = {p["id"]: p for p in json.load(open(keyp))["cells"]}
        meta = {r["file"]: r for r in (json.loads(l) for l in open(wd / "cells.jsonl"))}
        md = json.load(open(markedp))
        if isinstance(md, list):
            marked = {r["id"] for r in md}
        elif "cells" in md:
            marked = {r["id"] for r in md["cells"]}
        else:
            marked = set(md.get("ids", []))
        for cid, p in key.items():
            if cid in marked: continue
            cp = wd / "cells" / p["file"]; mp = wd / "masks" / p["file"]
            if not cp.exists(): continue
            ch = p["our_label"]
            if not ch: continue
            h = sha_file(cp)
            rec = {"id": h[:16], "key": p["key"], "bbox": None, "label": ch,
                   "crop_sha256": h, "source": label, "status": "verified",
                   "line": p.get("li"), "sub": p.get("sub")}
            # bbox from the cell metadata, not from the audit key
            r = meta.get(p["file"])
            if r: rec["bbox"] = [r["x0"], r["y0"], r["x1"], r["y1"]]
            if rec["id"] in index:
                if index[rec["id"]]["label"] != ch: conflict += 1
                continue
            Image.open(cp).convert("L").save(out / "cells" / (rec["id"] + ".png"))
            if mp.exists(): Image.open(mp).convert("L").save(out / "masks" / (rec["id"] + ".png"))
            index[rec["id"]] = rec; by_char[ch] += 1
    with open(out / "index.jsonl", "w") as f:
        for k in sorted(index): f.write(json.dumps(index[k], ensure_ascii=False) + "\n")
    man = {"n": len(index), "sources": {s[0]: sum(1 for r in index.values() if r["source"] == s[0]) for s in sources},
           "unique_chars": len(by_char), "conflicts": conflict,
           "note": "id = crop sha256[:16]; key/bbox kept for reuse; line/sub are provenance only"}
    (out / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1))
    print(json.dumps(man, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
