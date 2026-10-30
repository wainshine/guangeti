"""20k clustering pilot: shape clusters + anchor mapping + representative OCR.

This is a PILOT: it does not propagate labels and does not rewrite chosen.
It reports cluster entropy, anchor conflicts and representative OCR agreement.
"""
from __future__ import annotations
import argparse, json, random, collections, math, time
from pathlib import Path
import numpy as np, cv2
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; W = ROOT / "work-c"
SRC = W / "exp/v3d2"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(SRC))
    ap.add_argument("--sample", type=int, default=20000)
    ap.add_argument("--clusters", type=int, default=300)
    ap.add_argument("--out", default=str(W / "cluster_pilot"))
    ap.add_argument("--anchors", default=str(W / "verified/index.jsonl"))
    ap.add_argument("--ref", default=str(W / "wenkai_ref.json"))
    ap.add_argument("--skip-ocr", action="store_true")
    args = ap.parse_args()
    data = Path(args.data); out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    anchors = [json.loads(l) for l in open(args.anchors)]
    anchor_keys = {a["key"] for a in anchors}
    quota = {"一": 50, "二": 50, "三": 50, "申": 50}
    q = collections.Counter(); rng = random.Random(20261030)
    reservoir = []; n_all = 0; fills = []; aspects = []
    key_cells = collections.defaultdict(list)
    for l in open(data / "cells.jsonl"):
        r = json.loads(l); n_all += 1
        if n_all % 200000 == 0: print("scan", n_all, flush=True)
        f = r.get("fill") or 0
        fills.append(f)
        cp = max(1.0, float(r.get("cpitch") or 1))
        aspects.append(max(0.01, r["w"] / max(1.0, r["h"])))
        if r.get("key") in anchor_keys: key_cells[r["key"]].append(r)
        if not r.get("label") or f < 0.04 or r.get("merged"): continue
        if r["label"] in quota and q[r["label"]] < quota[r["label"]]:
            q[r["label"]] += 1; reservoir.append(r)
        elif len(reservoir) < args.sample:
            reservoir.append(r)
        else:
            j = rng.randrange(n_all)
            if j < len(reservoir): reservoir[j] = r
    # anchor mapping by nearest bbox centre, same key
    chosen = {}; failed = []
    for r in reservoir: chosen[r["file"]] = r
    def center(r):
        if r.get("bbox"):
            b = r["bbox"]; return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        return ((r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2)
    anchor_matches = []
    for a in anchors:
        best = None
        for r in key_cells.get(a["key"], []):
            if r.get("label") != a["label"]: continue
            cp = max(1.0, float(r.get("cpitch") or 1))
            ax, ay = center(a) if a.get("bbox") else (0, 0)
            rx, ry = center(r)
            d = math.hypot(ax - rx, ay - ry)
            if d <= 0.25 * cp and (best is None or d < best[0]): best = (d, r)
        if best:
            chosen[best[1]["file"]] = best[1]
            anchor_matches.append({"anchor": a["id"], "file": best[1]["file"], "label": a["label"]})
        else:
            failed.append({"id": a["id"], "key": a["key"], "label": a["label"]})
    rows = list(chosen.values())
    print("sample", len(rows), "anchors failed", len(failed), flush=True)
    thresholds = {"n": n_all,
                  "fill_p1": round(float(np.percentile(fills, 1)), 4),
                  "fill_p5": round(float(np.percentile(fills, 5)), 4),
                  "aspect_p1": round(float(np.percentile(aspects, 1)), 3),
                  "aspect_p5": round(float(np.percentile(aspects, 5)), 3)}
    (out / "thresholds.json").write_text(json.dumps(thresholds, ensure_ascii=False, indent=1))
    # embeddings
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from importlib.machinery import SourceFileLoader
    sel = SourceFileLoader("sel", str(ROOT / "scripts" / "05_select.py")).load_module()
    cache = out / "emb.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=True); X = z["X"]; meta = [dict(x) for x in z["meta"]]
    else:
        X = []; meta = []
        for i, r in enumerate(rows):
            v, m, _ = sel.norm_glyph(data / "cells" / r["file"])
            if v is None: continue
            X.append(v.reshape(-1)); meta.append(r)
            if i % 5000 == 0: print("embed", i, flush=True)
        X = np.asarray(X, dtype=np.float32)
        np.savez_compressed(cache, X=X, meta=np.array(meta, dtype=object))
    print("matrix", X.shape, flush=True)
    # PCA 64 + MiniBatchKMeans
    from sklearn.decomposition import PCA
    from sklearn.cluster import MiniBatchKMeans
    p = PCA(n_components=64, random_state=0).fit(X[::max(1, len(X)//20000)])
    Z = p.transform(X)
    km = MiniBatchKMeans(n_clusters=min(args.clusters, len(Z)), batch_size=2048,
                         n_init=3, random_state=0, max_iter=200).fit(Z)
    lab = km.labels_; cents = km.cluster_centers_
    by = collections.defaultdict(list)
    for i, c in enumerate(lab): by[int(c)].append(i)
    ref = json.load(open(args.ref))
    summaries = []
    for c, idx in by.items():
        labels = collections.Counter(meta[i]["label"] for i in idx)
        tot = sum(labels.values()); top = labels.most_common(2)
        ent = -sum((v / tot) * math.log(v / tot + 1e-9) for v in labels.values())
        summaries.append({"cluster": c, "n": len(idx), "top": top[0][0] if top else "",
                          "purity": round(top[0][1] / tot, 3) if top else 0,
                          "entropy": round(ent, 3), "labels": dict(labels.most_common(5)),
                          "idx": idx})
    if args.skip_ocr:
        with open(out / "clusters.jsonl", "w") as f:
            for x in summaries: f.write(json.dumps({k:v for k,v in x.items() if k!="idx"}, ensure_ascii=False) + "\n")
        with open(out / "assignments.jsonl", "w") as f:
            for i, r in enumerate(meta):
                f.write(json.dumps({"file": r["file"], "label": r["label"], "cluster": int(lab[i])}, ensure_ascii=False) + "\n")
        json.dump(anchor_matches, open(out / "anchor_matches.json", "w"), ensure_ascii=False, indent=1)
        print("clusters", len(summaries), "skip OCR ->", out, flush=True); return
    # representative OCR: medoid + farthest + random
    import sys as _s; _s.path.insert(0, str(ROOT / "scripts"))
    from importlib.machinery import SourceFileLoader as _S
    ocr = _S("ocr", str(ROOT / "scripts" / "92_ocr_c.py")).load_module()
    e6 = ocr.get_engine("v6"); e5 = ocr.get_engine("v5")
    def read_cell(r):
        img = cv2.imread(str(data / "cells" / r["file"]), cv2.IMREAD_GRAYSCALE)
        if img is None: return ("", "")
        h, w = img.shape; sc = max(1.0, 128.0 / max(1, min(h, w)))
        if sc > 1: img = cv2.resize(img, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_CUBIC)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        out = []
        for e in (e6, e5):
            try:
                r = e(img, use_det=False, use_cls=False, use_rec=True)
                out.append("".join(r.txts or "")[:1])
            except Exception:
                out.append("")
        return tuple(out)
    reps = []
    for s in summaries:
        idx = s.pop("idx"); d = np.linalg.norm(Z[idx] - cents[s["cluster"]], axis=1)
        picks = [idx[int(np.argmin(d))], idx[int(np.argmax(d))], idx[rng.randrange(len(idx))]]
        reads = []
        for i in picks:
            v6, v5 = read_cell(meta[i]); reads.append({"file": meta[i]["file"], "v6": v6, "v5": v5})
        s["reps"] = reads
        reps.extend(reads)
        summaries.append(s) if False else None
    # summaries mutated in place
    with open(out / "clusters.jsonl", "w") as f:
        for s in summaries: f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with open(out / "assignments.jsonl", "w") as f:
        for i, r in enumerate(meta):
            f.write(json.dumps({"file": r["file"], "label": r["label"], "cluster": int(lab[i])}, ensure_ascii=False) + "\n")
    json.dump(anchor_matches, open(out / "anchor_matches.json", "w"), ensure_ascii=False, indent=1)
    json.dump({"anchors": len(anchors), "anchors_failed": len(failed),
               "failed_sample": failed[:30]}, open(out / "anchors.json", "w"), ensure_ascii=False, indent=1)
    print("clusters", len(summaries), "reps_ocr", len(reps), "->", out, flush=True)


if __name__ == "__main__":
    main()
